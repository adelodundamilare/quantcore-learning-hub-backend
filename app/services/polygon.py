import os
import httpx
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.core.config import settings

class PolygonService:
    def __init__(self):
        self.base_url = "https://api.polygon.io"
        self.api_key = settings.POLYGON_API_KEY
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY is not set in environment variables")
        self.price_cache: dict = {}

    async def _make_request(self, path: str, params: Optional[dict] = None, allow_404: bool = False) -> Optional[dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{self.base_url}{path}"
            full_params = {"apiKey": self.api_key}
            if params:
                full_params.update(params)

            try:
                response = await client.get(url, params=full_params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if allow_404 and e.response.status_code == 404:
                    return None
                raise HTTPException(status_code=e.response.status_code, detail=f"API error: {e.response.text}")
            except httpx.RequestError as e:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Network error: {e}")

            return response.json()

    async def get_latest_quote(self, ticker: str, use_cache: bool = True) -> Optional[dict]:
        cache_key = f"quote_{ticker}"

        if use_cache and cache_key in self.price_cache:
            cached_data = self.price_cache[cache_key]
            if datetime.utcnow() - cached_data['timestamp'] < timedelta(seconds=5):
                return cached_data['data']

        data = await self._make_request(f"/v2/aggs/ticker/{ticker}/prev", allow_404=True)
        if not data or not data.get("results"):
            return None

        result = data["results"][0]

        quote_data = {
            "symbol": ticker,
            "price": result["c"],
            "change": result["c"] - result["o"],
            "change_percent": ((result["c"] - result["o"]) / result["o"]) * 100,
            "high": result["h"],
            "low": result["l"],
            "open": result["o"],
            "volume": result["v"],
            "timestamp": datetime.utcnow()
        }

        self.price_cache[cache_key] = {
            'data': quote_data,
            'timestamp': datetime.utcnow()
        }

        return quote_data
    async def get_company_details(self, ticker: str) -> Optional[dict]:
        data = await self._make_request(f"/v3/reference/tickers/{ticker}", allow_404=True)
        if not data:
            return None

        result = data.get("results", {})
        if not result:
            return None

        address = result.get("address", {})

        return {
            "symbol": ticker,
            "name": result.get("name", ""),
            "description": result.get("description", ""),
            "ceo": result.get("ceo", ""),
            "employees": result.get("total_employees"),
            "headquarters": f"{address.get('city', '')}, {address.get('state', '')}".strip(", "),
            "founded": result.get("list_date", ""),
            "market_cap": result.get("market_cap")
        }

    async def get_historical_data(self, ticker: str, from_date: datetime, to_date: datetime, multiplier: int = 1, timespan: str = "day") -> Optional[dict]:
        from_date_str = from_date.strftime("%Y-%m-%d")
        to_date_str = to_date.strftime("%Y-%m-%d")

        path = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date_str}/{to_date_str}"
        data = await self._make_request(path, allow_404=True)
        if not data or not data.get("results"):
            return None

        historical_results = []
        for result in data["results"]:
            historical_results.append({
                "open": result["o"],
                "high": result["h"],
                "low": result["l"],
                "close": result["c"],
                "volume": result["v"],
                "timestamp": datetime.fromtimestamp(result["t"] / 1000)
            })

        return {
            "symbol": ticker,
            "results_count": data.get("resultsCount", 0),
            "results": historical_results
        }

    async def get_all_stocks(self, search: Optional[str] = None, active: Optional[bool] = True, limit: int = 100, offset: int = 0) -> List[dict]:
        path = f"/v3/reference/tickers"
        params = {
            "market": "stocks",
            "active": "true" if active else "false",
            "limit": limit,
            "offset": offset
        }
        if search:
            params["search"] = search

        data = await self._make_request(path, params=params, allow_404=True)
        if not data:
            return []

        results = data.get("results", [])

        stocks = []
        for result in results:
            stocks.append({
                "symbol": result.get("ticker"),
                "name": result.get("name"),
                "market": result.get("market"),
                "locale": result.get("locale"),
                "primary_exchange": result.get("primary_exchange"),
                "type": result.get("type"),
                "active": result.get("active"),
                "currency_name": result.get("currency_name"),
                "cik": result.get("cik"),
                "composite_figi": result.get("composite_figi"),
                "share_class_figi": result.get("share_class_figi"),
                "last_updated_utc": result.get("last_updated_utc"),
                "delisted_utc": result.get("delisted_utc")
            })
        return stocks

    async def get_stock_details_combined(self, ticker: str) -> Optional[dict]:
        quote_data = await self.get_latest_quote(ticker)
        company_details = await self.get_company_details(ticker)

        if not quote_data and not company_details:
            return None

        combined_details = {
            "symbol": ticker,
            "name": company_details.get("name", ticker) if company_details else ticker,
            "price": quote_data.get("price") if quote_data else None,
            "change": quote_data.get("change") if quote_data else None,
            "change_percent": quote_data.get("change_percent") if quote_data else None,
            "high": quote_data.get("high") if quote_data else None,
            "low": quote_data.get("low") if quote_data else None,
            "open": quote_data.get("open") if quote_data else None,
            "volume": quote_data.get("volume") if quote_data else None,
            "avg_volume": None, # Not directly available from current Polygon endpoints
            "market_cap": company_details.get("market_cap") if company_details else None,
            "pe_ratio": None, # Not directly available from current Polygon endpoints
            "description": company_details.get("description") if company_details else None,
            "ceo": company_details.get("ceo") if company_details else None,
            "employees": company_details.get("employees") if company_details else None,
            "headquarters": company_details.get("headquarters") if company_details else None,
            "founded": company_details.get("founded") if company_details else None,
        }
        return combined_details

polygon_service = PolygonService()
