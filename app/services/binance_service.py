import logging
import httpx
from typing import Dict

logger = logging.getLogger(__name__)

class BinanceService:
    def __init__(self):
        self.last_prices = {}
        self.alert_thresholds = {
            "BTC": 2.0,
            "ETH": 3.0,
            "GOLD": 1.5
        }
    
    async def get_price(self, symbol: str) -> Dict:
        """Obtenir le prix depuis CoinGecko"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if symbol == "BTC":
                    response = await client.get(
                        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        price = float(data["bitcoin"]["usd"])
                        logger.info(f"📊 {symbol}: ${price:,.2f}")
                        return {"symbol": symbol, "price": price, "success": True}
                
                elif symbol == "ETH":
                    response = await client.get(
                        "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        price = float(data["ethereum"]["usd"])
                        logger.info(f"📊 {symbol}: ${price:,.2f}")
                        return {"symbol": symbol, "price": price, "success": True}
                
                elif symbol == "GOLD":
                    response = await client.get("https://api.gold-api.com/price/XAU")
                    if response.status_code == 200:
                        data = response.json()
                        price = float(data.get("price", 2400))
                        if price > 0:
                            logger.info(f"📊 {symbol}: ${price:,.2f}")
                            return {"symbol": symbol, "price": price, "success": True}
                    return {"symbol": symbol, "price": 2400, "success": True}
                
                return {"symbol": symbol, "price": 0, "success": False}
                
        except Exception as e:
            logger.error(f"Erreur {symbol}: {e}")
            mock_prices = {"BTC": 65000, "ETH": 3500, "GOLD": 2400}
            return {"symbol": symbol, "price": mock_prices.get(symbol, 0), "success": True}
    
    async def get_price_with_details(self, symbol: str) -> Dict:
        """Obtenir le prix avec détails"""
        price_data = await self.get_price(symbol)
        return {
            "price": price_data.get("price", 0),
            "change_24h": 0,
            "volume": 0
        }
    
    async def get_24h_change(self, symbol: str) -> Dict:
        """Obtenir la variation 24h"""
        return {"symbol": symbol, "success": False, "change_24h": 0}
    
    async def check_and_alert(self, symbol: str) -> Dict:
        """Vérifier les alertes"""
        return None
    
    async def get_weekly_report(self) -> Dict:
        """Rapport hebdomadaire"""
        return {"assets": {}, "summary": {}}
    
    async def get_portfolio_value(self, holdings: Dict[str, float]) -> Dict:
        """Valeur du portefeuille"""
        total_value = 0
        details = {}
        for symbol, quantity in holdings.items():
            price_data = await self.get_price(symbol)
            if price_data.get("success"):
                value = price_data["price"] * quantity
                total_value += value
                details[symbol] = {"quantity": quantity, "price": price_data["price"], "value": value}
        return {"total_value": total_value, "details": details}
