from datetime import datetime, timedelta
from typing import Dict
from collections import defaultdict
import asyncio
import logging
import socketio
from jose import jwt, JWTError
from pydantic import ValidationError
import httpx
from urllib.parse import parse_qs

from app.services.polygon import polygon_service
from app.core.config import settings
from app.schemas.token import TokenPayload
from app.core.database import SessionLocal
from app.crud.user import user as user_crud
from app.crud.token_denylist import token_denylist as token_denylist_crud

logger = logging.getLogger(__name__)

user_sessions: Dict[str, dict] = {}
subscribe_limits: Dict[int, list] = defaultdict(list)
BACKOFF_SECONDS = 60

active_subscriptions: set[str] = set()

symbol_error_backoff: Dict[str, datetime] = defaultdict(lambda: datetime.min)

def _convert_datetime_to_iso(data):
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, dict):
        return {k: _convert_datetime_to_iso(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_convert_datetime_to_iso(elem) for elem in data]
    return data


async def stream_prices_socketio(sio_server: socketio.AsyncServer):
    while True:
        try:
            symbols_to_fetch = list(active_subscriptions)

            if not symbols_to_fetch:
                await asyncio.sleep(5)
                continue

            now = datetime.utcnow()
            symbols_to_fetch = [
                s for s in symbols_to_fetch
                if (now - symbol_error_backoff[s]).total_seconds() > BACKOFF_SECONDS
            ]

            if not symbols_to_fetch:
                await asyncio.sleep(5)
                continue

            tasks = [polygon_service.get_latest_quote(symbol, use_cache=False) for symbol in symbols_to_fetch]
            quotes = await asyncio.gather(*tasks, return_exceptions=True)

            for i, symbol in enumerate(symbols_to_fetch):
                quote_result = quotes[i]
                if isinstance(quote_result, Exception):
                    logger.error(f"Error fetching quote for {symbol}: {quote_result}")
                    symbol_error_backoff[symbol] = now
                    await sio_server.emit('error', {'symbol': symbol, 'message': f'Failed to get price: {str(quote_result)}'}, room=symbol)
                elif quote_result:
                    serializable_quote = _convert_datetime_to_iso(quote_result)
                    await sio_server.emit('price_update', {'symbol': symbol, 'data': serializable_quote}, room=symbol)
                    if symbol in symbol_error_backoff:
                        del symbol_error_backoff[symbol]

            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Unhandled error in stream_prices_socketio: {e}")
            await asyncio.sleep(10)

def register_websocket_events(sio_server: socketio.AsyncServer):

    @sio_server.event
    async def connect(sid, environ, auth):
        db = None
        try:
            token = None
            if auth and 'token' in auth:
                token = auth['token']
            elif environ.get('QUERY_STRING'):
                query_params = parse_qs(environ.get('QUERY_STRING', ''))
                token = query_params.get('token', [None])[0]

            if not token:
                logger.warning(f"Connection rejected for {sid}: No token")
                return False

            db = SessionLocal()

            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            token_data = TokenPayload(**payload)

            if token_data.jti and token_denylist_crud.get_by_jti(db, jti=token_data.jti):
                logger.warning(f"Connection rejected for {sid}: Token has been revoked")
                return False

            user = user_crud.get(db, id=token_data.user_id)

            if not user:
                logger.warning(f"Connection rejected for {sid}: User not found for token")
                return False

            if not user.is_active:
                logger.warning(f"Connection rejected for {sid}: User account is inactive")
                return False

            user_sessions[sid] = {
                'user_id': user.id,
                'connected_at': datetime.utcnow(),
                'subscriptions': set()
            }

            await sio_server.save_session(sid, {'user_id': user.id})
            logger.info(f"Client {sid} connected (User: {user.id})")

            await sio_server.emit('connected', {
                'status': 'success',
                'message': 'Connected successfully'
            }, room=sid)

            return True

        except JWTError:
            logger.warning(f"Connection rejected for {sid}: Invalid token")
            return False
        except ValidationError:
            logger.warning(f"Connection rejected for {sid}: Invalid token payload")
            return False
        except Exception as e:
            logger.error(f"Connection error for {sid}: {e}")
            return False
        finally:
            if db:
                db.close()

    @sio_server.event
    async def disconnect(sid):
        user_id = user_sessions.get(sid, {}).get('user_id')

        for room in list(sio_server.rooms(sid)):
            if room != sid:
                await sio_server.leave_room(sid, room)

        if sid in user_sessions:
            del user_sessions[sid]

        logger.info(f"Client {sid} disconnected (User: {user_id})")

    @sio_server.on('subscribe')
    async def handle_subscribe(sid, data):
        try:
            symbol = data.get('symbol')

            if not symbol:
                await sio_server.emit('error', {
                    'message': 'Symbol is required'
                }, room=sid)
                return

            symbol = symbol.upper().strip()

            session = await sio_server.get_session(sid)
            if not session or 'user_id' not in session:
                await sio_server.emit('error', {
                    'message': 'Not authenticated'
                }, room=sid)
                return

            user_id = session['user_id']
            now = datetime.utcnow()

            subscribe_limits[user_id] = [
                t for t in subscribe_limits[user_id]
                if now - t < timedelta(minutes=1)
            ]

            if len(subscribe_limits[user_id]) >= 20:
                await sio_server.emit('error', {
                    'message': 'Rate limit exceeded. Max 20 subscriptions per minute'
                }, room=sid)
                return

            subscribe_limits[user_id].append(now)

            await sio_server.enter_room(sid, symbol)

            if sid in user_sessions:
                user_sessions[sid]['subscriptions'].add(symbol)

            active_subscriptions.add(symbol)

            logger.info(f"Client {sid} subscribed to {symbol}")

            initial_quote = await polygon_service.get_latest_quote(symbol)
            if initial_quote:
                serializable_initial_quote = _convert_datetime_to_iso(initial_quote)
                await sio_server.emit('price_update', {
                    'symbol': symbol,
                    'data': serializable_initial_quote
                }, room=sid)

            await sio_server.emit('subscribed', {
                'symbol': symbol,
                'status': 'success'
            }, room=sid)

        except Exception as e:
            logger.error(f"Subscribe error for {sid}: {e}")
            await sio_server.emit('error', {
                'message': f'Failed to subscribe: {str(e)}'
            }, room=sid)

    @sio_server.on('unsubscribe')
    async def handle_unsubscribe(sid, data):
        try:
            symbol = data.get('symbol')

            if not symbol:
                await sio_server.emit('error', {
                    'message': 'Symbol is required'
                }, room=sid)
                return

            symbol = symbol.upper().strip()

            sio_server.leave_room(sid, symbol)

            if sid in user_sessions:
                user_sessions[sid]['subscriptions'].discard(symbol)

            if not any(symbol in s['subscriptions'] for s in user_sessions.values()):
                active_subscriptions.discard(symbol)

            logger.info(f"Client {sid} unsubscribed from {symbol}")

            await sio_server.emit('unsubscribed', {
                'symbol': symbol,
                'status': 'success'
            }, room=sid)

        except Exception as e:
            logger.error(f"Unsubscribe error for {sid}: {e}")
            await sio_server.emit('error', {
                'message': f'Failed to unsubscribe: {str(e)}'
            }, room=sid)

    @sio_server.on('ping')
    async def handle_ping(sid, data):
        await sio_server.emit('pong', {
            'timestamp': datetime.utcnow().isoformat()
        }, room=sid)