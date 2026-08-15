import requests
import logging
from datetime import datetime

from app.core.config import config

logger = logging.getLogger(__name__)

class TelegramNotify:
    """Service de notifications via Telegram"""
    
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = config.TELEGRAM_NOTIFY_ENABLED if hasattr(config, 'TELEGRAM_NOTIFY_ENABLED') else True
    
    async def send_message(self, message: str) -> bool:
        """Envoyer un message Telegram"""
        if not self.enabled:
            logger.info("📝 Telegram notifications desactivees")
            return False
        
        if not self.bot_token or not self.chat_id:
            logger.error("❌ Telegram: Token ou Chat_ID manquant")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            response = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }, timeout=30)
            
            if response.status_code == 200:
                logger.info("✅ Telegram envoye")
                return True
            else:
                logger.error(f"❌ Erreur Telegram: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur envoi Telegram: {e}")
            return False
    
    async def send_alert(self, symbol: str, old_price: float, current_price: float, change: float) -> bool:
        """Envoyer une alerte de prix"""
        emoji = "🚀" if change > 0 else "📉"
        direction = "HAUSSE" if change > 0 else "BAISSE"
        
        message = f"""
<b>{emoji} ALERTE PRIX {symbol} - {direction} {abs(change):.2f}%</b>

💰 Ancien prix: ${old_price:,.2f}
💰 Prix actuel: ${current_price:,.2f}
📈 Variation: {change:+.2f}%

⚠️ Ceci est une alerte de prix uniquement.
⚠️ Ce n'est PAS une recommandation d'achat/vente.

📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        """.strip()
        
        return await self.send_message(message)
    
    async def send_weekly_report(self, report: dict) -> bool:
        """Envoyer le rapport hebdomadaire"""
        message = f"""
📊 <b>RAPPORT HEBDOMADAIRE</b>
{'='*30}
📅 {datetime.now().strftime('%d/%m/%Y')}

"""
        for symbol, data in report.get("assets", {}).items():
            if "error" in data:
                continue
            
            change = data.get('change_7d', 0)
            emoji = "✅" if change > 0 else "❌" if change < 0 else "⚪"
            
            message += f"""
<b>{symbol}</b>
   • Début: ${data.get('start_price', 0):,.2f}
   • Actuel: ${data.get('end_price', 0):,.2f}
   • Variation: {change:+.2f}%
   • 📈 Max: ${data.get('max_price', 0):,.2f}
   • 📉 Min: ${data.get('min_price', 0):,.2f}
   • Performance: {emoji}
"""
        
        message += f"""
{'='*30}
🤖 Genere par LongTerm AI Bot
⚠️ Ce rapport est une analyse, pas une prediction.
        """.strip()
        
        return await self.send_message(message)
    
    async def send_test(self) -> bool:
        """Envoyer un message de test"""
        test_msg = f"""
🔔 <b>TEST DE NOTIFICATION</b>

✅ Votre bot LongTerm AI est configure avec Telegram !

📅 Test effectue a: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🤖 Bot v3.0

💡 Vous recevrez desormais :
   • Alertes de prix
   • Analyses importantes
   • Rapports hebdomadaires
        """.strip()
        
        return await self.send_message(test_msg)