import json
import os
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

class PriceRecorder:
    """Service pour enregistrer les prix dans un fichier"""
    
    def __init__(self):
        self.data_dir = "data"
        self.prices_file = "data/price_history.json"
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Créer le dossier data s'il n'existe pas"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def _load_history(self) -> Dict:
        """Charger l'historique des prix"""
        try:
            if os.path.exists(self.prices_file):
                with open(self.prices_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"records": []}
        except Exception as e:
            logger.error(f"Erreur chargement historique: {e}")
            return {"records": []}
    
    def _save_history(self, data: Dict):
        """Sauvegarder l'historique"""
        try:
            with open(self.prices_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Historique sauvegardé: {len(data['records'])} enregistrements")
        except Exception as e:
            logger.error(f"Erreur sauvegarde historique: {e}")
    
    async def save_prices(self, prices: Dict):
        """Enregistrer les prix actuels"""
        try:
            # Charger l'historique existant
            history = self._load_history()
            
            # Créer l'enregistrement
            record = {
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime("%d/%m/%Y"),
                "time": datetime.now().strftime("%H:%M:%S"),
                "prices": {}
            }
            
            # Ajouter chaque prix
            for symbol, data in prices.items():
                record["prices"][symbol] = {
                    "price": data.get("price", 0),
                    "change_24h": data.get("change_24h", 0),
                    "volume": data.get("volume", 0)
                }
            
            # Ajouter à l'historique
            history["records"].append(record)
            
            # Garder seulement les 365 derniers jours (max 1460 enregistrements pour 6h)
            max_records = 1460
            if len(history["records"]) > max_records:
                history["records"] = history["records"][-max_records:]
            
            # Sauvegarder
            self._save_history(history)
            
            # Log corrigé - sans f-string problématique
            price_str = ""
            for s, d in record["prices"].items():
                price_str += f"{s}: ${d['price']:,.2f}, "
            price_str = price_str[:-2]  # Enlever la dernière virgule
            logger.info(f"📊 Prix enregistrés: {price_str}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur enregistrement prix: {e}")
            return False
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Obtenir l'historique des prix"""
        history = self._load_history()
        records = history.get("records", [])
        return records[-limit:] if records else []
    
    def get_last_price(self, symbol: str) -> Dict:
        """Obtenir le dernier prix d'un actif"""
        history = self._load_history()
        records = history.get("records", [])
        
        if not records:
            return None
        
        for record in reversed(records):
            if symbol in record.get("prices", {}):
                return {
                    "timestamp": record["timestamp"],
                    "price": record["prices"][symbol]["price"],
                    "change_24h": record["prices"][symbol]["change_24h"],
                    "volume": record["prices"][symbol]["volume"]
                }
        return None
    
    def get_daily_summary(self, date: str = None) -> Dict:
        """Obtenir un résumé journalier"""
        if not date:
            date = datetime.now().strftime("%d/%m/%Y")
        
        history = self._load_history()
        records = history.get("records", [])
        
        day_records = [r for r in records if r.get("date") == date]
        
        if not day_records:
            return None
        
        summary = {}
        for symbol in ["BTC", "ETH", "GOLD"]:
            prices = [r["prices"][symbol]["price"] for r in day_records if symbol in r.get("prices", {})]
            if prices:
                summary[symbol] = {
                    "first": prices[0],
                    "last": prices[-1],
                    "max": max(prices),
                    "min": min(prices),
                    "avg": sum(prices) / len(prices),
                    "count": len(prices)
                }
        
        return summary