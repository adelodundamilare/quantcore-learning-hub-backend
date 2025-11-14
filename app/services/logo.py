import asyncio
import httpx
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class LogoService:
    def __init__(self):
        self.logo_cache: Dict[str, Optional[str]] = {}
        self.domain_mappings = {
            # Common ticker to domain mappings
            'AAPL': 'apple.com',
            'MSFT': 'microsoft.com',
            'GOOGL': 'google.com',
            'AMZN': 'amazon.com',
            'TSLA': 'tesla.com',
            'META': 'meta.com',
            'NVDA': 'nvidia.com',
            'NFLX': 'netflix.com',
            'AMD': 'amd.com',
            'INTC': 'intel.com',
            'CRM': 'salesforce.com',
            'ORCL': 'oracle.com',
            'CSCO': 'cisco.com',
            'ADBE': 'adobe.com',
            'PYPL': 'paypal.com',
            'UBER': 'uber.com',
            'LYFT': 'lyft.com',
            'SPOT': 'spotify.com',
            'ZOOM': 'zoom.us',
            'SHOP': 'shopify.com',
            'SQ': 'block.com',
            'COIN': 'coinbase.com',
            'ROKU': 'roku.com',
            'PINS': 'pinterest.com',
            'TWTR': 'twitter.com',  # Note: Twitter rebranded to X
            'SNAP': 'snapchat.com',
            'TTD': 'thetradedesk.com',
            'FSLY': 'fastly.com',
            'NET': 'cloudflare.com',
            'OKTA': 'okta.com',
            'ZS': 'zscaler.com',
            'CRWD': 'crowdstrike.com',
            'DDOG': 'datadoghq.com',
            'NOW': 'servicenow.com',
            'TEAM': 'microsoft.com',  # Microsoft Teams
            'DOCU': 'docusign.com',
            'ZM': 'zoom.us',
            'PLTR': 'palantir.com',
            'ASAN': 'asana.com',
            'BILL': 'bill.com',
            'ETSY': 'etsy.com',
            'MELI': 'mercadolibre.com',
            'SE': 'shopify.com',
            'RUM': 'rumble.com',
            'HOOD': 'robinhood.com',
            'COIN': 'coinbase.com',
            'MSTR': 'microstrategy.com',
            'RIOT': 'riotblockchain.com',
            'MARA': 'marathon-digital.com',
            'ETHA': 'blackrock.com',
            'IBIT': 'blackrock.com',
            'SPY': 'ssga.com',
            'QQQ': 'invesco.com',
            'IWM': 'blackrock.com'
        }

    async def _url_exists(self, url: str) -> bool:
        """Check if a URL exists without downloading the full content."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.head(url)
                return response.status_code == 200
        except Exception:
            return False

    def _extract_domain_from_symbol(self, symbol: str, company_name: Optional[str] = None) -> str:
        """Extract domain from stock symbol using mappings or company name."""
        if symbol.upper() in self.domain_mappings:
            return self.domain_mappings[symbol.upper()]

        if company_name:
            name = company_name.lower().replace(' ', '').replace(',', '').replace('.', '')
            name = name.replace('inc', '').replace('corp', '').replace('corporation', '').replace('company', '').replace('ltd', '').replace('limited', '')

            potential_domains = [
                f"{name}.com",
                f"{name}inc.com",
                f"{name}corp.com"
            ]

            # For now, return the first potential domain
            # In production, you might want to validate these
            return potential_domains[0] if potential_domains else f"{name}.com"

        return f"{symbol.lower()}.com"

    async def get_company_logo(self, symbol: str, company_name: Optional[str] = None) -> Optional[str]:
        """Get company logo URL using Clearbit API."""
        cache_key = f"{symbol}_{company_name or ''}".strip('_')

        if cache_key in self.logo_cache:
            return self.logo_cache[cache_key]

        try:
            domain = self._extract_domain_from_symbol(symbol, company_name)

            clearbit_url = f"https://logo.clearbit.com/{domain}"

            if await self._url_exists(clearbit_url):
                logo_url = clearbit_url
            else:
                alt_clearbit_url = f"https://logo.clearbit.com/{domain}?size=128"
                if await self._url_exists(alt_clearbit_url):
                    logo_url = alt_clearbit_url
                else:
                    favicon_url = f"https://{domain}/favicon.ico"
                    if await self._url_exists(favicon_url):
                        logo_url = favicon_url
                    else:
                        logo_url = None

            self.logo_cache[cache_key] = logo_url
            return logo_url

        except Exception as e:
            logger.error(f"Error fetching logo for {symbol}: {e}")
            self.logo_cache[cache_key] = None
            return None

    async def get_multiple_logos(self, symbols_and_names: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
        """Get logos for multiple symbols concurrently."""
        tasks = [
            self.get_company_logo(symbol, company_name)
            for symbol, company_name in symbols_and_names.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        logo_map = {}
        for (symbol, _), result in zip(symbols_and_names.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching logo for {symbol}: {result}")
                logo_map[symbol] = None
            else:
                logo_map[symbol] = result

        return logo_map

    def clear_cache(self):
        """Clear the logo cache."""
        self.logo_cache.clear()

logo_service = LogoService()
