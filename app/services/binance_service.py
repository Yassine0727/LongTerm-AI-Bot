import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
import random
import time

import httpx
from decimal import Decimal

from app.core.config import config

logger = logging.getLogger(__name__)

class BinanceService:
    """Service pour recuperer les prix et donnees de Binance"""
    
    def __init__(self):
        # Liste des miroirs Binance
        self.base_urls = [
            "https://api.binance.com",
            "https://api1.binance.com", 
            "https://api2.binance.com",
            "https://api3.binance.com",
            "https://api.binance.us",
            "https://api.binance.vision",
            "https://api.binance.com/api/v3",
        ]
        
        self.symbols = {
            "BTC": "BTCUSDT",
            "ETH": "ETHUSDT",
            "GOLD": "XAUTUSDT"
        }
        
        self.last_prices = {}
        self.price_history = {}
        self.alert_thresholds = {
            "BTC": float(getattr(config, 'ALERT_BTC_THRESHOLD', 2.0)),
            "ETH": float(getattr(config, 'ALERT_ETH_THRESHOLD', 3.0)),
            "GOLD": float(getattr(config, 'ALERT_GOLD_THRESHOLD', 1.5))
        }
        self.weekly_data = {}
        self.current_url_index = 0
        
        # Headers pour imiter un navigateur
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }
    
    def _get_next_url(self) -> str:
        """Obtenir le prochain miroir Binance"""
        url = self.base_urls[self.current_url_index]
        self.current_url_index = (self.current_url_index + 1) % len(self.base_urls)
        return url
    
    async def get_price(self, symbol: str) -> Dict:
        """Obtenir le prix actuel depuis Binance"""
        try:
            if symbol not in self.symbols:
                return {"symbol": symbol, "price": 0, "success": False}
            
            binance_symbol = self.symbols[symbol]
            
            # Essayer tous les miroirs
            for attempt in range(15):
                base_url = self._get_next_url()
                
                # Construire l'URL correctement
                if base_url.endswith("/api/v3"):
                    url = f"{base_url}/ticker/price"
                else:
                    url = f"{base_url}/api/v3/ticker/price"
                
                try:
                    async with httpx.AsyncClient(
                        timeout=15.0,
                        headers=self.headers,
                        follow_redirects=True
                    ) as client:
                        response = await client.get(url, params={"symbol": binance_symbol})
                        
                        if response.status_code == 200:
                            data = response.json()
                            if "price" in data:
                                price = float(data["price"])
                                logger.info(f"📊 {symbol}: ${price:,.2f}")
                                return {"symbol": symbol, "price": price, "success": True}
                        
                        elif response.status_code == 451:
                            logger.warning(f"⚠️ Blocage 451 sur {base_url}, essai suivant...")
                            continue
                        
                        elif response.status_code == 403:
                            logger.warning(f"⚠️ Accès interdit sur {base_url}, essai suivant...")
                            continue
                        
                        elif response.status_code == 429:
                            logger.warning(f"⚠️ Rate limit sur {base_url}, attente...")
                            await asyncio.sleep(2)
                            continue
                        
                        else:
                            logger.warning(f"⚠️ Erreur {response.status_code} sur {base_url}")
                            continue
                            
                except httpx.ConnectError:
                    logger.warning(f"⚠️ Connexion impossible sur {base_url}")
                    continue
                    
                except httpx.TimeoutException:
                    logger.warning(f"⚠️ Timeout sur {base_url}")
                    continue
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erreur sur {base_url}: {e}")
                    continue
            
            # Si on arrive ici, Binance ne fonctionne pas du tout
            logger.error(f"❌ Binance totalement inaccessible pour {symbol} après 15 tentatives")
            
            # Dernière tentative avec un proxy
            return await self._get_price_with_proxy(symbol)
                
        except Exception as e:
            logger.error(f"❌ Erreur {symbol}: {e}")
            return await self._get_price_with_proxy(symbol)
    
    async def _get_price_with_proxy(self, symbol: str) -> Dict:
        """Dernière tentative avec proxy"""
        try:
            # Liste de proxies gratuits (à tester)
            proxy_list = [
                "http://45.138.80.105:8080",
                "http://45.138.80.108:8080", 
                "http://45.138.80.109:8080",
                "http://45.138.80.111:8080",
            ]
            
            binance_symbol = self.symbols.get(symbol)
            if not binance_symbol:
                return {"symbol": symbol, "price": 0, "success": False}
            
            for proxy in proxy_list:
                try:
                    async with httpx.AsyncClient(
                        timeout=15.0,
                        proxies=proxy,
                        headers=self.headers
                    ) as client:
                        response = await client.get(
                            "https://api.binance.com/api/v3/ticker/price",
                            params={"symbol": binance_symbol}
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            price = float(data["price"])
                            logger.info(f"📊 {symbol}: ${price:,.2f} (via proxy)")
                            return {"symbol": symbol, "price": price, "success": True}
                            
                except Exception as e:
                    logger.warning(f"⚠️ Proxy {proxy} échoué: {e}")
                    continue
            
            # Si tout échoue, retourner le dernier prix connu
            if symbol in self.last_prices and self.last_prices[symbol] > 0:
                logger.warning(f"⚠️ Utilisation du dernier prix connu: {symbol} = {self.last_prices[symbol]}")
                return {"symbol": symbol, "price": self.last_prices[symbol], "success": True}
            
            logger.error(f"❌ Binance inaccessible pour {symbol}")
            return {"symbol": symbol, "price": 0, "success": False}
            
        except Exception as e:
            logger.error(f"❌ Erreur proxy {symbol}: {e}")
            if symbol in self.last_prices and self.last_prices[symbol] > 0:
                return {"symbol": symbol, "price": self.last_prices[symbol], "success": True}
            return {"symbol": symbol, "price": 0, "success": False}
    
    async def get_price_with_details(self, symbol: str) -> Dict:
        """Obtenir le prix avec plus de détails"""
        price_data = await self.get_price(symbol)
        if not price_data.get("success") or price_data.get("price", 0) == 0:
            return {"price": 0, "change_24h": 0, "volume": 0}
        
        # Sauvegarder le prix pour fallback
        self.last_prices[symbol] = price_data["price"]
        
        data_24h = await self.get_24h_change(symbol)
        
        return {
            "price": price_data["price"],
            "change_24h": data_24h.get("change_24h", 0) if data_24h.get("success") else 0,
            "volume": data_24h.get("volume", 0) if data_24h.get("success") else 0
        }
    
    async def get_24h_change(self, symbol: str) -> Dict:
        """Obtenir la variation sur 24h"""
        for attempt in range(5):
            base_url = self._get_next_url()
            
            if base_url.endswith("/api/v3"):
                url = f"{base_url}/ticker/24hr"
            else:
                url = f"{base_url}/api/v3/ticker/24hr"
            
            try:
                async with httpx.AsyncClient(timeout=10.0, headers=self.headers) as client:
                    binance_symbol = self.symbols.get(symbol)
                    if not binance_symbol:
                        return {"symbol": symbol, "success": False}
                    
                    response = await client.get(url, params={"symbol": binance_symbol})
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "symbol": symbol,
                            "price": float(data["lastPrice"]),
                            "change_24h": float(data["priceChangePercent"]),
                            "high": float(data["highPrice"]),
                            "low": float(data["lowPrice"]),
                            "volume": float(data["volume"]),
                            "success": True
                        }
                    elif response.status_code == 451:
                        continue
            except Exception as e:
                logger.warning(f"⚠️ Erreur 24h {symbol}: {e}")
                continue
        
        return {"symbol": symbol, "success": False, "change_24h": 0}
    
    async def get_historical_klines(self, symbol: str, interval: str = "1d", limit: int = 30) -> List[Dict]:
        """Obtenir les donnees historiques"""
        for attempt in range(5):
            base_url = self._get_next_url()
            
            if base_url.endswith("/api/v3"):
                url = f"{base_url}/klines"
            else:
                url = f"{base_url}/api/v3/klines"
            
            try:
                async with httpx.AsyncClient(timeout=10.0, headers=self.headers) as client:
                    binance_symbol = self.symbols.get(symbol)
                    if not binance_symbol:
                        return []
                    
                    response = await client.get(url, params={
                        "symbol": binance_symbol,
                        "interval": interval,
                        "limit": limit
                    })
                    
                    if response.status_code == 200:
                        data = response.json()
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
                    elif response.status_code == 451:
                        continue
            except Exception as e:
                logger.warning(f"⚠️ Erreur klines {symbol}: {e}")
                continue
        
        return []
    
    async def check_and_alert(self, symbol: str) -> Optional[Dict]:
        """Verifier si une alerte doit etre declenchee"""
        try:
            current = await self.get_price(symbol)
            if not current.get("success") or current.get("price", 0) == 0:
                return None
            
            current_price = current["price"]
            
            if symbol not in self.last_prices or self.last_prices[symbol] == 0:
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
            if price_data.get("success") and price_data.get("price", 0) > 0:
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
