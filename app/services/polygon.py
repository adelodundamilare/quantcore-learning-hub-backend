import os
import httpx
from typing import Optional
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

    async def get_latest_quote(self, ticker: str, use_cache: bool = True) -> Optional[dict]:
        cache_key = f"quote_{ticker}"

        if use_cache and cache_key in self.price_cache:
            cached_data = self.price_cache[cache_key]
            if datetime.utcnow() - cached_data['timestamp'] < timedelta(seconds=5):
                return cached_data['data']

        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{self.base_url}/v2/aggs/ticker/{ticker}/prev"
            params = {"apiKey": self.api_key}

            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
            except httpx.RequestError as e:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Network error fetching quote: {e}")

            data = response.json()
            if not data.get("results"):
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{self.base_url}/v3/reference/tickers/{ticker}"
            params = {"apiKey": self.api_key}

            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
            except httpx.RequestError as e:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Network error fetching company details: {e}")

            data = response.json()
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            from_date_str = from_date.strftime("%Y-%m-%d")
            to_date_str = to_date.strftime("%Y-%m-%d")

            url = f"{self.base_url}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date_str}/{to_date_str}"
            params = {"apiKey": self.api_key}

            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
            except httpx.RequestError as e:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Network error fetching historical data: {e}")

            data = response.json()
            if not data.get("results"):
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

polygon_service = PolygonService()
