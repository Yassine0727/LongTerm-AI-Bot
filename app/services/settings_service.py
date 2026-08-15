import json
import os
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SettingsService:
    """Service de gestion des paramètres depuis settings.json"""
    
    def __init__(self):
        self.settings_file = "settings.json"
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict:
        """Charger les paramètres depuis le fichier"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Créer le fichier par défaut
                default_settings = self._get_default_settings()
                self._save_settings(default_settings)
                return default_settings
        except Exception as e:
            logger.error(f"Erreur chargement settings: {e}")
            return self._get_default_settings()
    
    def _save_settings(self, settings: Dict):
        """Sauvegarder les paramètres"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde settings: {e}")
    
    def _get_default_settings(self) -> Dict:
        """Paramètres par défaut"""
        return {
            "telegram": {
                "channels": ["@Crypto_News95"],
                "enabled": True
            },
            "binance": {
                "enabled": True,
                "symbols": ["BTC", "ETH", "GOLD"]
            },
            "deepseek": {
                "enabled": True
            },
            "notifications": {
                "telegram": True,
                "email": False,
                "whatsapp": False
            },
            "portfolio": {
                "tnd_usd_rate": 3.12,
                "fee_percent": 3.7
            },
            "alerts": {
                "price_alerts": True,
                "news_alerts": True,
                "weekly_report": True,
                "thresholds": {
                    "BTC": 2.0,
                    "ETH": 3.0,
                    "GOLD": 1.5
                }
            },
            "prices": {
                "check_interval_hours": 1,
                "save_interval_hours": 6
            }
        }
    
    def get_telegram_channels(self) -> List[str]:
        """Obtenir la liste des chaînes Telegram"""
        return self.settings.get("telegram", {}).get("channels", ["@Crypto_News95"])
    
    def get_binance_symbols(self) -> List[str]:
        """Obtenir la liste des symboles Binance"""
        return self.settings.get("binance", {}).get("symbols", ["BTC", "ETH", "GOLD"])
    
    def get_alert_thresholds(self) -> Dict:
        """Obtenir les seuils d'alerte"""
        return self.settings.get("alerts", {}).get("thresholds", {
            "BTC": 2.0,
            "ETH": 3.0,
            "GOLD": 1.5
        })
    
    def get_price_intervals(self) -> Dict:
        """Obtenir les intervalles de prix"""
        prices = self.settings.get("prices", {})
        return {
            "check_hours": prices.get("check_interval_hours", 1),
            "save_hours": prices.get("save_interval_hours", 6)
        }
    
    def is_notification_enabled(self, channel: str) -> bool:
        """Vérifier si une notification est activée"""
        return self.settings.get("notifications", {}).get(channel, False)
    
    def update_settings(self, new_settings: Dict) -> bool:
        """Mettre à jour les paramètres"""
        try:
            # Fusionner avec les paramètres existants
            self.settings.update(new_settings)
            self._save_settings(self.settings)
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour settings: {e}")
            return False
    
    def add_channel(self, channel: str) -> bool:
        """Ajouter une chaîne Telegram"""
        try:
            channels = self.get_telegram_channels()
            if channel not in channels:
                channels.append(channel)
                self.settings["telegram"]["channels"] = channels
                self._save_settings(self.settings)
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur ajout canal: {e}")
            return False
    
    def remove_channel(self, channel: str) -> bool:
        """Supprimer une chaîne Telegram"""
        try:
            channels = self.get_telegram_channels()
            if channel in channels:
                channels.remove(channel)
                self.settings["telegram"]["channels"] = channels
                self._save_settings(self.settings)
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur suppression canal: {e}")
            return False
    
    def reload(self):
        """Recharger les paramètres"""
        self.settings = self._load_settings()