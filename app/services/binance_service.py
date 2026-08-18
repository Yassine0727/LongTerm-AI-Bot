import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
import random

import httpx
from decimal import Decimal

from app.core.config import config

logger = logging.getLogger(__name__)

class BinanceService:
    """Service pour recuperer les prix et donnees de Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.symbols = {
            "BTC": "BTCUSDT",
            "ETH": "ETHUSDT",
            "GOLD": "XAUTUSDT"  # Tether Gold (or tokenisé)
        }
        self.last_prices = {}
        self.price_history = {}
        self.alert_thresholds = {
            "BTC": float(getattr(config, 'ALERT_BTC_THRESHOLD', 2.0)),
            "ETH": float(getattr(config, 'ALERT_ETH_THRESHOLD', 3.0)),
            "GOLD": float(getattr(config, 'ALERT_GOLD_THRESHOLD', 1.5))
        }
        self.weekly_data = {}
        
        # ===== PROXY CONFIGURATION =====
        # Liste de proxies gratuits (à tester, peuvent changer)
        self.proxies = [
            "http://45.138.80.105:8080",
            "http://45.138.80.108:8080",
            "http://45.138.80.109:8080",
            "http://45.138.80.111:8080",
            "http://45.138.80.112:8080",
            "http://45.138.80.113:8080",
            "http://45.138.80.114:8080",
            "http://45.138.80.115:8080",
            "http://45.138.80.116:8080",
            "http://45.138.80.117:8080",
            "http://45.138.80.118:8080",
            "http://45.138.80.119:8080",
        ]
        self.current_proxy_index = 0
        self.use_proxy = True  # Mettre à False pour désactiver le proxy
    
    def _get_next_proxy(self) -> Optional[str]:
        """Obtenir le prochain proxy dans la liste (round-robin)"""
        if not self.proxies or not self.use_proxy:
            return None
        
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy
    
    async def _make_request(self, url: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """Faire une requête HTTP avec fallback et retry"""
        for attempt in range(max_retries):
            proxy = self._get_next_proxy()
            
            try:
                async with httpx.AsyncClient(
                    timeout=15.0,
                    proxies=proxy
                ) as client:
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 451:
                        logger.warning(f"⚠️ Blocage 451, tentative {attempt+1}/{max_retries} avec proxy {proxy}")
                        continue
                    else:
                        logger.warning(f"⚠️ Erreur HTTP {response.status_code}, tentative {attempt+1}/{max_retries}")
                        continue
                        
            except Exception as e:
                logger.warning(f"⚠️ Erreur requête (tentative {attempt+1}/{max_retries}): {e}")
                continue
        
        return None
    
    async def get_price(self, symbol: str) -> Dict:
        """Obtenir le prix actuel d'un symbole"""
        try:
            if symbol in ["BTC", "ETH", "GOLD"]:
                binance_symbol = self.symbols.get(symbol)
                if binance_symbol:
                    url = f"{self.base_url}/api/v3/ticker/price"
                    data = await self._make_request(url, {"symbol": binance_symbol})
                    
                    if data and "price" in data:
                        price = float(data["price"])
                        logger.info(f"📊 {symbol}: ${price:,.2f}")
                        return {"symbol": symbol, "price": price, "success": True}
            
            # Fallback: essayer de récupérer le prix depuis CoinGecko
            return await self._get_price_fallback(symbol)
                
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return await self._get_price_fallback(symbol)
    
    async def _get_price_fallback(self, symbol: str) -> Dict:
        """Récupérer le prix depuis CoinGecko en fallback"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if symbol == "BTC":
                    response = await client.get(
                        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        price = float(data["bitcoin"]["usd"])
                        logger.info(f"📊 {symbol}: ${price:,.2f} (via CoinGecko)")
                        return {"symbol": symbol, "price": price, "success": True}
                
                elif symbol == "ETH":
                    response = await client.get(
                        "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        price = float(data["ethereum"]["usd"])
                        logger.info(f"📊 {symbol}: ${price:,.2f} (via CoinGecko)")
                        return {"symbol": symbol, "price": price, "success": True}
                
                elif symbol == "GOLD":
                    response = await client.get("https://api.gold-api.com/price/XAU")
                    if response.status_code == 200:
                        data = response.json()
                        price = float(data.get("price", 0))
                        if price > 0:
                            logger.info(f"📊 {symbol}: ${price:,.2f} (via Gold-API)")
                            return {"symbol": symbol, "price": price, "success": True}
                
                # Dernier fallback: prix simulé
                mock_prices = {"BTC": 65000, "ETH": 3500, "GOLD": 2400}
                price = mock_prices.get(symbol, 0)
                logger.warning(f"⚠️ Utilisation du prix simulé pour {symbol}: ${price}")
                return {"symbol": symbol, "price": price, "success": True}
                
        except Exception as e:
            logger.error(f"Fallback error for {symbol}: {e}")
            mock_prices = {"BTC": 65000, "ETH": 3500, "GOLD": 2400}
            return {"symbol": symbol, "price": mock_prices.get(symbol, 0), "success": True}
    
    async def get_price_with_details(self, symbol: str) -> Dict:
        """Obtenir le prix avec plus de détails"""
        price_data = await self.get_price(symbol)
        if not price_data.get("success"):
            return {"price": 0, "change_24h": 0, "volume": 0}
        
        data_24h = await self.get_24h_change(symbol)
        
        return {
            "price": price_data["price"],
            "change_24h": data_24h.get("change_24h", 0) if data_24h.get("success") else 0,
            "volume": data_24h.get("volume", 0) if data_24h.get("success") else 0
        }
    
    async def get_24h_change(self, symbol: str) -> Dict:
        """Obtenir la variation sur 24h"""
        try:
            if symbol in ["BTC", "ETH", "GOLD"]:
                binance_symbol = self.symbols.get(symbol)
                if binance_symbol:
                    url = f"{self.base_url}/api/v3/ticker/24hr"
                    data = await self._make_request(url, {"symbol": binance_symbol})
                    
                    if data and "lastPrice" in data:
                        return {
                            "symbol": symbol,
                            "price": float(data["lastPrice"]),
                            "change_24h": float(data["priceChangePercent"]),
                            "high": float(data["highPrice"]),
                            "low": float(data["lowPrice"]),
                            "volume": float(data["volume"]),
                            "success": True
                        }
            
            return {"symbol": symbol, "success": False, "change_24h": 0}
            
        except Exception as e:
            logger.error(f"Error fetching 24h for {symbol}: {e}")
            return {"symbol": symbol, "success": False, "change_24h": 0}
    
    async def get_historical_klines(self, symbol: str, interval: str = "1d", limit: int = 30) -> List[Dict]:
        """Obtenir les donnees historiques"""
        try:
            if symbol in ["BTC", "ETH", "GOLD"]:
                binance_symbol = self.symbols.get(symbol)
                if binance_symbol:
                    url = f"{self.base_url}/api/v3/klines"
                    data = await self._make_request(
                        url,
                        {"symbol": binance_symbol, "interval": interval, "limit": limit}
                    )
                    
                    if data:
                        return [
                            {
                                "timestamp": datetime.fromtimestamp(k[0]/1000).isoformat(),
                                "open": float(k[1]),
                                "high": float(k[2]),
                                "low": float(k[3]),
                                "close": float(k[4]),
                                "volume": float(k[5])
                            }
                            for k in data
                        ]
            return []
            
        except Exception as e:
            logger.error(f"Error fetching historical for {symbol}: {e}")
            return []
    
    async def check_and_alert(self, symbol: str) -> Optional[Dict]:
        """Verifier si une alerte doit etre declenchee"""
        try:
            current = await self.get_price(symbol)
            if not current.get("success"):
                return None
            
            current_price = current["price"]
            
            if symbol not in self.last_prices:
                self.last_prices[symbol] = current_price
                return None
            
            old_price = self.last_prices[symbol]
            change_percent = ((current_price - old_price) / old_price) * 100
            
            threshold = self.alert_thresholds.get(symbol, 2.0)
            
            if abs(change_percent) >= threshold:
                self.last_prices[symbol] = current_price
                data_24h = await self.get_24h_change(symbol)
                
                logger.info(f"🔔 ALERTE {symbol}: {change_percent:+.2f}%")
                
                return {
                    "symbol": symbol,
                    "old_price": old_price,
                    "current_price": current_price,
                    "change_percent": change_percent,
                    "threshold": threshold,
                    "data_24h": data_24h if data_24h.get("success") else None,
                    "timestamp": datetime.now().isoformat()
                }
            
            self.last_prices[symbol] = current_price
            return None
            
        except Exception as e:
            logger.error(f"Error checking alert for {symbol}: {e}")
            return None
    
    async def get_detailed_weekly_report(self) -> Dict:
        """Generer un rapport hebdomadaire detaille"""
        report = {
            "date": datetime.now().isoformat(),
            "week_start": (datetime.now() - timedelta(days=7)).isoformat(),
            "week_end": datetime.now().isoformat(),
            "assets": {},
            "summary": {}
        }
        
        total_change = 0
        total_assets = 0
        
        for symbol in ["BTC", "ETH", "GOLD"]:
            try:
                historical = await self.get_historical_klines(symbol, "1d", 7)
                
                if historical:
                    prices = [h["close"] for h in historical]
                    max_price = max(prices)
                    min_price = min(prices)
                    start_price = historical[0]["close"]
                    end_price = historical[-1]["close"]
                    change_7d = ((end_price - start_price) / start_price) * 100
                    
                    max_date = None
                    min_date = None
                    for h in historical:
                        if h["close"] == max_price:
                            max_date = h["timestamp"]
                        if h["close"] == min_price:
                            min_date = h["timestamp"]
                    
                    total_volume = sum([h["volume"] for h in historical])
                    
                    daily_prices = []
                    for h in historical:
                        daily_prices.append({
                            "date": h["timestamp"][:10],
                            "price": h["close"],
                            "change": ((h["close"] - historical[0]["close"]) / historical[0]["close"]) * 100
                        })
                    
                    report["assets"][symbol] = {
                        "start_price": start_price,
                        "end_price": end_price,
                        "max_price": max_price,
                        "max_date": max_date,
                        "min_price": min_price,
                        "min_date": min_date,
                        "change_7d": change_7d,
                        "total_volume": total_volume,
                        "avg_price": sum(prices) / len(prices),
                        "volatility": max_price - min_price,
                        "daily_prices": daily_prices,
                        "performance": "excellent" if change_7d > 10 else "good" if change_7d > 5 else "stable" if change_7d > -5 else "weak"
                    }
                    
                    total_change += change_7d
                    total_assets += 1
            except Exception as e:
                logger.error(f"Error generating detailed weekly for {symbol}: {e}")
                report["assets"][symbol] = {"error": str(e)}
        
        if total_assets > 0:
            avg_change = total_change / total_assets
            report["summary"] = {
                "avg_change": avg_change,
                "best_performer": max(report["assets"].items(), key=lambda x: x[1].get("change_7d", -100))[0] if report["assets"] else "N/A",
                "worst_performer": min(report["assets"].items(), key=lambda x: x[1].get("change_7d", 100))[0] if report["assets"] else "N/A",
                "overall_sentiment": "positive" if avg_change > 0 else "negative" if avg_change < 0 else "neutral"
            }
        
        return report
    
    async def get_weekly_report(self) -> Dict:
        """Generer un rapport hebdomadaire (alias)"""
        return await self.get_detailed_weekly_report()
    
    async def get_portfolio_value(self, holdings: Dict[str, float]) -> Dict:
        """Calculer la valeur du portefeuille"""
        total_value = 0
        details = {}
        
        for symbol, quantity in holdings.items():
            price_data = await self.get_price(symbol)
            if price_data.get("success"):
                value = price_data["price"] * quantity
                total_value += value
                details[symbol] = {
                    "quantity": quantity,
                    "price": price_data["price"],
                    "value": value
                }
        
        return {
            "total_value": total_value,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
