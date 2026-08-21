import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
import httpx

from app.services.binance_service import BinanceService

logger = logging.getLogger(__name__)

class PortfolioService:
    """Service de gestion du portefeuille"""
    
    def __init__(self):
        self.portfolio_file = "data/portfolio.json"
        self.binance = BinanceService()
        self._ensure_file()
    
    def _ensure_file(self):
        """Créer le fichier s'il n'existe pas"""
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.portfolio_file):
            with open(self.portfolio_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "tnd_usd_rate": 3.8,
                    "fee_percent": 0,
                    "transactions": [],
                    "holdings": {}
                }, f, indent=2, ensure_ascii=False)
    
    def _load_data(self) -> Dict:
        """Charger les données du portefeuille"""
        try:
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "tnd_usd_rate": 3.8,
                "fee_percent": 0,
                "transactions": [],
                "holdings": {}
            }
    
    def _save_data(self, data: Dict):
        """Sauvegarder les données"""
        with open(self.portfolio_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _get_price_sync(self, asset: str) -> float:
        """Obtenir le prix de manière synchrone (sans asyncio)"""
        try:
            import httpx
            with httpx.Client(timeout=10.0) as client:
                if asset == "BTC":
                    # Kraken d'abord
                    try:
                        response = client.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD")
                        if response.status_code == 200:
                            data = response.json()
                            return float(data["result"]["XXBTZUSD"]["c"][0])
                    except Exception as e:
                        logger.warning(f"⚠️ Kraken BTC échoué: {e}")
                    
                    # Fallback CoinCap
                    try:
                        response = client.get("https://api.coincap.io/v2/assets/bitcoin")
                        if response.status_code == 200:
                            data = response.json()
                            return float(data["data"]["priceUsd"])
                    except Exception as e:
                        logger.warning(f"⚠️ CoinCap BTC échoué: {e}")
                    
                    # Fallback CoinGecko
                    try:
                        response = client.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
                        if response.status_code == 200:
                            data = response.json()
                            return float(data["bitcoin"]["usd"])
                    except Exception as e:
                        logger.warning(f"⚠️ CoinGecko BTC échoué: {e}")
                    
                elif asset == "ETH":
                    # Kraken d'abord
                    try:
                        response = client.get("https://api.kraken.com/0/public/Ticker?pair=ETHUSD")
                        if response.status_code == 200:
                            data = response.json()
                            return float(data["result"]["XETHZUSD"]["c"][0])
                    except Exception as e:
                        logger.warning(f"⚠️ Kraken ETH échoué: {e}")
                    
                    # Fallback CoinCap
                    try:
                        response = client.get("https://api.coincap.io/v2/assets/ethereum")
                        if response.status_code == 200:
                            data = response.json()
                            return float(data["data"]["priceUsd"])
                    except Exception as e:
                        logger.warning(f"⚠️ CoinCap ETH échoué: {e}")
                    
                    # Fallback CoinGecko
                    try:
                        response = client.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
                        if response.status_code == 200:
                            data = response.json()
                            return float(data["ethereum"]["usd"])
                    except Exception as e:
                        logger.warning(f"⚠️ CoinGecko ETH échoué: {e}")
                    
                elif asset == "GOLD":
                    # Gold-API
                    try:
                        response = client.get("https://api.gold-api.com/price/XAU")
                        if response.status_code == 200:
                            data = response.json()
                            return float(data.get("price", 0))
                    except Exception as e:
                        logger.warning(f"⚠️ Gold-API échoué: {e}")
                    
                    # Fallback Binance XAUUSDT
                    try:
                        response = client.get(
                            "https://api.binance.com/api/v3/ticker/price",
                            params={"symbol": "XAUTUSDT"}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            return float(data["price"])
                    except Exception as e:
                        logger.warning(f"⚠️ Binance XAUUSDT échoué: {e}")
                
                # Dernier fallback
                fallback = {"BTC": 65000, "ETH": 3500, "GOLD": 2400}
                return fallback.get(asset, 0)
                
        except Exception as e:
            logger.error(f"❌ Erreur prix {asset}: {e}")
            fallback = {"BTC": 65000, "ETH": 3500, "GOLD": 2400}
            return fallback.get(asset, 0)
    
    def add_transaction(self, asset: str, amount_tnd: float, fee_percent: float = None) -> Dict:
        """
        Ajouter une transaction d'achat
        """
        try:
            data = self._load_data()
            rate = data["tnd_usd_rate"]
            fee = fee_percent if fee_percent is not None else data["fee_percent"]
            
            # Calculer USD
            amount_usd = amount_tnd / rate
            
            # Calculer les frais
            fee_amount_usd = amount_usd * (fee / 100)
            amount_usd_after_fee = amount_usd - fee_amount_usd
            
            # Obtenir le prix actuel (synchrone)
            price = self._get_price_sync(asset)
            
            if price == 0:
                return {"success": False, "error": f"Impossible d'obtenir le prix de {asset}"}
            
            # Calculer la quantité
            quantity = amount_usd_after_fee / price
            
            # Créer la transaction
            transaction = {
                "id": len(data["transactions"]) + 1,
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime("%d/%m/%Y"),
                "time": datetime.now().strftime("%H:%M:%S"),
                "asset": asset,
                "amount_tnd": amount_tnd,
                "amount_usd": amount_usd,
                "fee_percent": fee,
                "fee_amount_usd": fee_amount_usd,
                "amount_usd_after_fee": amount_usd_after_fee,
                "price_usd": price,
                "quantity": quantity,
                "status": "active"
            }
            
            # Ajouter à l'historique
            data["transactions"].append(transaction)
            
            # Mettre à jour les avoirs
            if asset not in data["holdings"]:
                data["holdings"][asset] = {
                    "total_quantity": 0,
                    "total_invested_usd": 0,
                    "total_invested_tnd": 0,
                    "transactions": []
                }
            
            data["holdings"][asset]["total_quantity"] += quantity
            data["holdings"][asset]["total_invested_usd"] += amount_usd_after_fee
            data["holdings"][asset]["total_invested_tnd"] += amount_tnd
            data["holdings"][asset]["transactions"].append(transaction)
            
            self._save_data(data)
            
            logger.info(f"Achat {asset}: {quantity:.8f} a ${price:,.2f}")
            
            return {
                "success": True,
                "transaction": transaction,
                "message": f"Achat de {quantity:.8f} {asset} a ${price:,.2f} (frais: {fee}%)"
            }
            
        except Exception as e:
            logger.error(f"Erreur achat: {e}")
            return {"success": False, "error": str(e)}
    
    def get_portfolio_summary(self) -> Dict:
        """Obtenir un résumé du portefeuille"""
        data = self._load_data()
        holdings = data.get("holdings", {})
        transactions = data.get("transactions", [])
        
        summary = {
            "total_invested_tnd": 0,
            "total_invested_usd": 0,
            "total_current_usd": 0,
            "total_profit_usd": 0,
            "total_profit_tnd": 0,
            "roi_percent": 0,
            "assets": {},
            "transactions_count": len(transactions),
            "tnd_usd_rate": data["tnd_usd_rate"],
            "fee_percent": data["fee_percent"]
        }
        
        for asset, h in holdings.items():
            # Obtenir le prix actuel (synchrone)
            current_price = self._get_price_sync(asset)
            
            # Si le prix est 0, utiliser un fallback
            if current_price == 0:
                fallback = {"BTC": 65000, "ETH": 3500, "GOLD": 2400}
                current_price = fallback.get(asset, 0)
                logger.warning(f"⚠️ Utilisation du prix fallback pour {asset}: ${current_price}")
            
            current_value_usd = h["total_quantity"] * current_price
            profit_usd = current_value_usd - h["total_invested_usd"]
            
            summary["total_invested_tnd"] += h["total_invested_tnd"]
            summary["total_invested_usd"] += h["total_invested_usd"]
            summary["total_current_usd"] += current_value_usd
            
            summary["assets"][asset] = {
                "quantity": h["total_quantity"],
                "invested_usd": h["total_invested_usd"],
                "invested_tnd": h["total_invested_tnd"],
                "current_price": current_price,
                "current_value_usd": current_value_usd,
                "profit_usd": profit_usd,
                "profit_tnd": profit_usd * data["tnd_usd_rate"],
                "roi_percent": (profit_usd / h["total_invested_usd"] * 100) if h["total_invested_usd"] > 0 else 0,
                "transactions_count": len(h["transactions"])
            }
        
        total_profit_usd = summary["total_current_usd"] - summary["total_invested_usd"]
        summary["total_profit_usd"] = total_profit_usd
        summary["total_profit_tnd"] = total_profit_usd * data["tnd_usd_rate"]
        
        if summary["total_invested_usd"] > 0:
            summary["roi_percent"] = (total_profit_usd / summary["total_invested_usd"]) * 100
        
        return summary
    
    def get_transactions(self, asset: str = None, limit: int = 20) -> List[Dict]:
        """Obtenir les transactions"""
        data = self._load_data()
        transactions = data.get("transactions", [])
        
        if asset:
            transactions = [t for t in transactions if t.get("asset") == asset]
        
        return transactions[-limit:] if transactions else []
    
    def get_weekly_report(self) -> Dict:
        """Générer un rapport hebdomadaire du portefeuille"""
        summary = self.get_portfolio_summary()
        transactions = self.get_transactions(limit=50)
        
        week_transactions = []
        for t in transactions:
            try:
                t_date = datetime.fromisoformat(t["timestamp"])
                if (datetime.now() - t_date).days <= 7:
                    week_transactions.append(t)
            except:
                pass
        
        report = {
            "date": datetime.now().isoformat(),
            "summary": summary,
            "week_transactions": week_transactions,
            "week_count": len(week_transactions),
            "best_performer": None,
            "worst_performer": None
        }
        
        best_roi = -100
        worst_roi = 100
        for asset, data in summary["assets"].items():
            if data["roi_percent"] > best_roi:
                best_roi = data["roi_percent"]
                report["best_performer"] = asset
            if data["roi_percent"] < worst_roi:
                worst_roi = data["roi_percent"]
                report["worst_performer"] = asset
        
        return report
    
    def reset_portfolio(self) -> bool:
        """Réinitialiser complètement le portefeuille"""
        try:
            import os
            import json
            
            # Supprimer le fichier portfolio
            if os.path.exists(self.portfolio_file):
                os.remove(self.portfolio_file)
                logger.info("🗑️ Fichier portfolio supprimé")
            
            # Recréer un fichier vierge
            self._ensure_file()
            
            # Réinitialiser les données en mémoire
            self._load_data()
            
            logger.info("✅ Portefeuille réinitialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur reset_portfolio: {e}")
            return False
    
    def clear_all_data(self) -> bool:
        """Supprimer toutes les données du portefeuille"""
        try:
            import os
            import shutil
            
            # Supprimer le fichier
            if os.path.exists(self.portfolio_file):
                os.remove(self.portfolio_file)
                logger.info("🗑️ Fichier portfolio supprimé")
            
            # Supprimer le dossier data s'il est vide
            data_folder = "data"
            if os.path.exists(data_folder) and not os.listdir(data_folder):
                os.rmdir(data_folder)
                logger.info("🗑️ Dossier data supprimé")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur clear_all_data: {e}")
            return False
    
    def set_tnd_usd_rate(self, rate: float) -> bool:
        """Définir le taux TND/USD"""
        try:
            data = self._load_data()
            data["tnd_usd_rate"] = rate
            self._save_data(data)
            logger.info(f"✅ Taux TND/USD mis à jour: {rate}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur set_tnd_usd_rate: {e}")
            return False
    
    def set_fee_percent(self, fee: float) -> bool:
        """Définir le pourcentage de frais"""
        try:
            data = self._load_data()
            data["fee_percent"] = fee
            self._save_data(data)
            logger.info(f"✅ Frais mis à jour: {fee}%")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur set_fee_percent: {e}")
            return False
    
    def get_holdings(self) -> Dict:
        """Obtenir les avoirs actuels"""
        data = self._load_data()
        return data.get("holdings", {})
    
    def get_total_value(self) -> Dict:
        """Obtenir la valeur totale du portefeuille"""
        summary = self.get_portfolio_summary()
        return {
            "total_invested_usd": summary["total_invested_usd"],
            "total_current_usd": summary["total_current_usd"],
            "total_profit_usd": summary["total_profit_usd"],
            "total_profit_tnd": summary["total_profit_tnd"],
            "roi_percent": summary["roi_percent"],
            "tnd_usd_rate": summary["tnd_usd_rate"]
        }
    
    def delete_transaction(self, transaction_id: int) -> bool:
        """Supprimer une transaction spécifique"""
        try:
            data = self._load_data()
            
            # Trouver la transaction
            transaction_to_remove = None
            for t in data["transactions"]:
                if t["id"] == transaction_id:
                    transaction_to_remove = t
                    break
            
            if not transaction_to_remove:
                return False
            
            # Supprimer de la liste des transactions
            data["transactions"] = [t for t in data["transactions"] if t["id"] != transaction_id]
            
            # Mettre à jour les avoirs
            asset = transaction_to_remove["asset"]
            if asset in data["holdings"]:
                # Recréer les avoirs à partir des transactions restantes
                holdings = data["holdings"][asset]
                holdings["total_quantity"] = 0
                holdings["total_invested_usd"] = 0
                holdings["total_invested_tnd"] = 0
                
                for t in data["transactions"]:
                    if t.get("asset") == asset:
                        holdings["total_quantity"] += t.get("quantity", 0)
                        holdings["total_invested_usd"] += t.get("amount_usd_after_fee", 0)
                        holdings["total_invested_tnd"] += t.get("amount_tnd", 0)
            
            self._save_data(data)
            logger.info(f"🗑️ Transaction {transaction_id} supprimée")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur delete_transaction: {e}")
            return False
