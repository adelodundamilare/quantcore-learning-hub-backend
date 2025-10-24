from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.endpoints import auth, account, course, utility, school, role, permission, notification, curriculum, exam, reward_rating, course_progress, report, trading, billing, webhooks
from app.realtime import websockets as websocket_events
from fastapi.exceptions import RequestValidationError
from app.middleware.exceptions import global_exception_handler, validation_exception_handler
import socketio
import asyncio
from datetime import datetime, timedelta

from app.services.report import report_service
from app.core.database import SessionLocal
from app.crud.school import school as crud_school

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/socket.io", socketio.ASGIApp(sio))

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(school.router, prefix="/schools", tags=["Schools"])
app.include_router(account.router, prefix="/account", tags=["Account"])
app.include_router(course.router, prefix="/courses", tags=["Courses"])
app.include_router(curriculum.router, tags=["Curriculum"])
app.include_router(exam.router, prefix="/exams", tags=["Exams"])
app.include_router(course_progress.router, tags=["Course Progress"])
app.include_router(reward_rating.router, tags=["Reward & Rating"])
app.include_router(report.router, tags=["Reports"])

app.include_router(role.router, prefix="/roles", tags=["Roles"])
app.include_router(permission.router, prefix="/permissions", tags=["Permissions"])
app.include_router(notification.router, prefix="/notifications", tags=["Notifications"])
app.include_router(utility.router, prefix="/utility", tags=["utility"])

app.include_router(billing.router, prefix="/billing", tags=["Billing"])
trading_router = trading.create_trading_router()
app.include_router(trading_router, prefix="/trading", tags=["Trading"])
app.include_router(webhooks.router, tags=["Webhooks"])

async def _run_leaderboard_precomputation():
    while True:
        db = SessionLocal()
        try:
            schools = crud_school.get_multi(db)
            for school in schools:
                await report_service.precompute_trading_leaderboard(db, school_id=school.id, current_user_context=None)
                await report_service.precompute_leaderboard(db, school_id=school.id)
        except Exception as e:
            print(f"Error during leaderboard precomputation: {e}")
        finally:
            db.close()
        await asyncio.sleep(60*60)

@app.on_event("startup")
async def startup_event():
    websocket_events.register_websocket_events(sio)
    asyncio.create_task(websocket_events.stream_prices_socketio(sio))
    asyncio.create_task(_run_leaderboard_precomputation())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)