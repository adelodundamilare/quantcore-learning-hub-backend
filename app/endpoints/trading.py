from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.constants import OrderTypeEnum
from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.user import UserContext
from app.schemas.trading import (
    HistoricalDataPointSchema,
    HistoricalDataSchema,
    PortfolioPositionSchema,
    StockDetailsSchema,
    StockQuoteSchema,
    StockSchema,
    UserWatchlistCreate,
    UserWatchlistUpdate,
    UserWatchlistSchema,
    AccountBalanceSchema,
    PortfolioItemSchema,
    TradeOrderCreate,
    TradeOrder,
    CompanyDetailsSchema,
    PortfolioHistoricalDataSchema,
    OrderPreviewRequest,
    OrderPreview,
    NewsArticle
)
from app.services.polygon import polygon_service
from app.services.trading import trading_service
from app.services.popular_stocks_cache import popular_stocks_cache

# Popular stocks to show by default
POPULAR_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX",
    "AMD", "INTC", "CRM", "ORCL", "CSCO", "ADBE", "PYPL", "UBER",
    "SPOT", "ZOOM", "SHOP", "SQ", "COIN", "ROKU", "PINS", "SNAP",
    "TTD", "OKTA", "ZS", "CRWD", "DDOG", "NOW", "DOCU", "PLTR"
]

def create_trading_router():
    router = APIRouter()

    @router.get("/stocks", response_model=APIResponse[List[StockSchema]])
    async def get_stocks(
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context),
        search: Optional[str] = None,
        active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0
    ):
        if search:
            stocks = await polygon_service.get_all_stocks(
                search=search, active=active, limit=limit, offset=offset
            )
            message = f"Found {len(stocks)} stocks matching '{search}'"
        else:
            stocks_data = await popular_stocks_cache.get_popular_stocks(limit=limit)

            stocks = []
            for stock_data in stocks_data:
                try:
                    stock = StockSchema(**stock_data)
                    stocks.append(stock)
                except Exception as e:
                    continue

            message = f"Popular stocks retrieved ({len(stocks)} stocks)"

        return APIResponse(message=message, data=stocks)

    @router.get("/stocks/{ticker}/details_combined", response_model=APIResponse[StockDetailsSchema])
    async def get_stock_details_combined(
        ticker: str,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        combined_details = await polygon_service.get_stock_details_combined(ticker)
        if not combined_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Details for {ticker} not found."
            )
        return APIResponse(message=f"Combined details for {ticker} retrieved successfully", data=combined_details)

    @router.get("/stocks/{ticker}/quote", response_model=APIResponse[StockQuoteSchema])
    async def get_stock_quote(
        ticker: str,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        quote_data = await polygon_service.get_latest_quote(ticker)
        if not quote_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quote for {ticker} not found."
            )

        try:
            stock_quote = StockQuoteSchema(
                symbol=quote_data.get('T', ticker),
                price=quote_data.get('p'),
                timestamp=quote_data.get('t')
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error parsing quote data: {e}"
            )

        return APIResponse(
            message=f"Latest quote for {ticker} retrieved successfully",
            data=stock_quote
        )

    @router.get("/stocks/{ticker}/details", response_model=APIResponse[CompanyDetailsSchema])
    async def get_company_details(
        ticker: str,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        details_data = await polygon_service.get_company_details(ticker)
        if not details_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Details for {ticker} not found."
            )

        try:
            company_details = CompanyDetailsSchema(**details_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error parsing company details: {e}"
            )

        return APIResponse(
            message=f"Company details for {ticker} retrieved successfully",
            data=company_details
        )



    @router.get("/account/balance", response_model=APIResponse[AccountBalanceSchema])
    async def get_account_balance(
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        balance = await trading_service.get_account_balance(db, user_id=context.user.id)
        return APIResponse(
            message="Account balance retrieved successfully",
            data=balance
        )

    @router.get("/portfolio", response_model=APIResponse[List[PortfolioPositionSchema]])
    async def get_portfolio(
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context),
        skip: int = 0,
        limit: int = 100
    ):
        portfolio = await trading_service.get_portfolio(
            db,
            user_id=context.user.id,
            skip=skip,
            limit=limit
        )
        return APIResponse(
            message="User portfolio retrieved successfully",
            data=portfolio
        )

    @router.get("/portfolio/history", response_model=APIResponse[PortfolioHistoricalDataSchema])
    async def get_portfolio_history(
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        from_dt: Optional[datetime] = None
        to_dt: Optional[datetime] = None

        if from_date:
            try:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid from_date format. Use YYYY-MM-DD"
                )

        if to_date:
            try:
                to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid to_date format. Use YYYY-MM-DD"
                )

        if from_dt and to_dt and from_dt > to_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_date must be before to_date"
            )

        historical_data = await trading_service.get_portfolio_historical_data(
            db,
            user_id=context.user.id,
            from_date=from_dt,
            to_date=to_dt
        )

        return APIResponse(
            message="Portfolio historical data retrieved successfully",
            data=PortfolioHistoricalDataSchema(user_id=context.user.id, results=historical_data)
        )

    @router.get("/portfolio/{position_id}", response_model=APIResponse[PortfolioItemSchema])
    async def get_portfolio_position_by_id(
        position_id: int,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        position = await trading_service.get_portfolio_position_by_id(
            db,
            user_id=context.user.id,
            position_id=position_id
        )
        return APIResponse(
            message="Portfolio position retrieved successfully",
            data=position
        )

    @router.post("/watchlists", response_model=APIResponse[UserWatchlistSchema], status_code=status.HTTP_201_CREATED)
    async def create_user_watchlist(
        watchlist_in: UserWatchlistCreate,
        db: Session = Depends(deps.get_transactional_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        new_watchlist = await trading_service.create_user_watchlist(
            db,
            user_id=context.user.id,
            watchlist_in=watchlist_in
        )
        return APIResponse(message="Watchlist created successfully", data=new_watchlist)

    @router.get("/watchlists", response_model=APIResponse[List[UserWatchlistSchema]])
    async def get_user_watchlists(
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context),
        skip: int = 0,
        limit: int = 100
    ):
        watchlists = await trading_service.get_user_watchlists(
            db,
            user_id=context.user.id,
            skip=skip,
            limit=limit
        )
        return APIResponse(message="User watchlists retrieved successfully", data=watchlists)

    @router.get("/watchlists/{watchlist_id}", response_model=APIResponse[UserWatchlistSchema])
    async def get_user_watchlist_by_id(
        watchlist_id: int,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        watchlist = await trading_service.get_user_watchlist_by_id(
            db,
            user_id=context.user.id,
            watchlist_id=watchlist_id
        )
        return APIResponse(message="Watchlist retrieved successfully", data=watchlist)

    @router.put("/watchlists/{watchlist_id}", response_model=APIResponse[UserWatchlistSchema])
    async def update_user_watchlist(
        watchlist_id: int,
        watchlist_in: UserWatchlistUpdate,
        db: Session = Depends(deps.get_transactional_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        updated_watchlist = await trading_service.update_user_watchlist(
            db,
            user_id=context.user.id,
            watchlist_id=watchlist_id,
            watchlist_in=watchlist_in
        )
        return APIResponse(message="Watchlist updated successfully", data=updated_watchlist)

    @router.delete("/watchlists/{watchlist_id}", response_model=APIResponse[dict])
    async def delete_user_watchlist(
        watchlist_id: int,
        db: Session = Depends(deps.get_transactional_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        result = trading_service.delete_user_watchlist(
            db,
            user_id=context.user.id,
            watchlist_id=watchlist_id
        )
        return APIResponse(message=result["message"])

    @router.post("/watchlists/{watchlist_id}/stocks/{symbol}", response_model=APIResponse[UserWatchlistSchema], status_code=status.HTTP_201_CREATED)
    async def add_stock_to_user_watchlist(
        watchlist_id: int,
        symbol: str,
        db: Session = Depends(deps.get_transactional_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        updated_watchlist = await trading_service.add_stock_to_watchlist(
            db,
            user_id=context.user.id,
            watchlist_id=watchlist_id,
            symbol=symbol.upper()
        )
        return APIResponse(message="Stock added to watchlist successfully", data=updated_watchlist)

    @router.delete("/watchlists/{watchlist_id}/stocks/{symbol}", response_model=APIResponse[UserWatchlistSchema])
    async def remove_stock_from_user_watchlist(
        watchlist_id: int,
        symbol: str,
        db: Session = Depends(deps.get_transactional_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        updated_watchlist = await trading_service.remove_stock_from_watchlist(
            db,
            user_id=context.user.id,
            watchlist_id=watchlist_id,
            symbol=symbol.upper()
        )
        return APIResponse(message="Stock removed from watchlist successfully", data=updated_watchlist)

    @router.post("/trade/buy", response_model=APIResponse[TradeOrder], status_code=status.HTTP_201_CREATED)
    async def buy_stock(
        order_in: TradeOrderCreate,
        db: Session = Depends(deps.get_transactional_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        if order_in.order_type != OrderTypeEnum.BUY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order type must be BUY."
            )
        new_order = await trading_service.place_order(
            db,
            user_id=context.user.id,
            order_in=order_in
        )
        return APIResponse(
            message="Buy order placed successfully",
            data=new_order
        )

    @router.post("/trade/sell", response_model=APIResponse[TradeOrder], status_code=status.HTTP_201_CREATED)
    async def sell_stock(
        order_in: TradeOrderCreate,
        db: Session = Depends(deps.get_transactional_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        if order_in.order_type != OrderTypeEnum.SELL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order type must be SELL."
            )
        new_order = await trading_service.place_order(
            db,
            user_id=context.user.id,
            order_in=order_in
        )
        return APIResponse(
            message="Sell order placed successfully",
            data=new_order
        )

    @router.post("/orders/preview", response_model=OrderPreview)
    async def preview_order(
        order_preview: OrderPreviewRequest,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context),
    ):
        return await trading_service.preview_order(db, context.user.id, order_preview)

    @router.get("/trade/history", response_model=APIResponse[List[TradeOrder]])
    def get_trade_history(
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context),
        skip: int = 0,
        limit: int = 100
    ):
        history = trading_service.get_trade_history(
            db,
            user_id=context.user.id,
            skip=skip,
            limit=limit
        )
        return APIResponse(
            message="Trade history retrieved successfully",
            data=history
        )

    @router.get("/stocks/{ticker}/history", response_model=APIResponse[HistoricalDataSchema])
    async def get_historical_data(
        ticker: str,
        from_date: str,
        to_date: str,
        multiplier: int = 1,
        timespan: str = "day",
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

        if from_dt > to_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_date must be before to_date"
            )

        historical_data = await polygon_service.get_historical_data(
            ticker,
            from_dt,
            to_dt,
            multiplier,
            timespan
        )

        if not historical_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Historical data for {ticker} not found."
            )

        try:
            historical_schema = HistoricalDataSchema(
                symbol=historical_data.get('symbol', ticker),
                results_count=historical_data.get('results_count', 0),
                results=[
                    HistoricalDataPointSchema(**res)
                    for res in historical_data.get('results', [])
                ]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error parsing historical data: {e}"
            )

        return APIResponse(
            message=f"Historical data for {ticker} retrieved successfully",
            data=historical_schema
        )

    @router.get("/news", response_model=APIResponse[List[NewsArticle]])
    async def get_market_news(
        limit: int = 20,
        symbols: Optional[str] = None,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        news_articles = await polygon_service.get_market_news(limit=limit, symbols=symbols)
        return APIResponse(message="Market news retrieved successfully", data=[NewsArticle(**article) for article in news_articles])

    @router.get("/news/{symbol}", response_model=APIResponse[List[NewsArticle]])
    async def get_stock_news(
        symbol: str,
        limit: int = 10,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        news_articles = await polygon_service.get_stock_news(symbol=symbol, limit=limit)
        return APIResponse(message=f"News for {symbol} retrieved successfully", data=[NewsArticle(**article) for article in news_articles])

    return router
