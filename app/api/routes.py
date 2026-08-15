from fastapi import APIRouter, HTTPException, Header
from typing import Dict, Any
import logging
import asyncio
import threading
from datetime import datetime

from app.core.config import config
from app.core.database import Database
from app.services.analyzer_service import AnalyzerService
from app.services.telegram_service import TelegramService
from app.services.notification_service import NotificationService
from app.services.price_recorder import PriceRecorder

logger = logging.getLogger(__name__)
router = APIRouter()

analyzer = AnalyzerService()
telegram = TelegramService()
notifier = NotificationService()
recorder = PriceRecorder()

bot_running = False

# ===== TÂCHE DE FOND POUR LA VÉRIFICATION 6H =====
async def price_check_and_save():
    """Verifier les prix toutes les 1h et enregistrer toutes les 6h"""
    from app.services.binance_service import BinanceService
    binance = BinanceService()
    
    check_count = 0
    first_run = True
    
    while True:
        try:
            if bot_running:
                logger.info("📊 Verification des prix...")
                prices = {}
                
                for symbol in ["BTC", "ETH", "GOLD"]:
                    price = await binance.get_price(symbol)
                    if price.get("success"):
                        details = await binance.get_price_with_details(symbol)
                        prices[symbol] = details
                        logger.info(f"📊 {symbol}: ${details['price']:,.2f} (24h: {details['change_24h']:+.2f}%)")
                
                if first_run:
                    await recorder.save_prices(prices)
                    first_run = False
                    logger.info("✅ Premier enregistrement effectue au demarrage !")
                    logger.info("⏳ Prochain enregistrement dans 6 heures...")
                else:
                    check_count += 1
                    if check_count >= 6:
                        await recorder.save_prices(prices)
                        check_count = 0
                        logger.info("✅ Prix enregistres (cycle 6h)")
                    else:
                        logger.info(f"⏳ Prochain enregistrement dans {6 - check_count} heure(s)")
                
                logger.info("✅ Verification terminee")
            else:
                logger.info("⏳ Bot arrete - Pas de verification")
            
            logger.info("⏳ Prochaine verification dans 1 heure...")
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await asyncio.sleep(60)

background_task = None

def start_background_tasks():
    global background_task
    if background_task is None or background_task.done():
        background_task = asyncio.create_task(price_check_and_save())
        logger.info("✅ Tache de verification horaire demarree")

# ===== AUTH =====
def check_auth(password: str = Header(default=None)):
    pass

# ============================================
# ROUTES PRINCIPALES
# ============================================

@router.get("/api/status")
async def get_status(password: str = Header(default=None)):
    check_auth(password)
    return {
        "running": bot_running,
        "telegram_connected": telegram.is_connected,
        "stats": analyzer.get_stats()
    }

@router.post("/api/start")
async def start_bot(password: str = Header(default=None)):
    global bot_running
    check_auth(password)
    
    if bot_running:
        return {"message": "Bot already running"}
    
    bot_running = True
    logger.info("🚀 Bot started")
    
    async def run_telegram():
        if await telegram.connect():
            await telegram.start_listening_multiple(analyzer.analyze_message)
    
    thread = threading.Thread(target=lambda: asyncio.run(run_telegram()))
    thread.daemon = True
    thread.start()
    
    start_background_tasks()
    
    return {"message": "Bot started", "running": True}

@router.post("/api/stop")
async def stop_bot(password: str = Header(default=None)):
    global bot_running
    check_auth(password)
    
    bot_running = False
    await telegram.disconnect()
    logger.info("🛑 Bot stopped")
    
    return {"message": "Bot stopped", "running": False}

# ============================================
# ROUTES ANALYSES
# ============================================

@router.post("/api/analyze")
async def analyze_text(request: Dict[str, str], password: str = Header(default=None)):
    check_auth(password)
    text = request.get("text", "")
    if not text:
        return {"success": False, "error": "No text provided"}
    
    result = await analyzer.analyze_message(text, "manual_" + str(hash(text)))
    if result:
        return {"success": True, "analysis": result}
    return {"success": False, "error": "Analysis failed"}

@router.get("/api/analyses")
async def get_analyses(password: str = Header(default=None)):
    check_auth(password)
    return {"analyses": Database.get_recent_analyses(20)}

# ============================================
# ROUTES CONFIGURATION
# ============================================

@router.post("/api/telegram/config")
async def set_telegram_config(request: Dict[str, Any], password: str = Header(default=None)):
    check_auth(password)
    config.TELEGRAM_API_ID = int(request.get("api_id", 0))
    config.TELEGRAM_API_HASH = request.get("api_hash", "")
    config.TELEGRAM_PHONE = request.get("phone", "")
    config.TELEGRAM_CHANNEL = request.get("channel", "")
    logger.info("Telegram config saved")
    return {"success": True}

@router.post("/api/deepseek/config")
async def set_deepseek_key(request: Dict[str, str], password: str = Header(default=None)):
    check_auth(password)
    config.DEEPSEEK_API_KEY = request.get("api_key", "")
    logger.info("DeepSeek key saved")
    return {"success": True}

@router.post("/api/binance/key")
async def set_binance_key(request: Dict[str, str], password: str = Header(default=None)):
    check_auth(password)
    config.BINANCE_API_KEY = request.get("api_key", "")
    logger.info("Binance key saved")
    return {"success": True}

@router.post("/api/binance/secret")
async def set_binance_secret(request: Dict[str, str], password: str = Header(default=None)):
    check_auth(password)
    config.BINANCE_API_SECRET = request.get("secret", "")
    logger.info("Binance secret saved")
    return {"success": True}

# ============================================
# ROUTES BINANCE / PRIX
# ============================================

@router.get("/api/prices")
async def get_prices(password: str = Header(default=None)):
    check_auth(password)
    from app.services.binance_service import BinanceService
    
    binance = BinanceService()
    prices = {}
    
    for symbol in ["BTC", "ETH", "GOLD"]:
        price_data = await binance.get_price(symbol)
        if price_data.get("success"):
            data_24h = await binance.get_24h_change(symbol)
            prices[symbol] = {
                "price": price_data["price"],
                "change_24h": data_24h.get("change_24h", 0) if data_24h.get("success") else 0,
                "change_7d": 0,
                "volume": data_24h.get("volume", 0) if data_24h.get("success") else 0
            }
        else:
            prices[symbol] = {"price": 0, "change_24h": 0, "change_7d": 0, "volume": 0}
    
    return {"success": True, "assets": prices}

@router.post("/api/check-prices")
async def check_prices_route(password: str = Header(default=None)):
    check_auth(password)
    from app.services.binance_service import BinanceService
    from app.services.notification_service import NotificationService
    
    binance = BinanceService()
    notifier = NotificationService()
    
    alerts = []
    for symbol in ["BTC", "ETH", "GOLD"]:
        alert = await binance.check_and_alert(symbol)
        if alert:
            alerts.append(alert)
            await notifier.send_price_alert(alert)
    
    return {"success": True, "alerts": alerts}

@router.post("/api/test-binance")
async def test_binance_route(password: str = Header(default=None)):
    check_auth(password)
    from app.services.binance_service import BinanceService
    
    binance = BinanceService()
    prices = {}
    
    for symbol in ["BTC", "ETH", "GOLD"]:
        price = await binance.get_price(symbol)
        if price.get("success"):
            prices[symbol] = price["price"]
    
    if prices:
        return {"success": True, "prices": prices}
    return {"success": False, "error": "Binance test failed"}

# ============================================
# ROUTES NOTIFICATIONS
# ============================================

@router.post("/api/telegram/test")
async def test_telegram_notification(password: str = Header(default=None)):
    check_auth(password)
    from app.services.notification_service import NotificationService
    
    notifier = NotificationService()
    result = await notifier.telegram.send_test()
    
    if result:
        return {"success": True, "message": "Test Telegram envoye !"}
    else:
        return {"success": False, "error": "Echec de l'envoi Telegram"}

@router.post("/api/test/telegram")
async def test_telegram_route(password: str = Header(default=None)):
    check_auth(password)
    from app.services.notification_service import NotificationService
    
    notifier = NotificationService()
    result = await notifier.telegram.send_test()
    
    if result:
        return {"success": True, "message": "Test Telegram envoye !"}
    return {"success": False, "error": "Echec de l'envoi Telegram"}

@router.post("/api/test/sendgrid")
async def test_sendgrid(password: str = Header(default=None)):
    check_auth(password)
    from app.services.sendgrid_service import SendGridService
    
    sg = SendGridService()
    result = await sg.send_test_email()
    
    if result:
        return {"success": True, "message": "Email SendGrid de test envoye !"}
    return {"success": False, "error": "Echec de l'envoi SendGrid"}

@router.post("/api/test/all")
async def test_all_notifications(password: str = Header(default=None)):
    check_auth(password)
    from app.services.notification_service import NotificationService
    
    notifier = NotificationService()
    result = await notifier.send_test()
    
    return {
        "success": result,
        "message": "Notifications de test envoyees !" if result else "Echec des notifications"
    }

@router.post("/api/weekly-report")
async def generate_weekly_report(password: str = Header(default=None)):
    check_auth(password)
    from app.services.binance_service import BinanceService
    from app.services.notification_service import NotificationService
    
    binance = BinanceService()
    notifier = NotificationService()
    
    report = await binance.get_detailed_weekly_report()
    await notifier.send_weekly_report(report)
    
    return {"success": True, "report": report}

# ============================================
# ROUTES PRICE HISTORY
# ============================================

@router.get("/api/price-history")
async def get_price_history(password: str = Header(default=None)):
    check_auth(password)
    history = recorder.get_history(100)
    daily_summary = recorder.get_daily_summary()
    
    return {
        "success": True,
        "total_records": len(history),
        "history": history,
        "daily_summary": daily_summary
    }

@router.get("/api/price-history/last/{symbol}")
async def get_last_price(symbol: str, password: str = Header(default=None)):
    check_auth(password)
    last = recorder.get_last_price(symbol.upper())
    
    if last:
        return {"success": True, "symbol": symbol.upper(), "data": last}
    return {"success": False, "error": "Aucune donnee trouvee"}

@router.post("/api/price-history/save")
async def save_prices_now(password: str = Header(default=None)):
    check_auth(password)
    from app.services.binance_service import BinanceService
    
    binance = BinanceService()
    prices = {}
    
    for symbol in ["BTC", "ETH", "GOLD"]:
        details = await binance.get_price_with_details(symbol)
        prices[symbol] = details
    
    result = await recorder.save_prices(prices)
    
    if result:
        return {"success": True, "message": "Prix enregistres avec succes"}
    return {"success": False, "error": "Erreur lors de l'enregistrement"}

# ============================================
# ROUTES LEARNING
# ============================================

@router.get("/api/learning/{asset}")
async def get_learning_summary(asset: str, password: str = Header(default=None)):
    check_auth(password)
    from app.services.historical_memory import HistoricalMemory
    
    memory = HistoricalMemory()
    summary = memory.get_learning_summary(asset.upper())
    
    return {"success": True, "summary": summary}

@router.get("/api/top-events/{asset}")
async def get_top_events(asset: str, password: str = Header(default=None)):
    check_auth(password)
    from app.services.historical_memory import HistoricalMemory
    
    memory = HistoricalMemory()
    events = memory.get_top_impact_events(asset.upper())
    
    return {"success": True, "events": events}

# ============================================
# ROUTE WHATSAPP
# ============================================

@router.post("/api/whatsapp/test")
async def test_whatsapp(password: str = Header(default=None)):
    check_auth(password)
    from app.services.notification_service import NotificationService
    
    notifier = NotificationService()
    result = await notifier.send_test_whatsapp()
    
    if result:
        return {"success": True, "message": "WhatsApp test envoye !"}
    else:
        return {"success": False, "error": "Echec de l'envoi WhatsApp"}

@router.get("/api/whatsapp/status")
async def whatsapp_status(password: str = Header(default=None)):
    check_auth(password)
    from app.core.config import config
    
    return {
        "enabled": config.WHATSAPP_ENABLED,
        "phone": config.WHATSAPP_PHONE,
        "configured": bool(config.WHATSAPP_API_KEY)
    }

# ============================================
# ROUTE NOTIFICATIONS STATUS
# ============================================

@router.get("/api/notifications/status")
async def notification_status(password: str = Header(default=None)):
    check_auth(password)
    from app.services.notification_service import NotificationService
    
    notifier = NotificationService()
    return {"success": True, "status": notifier.get_status()}

# ============================================
# PORTFOLIO ROUTES
# ============================================

@router.post("/api/portfolio/buy")
async def buy_asset(request: Dict, password: str = Header(default=None)):
    check_auth(password)
    from app.services.portfolio_service import PortfolioService
    
    asset = request.get("asset", "").upper()
    amount_tnd = request.get("amount_tnd", 0)
    fee = request.get("fee_percent", None)
    
    if asset not in ["BTC", "ETH", "GOLD"]:
        return {"success": False, "error": "Actif invalide. Utilisez BTC, ETH ou GOLD"}
    
    if amount_tnd <= 0:
        return {"success": False, "error": "Le montant doit être supérieur à 0"}
    
    portfolio = PortfolioService()
    result = portfolio.add_transaction(asset, amount_tnd, fee)
    
    return result

@router.get("/api/portfolio/summary")
async def get_portfolio_summary(password: str = Header(default=None)):
    check_auth(password)
    from app.services.portfolio_service import PortfolioService
    
    portfolio = PortfolioService()
    summary = portfolio.get_portfolio_summary()
    
    return {"success": True, "summary": summary}

@router.get("/api/portfolio/transactions")
async def get_portfolio_transactions(asset: str = None, limit: int = 20, password: str = Header(default=None)):
    check_auth(password)
    from app.services.portfolio_service import PortfolioService
    
    portfolio = PortfolioService()
    transactions = portfolio.get_transactions(asset, limit)
    
    return {"success": True, "transactions": transactions}

@router.post("/api/portfolio/rate")
async def set_tnd_usd_rate(request: Dict, password: str = Header(default=None)):
    check_auth(password)
    from app.services.portfolio_service import PortfolioService
    
    rate = request.get("rate", 0)
    if rate <= 0:
        return {"success": False, "error": "Le taux doit être supérieur à 0"}
    
    portfolio = PortfolioService()
    portfolio.set_tnd_usd_rate(rate)
    
    return {"success": True, "rate": rate}

@router.post("/api/portfolio/fee")
async def set_fee_percent(request: Dict, password: str = Header(default=None)):
    check_auth(password)
    from app.services.portfolio_service import PortfolioService
    
    fee = request.get("fee", 0)
    if fee < 0:
        return {"success": False, "error": "Les frais ne peuvent pas être négatifs"}
    
    portfolio = PortfolioService()
    portfolio.set_fee_percent(fee)
    
    return {"success": True, "fee": fee}

@router.get("/api/portfolio/weekly-report")
async def get_portfolio_weekly_report(password: str = Header(default=None)):
    check_auth(password)
    from app.services.portfolio_service import PortfolioService
    
    portfolio = PortfolioService()
    report = portfolio.get_weekly_report()
    
    return {"success": True, "report": report}

# ============================================
# ROUTES SETTINGS
# ============================================

@router.post("/api/settings/interval")
async def save_interval(request: Dict, password: str = Header(default=None)):
    """Sauvegarder l'intervalle de vérification des prix"""
    check_auth(password)
    
    interval_minutes = request.get("interval_minutes", 0)
    if interval_minutes <= 0:
        return {"success": False, "error": "L'intervalle doit être supérieur à 0"}
    
    config.PRICE_CHECK_INTERVAL = interval_minutes
    logger.info(f"✅ Intervalle mis à jour: {interval_minutes} minutes")
    
    return {"success": True, "message": f"Intervalle mis à jour: {interval_minutes} minutes"}

@router.post("/api/settings/threshold")
async def save_threshold(request: Dict, password: str = Header(default=None)):
    """Sauvegarder le seuil d'alerte de prix"""
    check_auth(password)
    
    threshold_percent = request.get("threshold_percent", 0)
    if threshold_percent <= 0:
        return {"success": False, "error": "Le seuil doit être supérieur à 0"}
    
    config.ALERT_THRESHOLD_PERCENT = threshold_percent
    logger.info(f"✅ Seuil mis à jour: {threshold_percent}%")
    
    return {"success": True, "message": f"Seuil mis à jour: {threshold_percent}%"}

@router.post("/api/settings/notifications")
async def save_notifications(request: Dict, password: str = Header(default=None)):
    """Sauvegarder les préférences de notifications"""
    check_auth(password)
    
    price = request.get("price", True)
    news = request.get("news", True)
    weekly = request.get("weekly", True)
    
    config.NOTIFY_PRICE = price
    config.NOTIFY_NEWS = news
    config.NOTIFY_WEEKLY = weekly
    
    logger.info(f"✅ Préférences notifications: Prix={price}, News={news}, Hebdo={weekly}")
    
    return {"success": True, "message": "Préférences de notification enregistrées"}

@router.get("/api/export-data")
async def export_data(password: str = Header(default=None)):
    """Exporter toutes les données du bot"""
    check_auth(password)
    
    try:
        import json
        from datetime import datetime
        
        analyses = Database.get_recent_analyses(1000)
        price_history = recorder.get_history(1000)
        
        data = {
            "export_date": datetime.now().isoformat(),
            "version": "3.0",
            "config": {
                "price_interval": getattr(config, 'PRICE_CHECK_INTERVAL', 30),
                "alert_threshold": getattr(config, 'ALERT_THRESHOLD_PERCENT', 5),
                "notifications": {
                    "price": getattr(config, 'NOTIFY_PRICE', True),
                    "news": getattr(config, 'NOTIFY_NEWS', True),
                    "weekly": getattr(config, 'NOTIFY_WEEKLY', True)
                }
            },
            "analyses": analyses,
            "price_history": price_history
        }
        
        return {"success": True, "data": data}
        
    except Exception as e:
        logger.error(f"Erreur export: {e}")
        return {"success": False, "error": str(e)}

@router.post("/api/reset")
async def reset_bot(password: str = Header(default=None)):
    """Réinitialiser le bot (supprime toutes les données)"""
    check_auth(password)
    
    try:
        import os
        import json
        import shutil
        
        deleted_files = []
        
        # 1. Supprimer TOUS les fichiers dans le dossier data/
        data_folder = "data"
        if os.path.exists(data_folder):
            for root, dirs, files in os.walk(data_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        deleted_files.append(file_path)
                        logger.info(f"🗑️ Fichier supprimé: {file_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ Impossible de supprimer {file_path}: {e}")
            
            # Supprimer le dossier data s'il est vide
            try:
                if os.path.exists(data_folder) and not os.listdir(data_folder):
                    os.rmdir(data_folder)
                    logger.info("🗑️ Dossier data supprimé")
            except:
                pass
        
        # 2. Supprimer les fichiers à la racine
        root_files = [
            "analyses.json",
            "portfolio_data.json",
            "price_history.json",
            "settings.json",
            "config.json",
            "portfolio.json"
        ]
        
        for file in root_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    deleted_files.append(file)
                    logger.info(f"🗑️ Fichier supprimé: {file}")
                except Exception as e:
                    logger.warning(f"⚠️ Impossible de supprimer {file}: {e}")
        
        # 3. Supprimer le dossier session (Telegram)
        session_folder = "session"
        if os.path.exists(session_folder):
            try:
                shutil.rmtree(session_folder)
                deleted_files.append(session_folder + "/")
                logger.info("🗑️ Dossier session supprimé")
            except Exception as e:
                logger.warning(f"⚠️ Impossible de supprimer session: {e}")
        
        # 4. Recréer le dossier data/
        os.makedirs("data", exist_ok=True)
        
        # 5. Créer un nouveau config.json avec les valeurs par défaut
        default_config = {
            "price_interval": 30,
            "alert_threshold": 5,
            "notifications": {
                "price": True,
                "news": True,
                "weekly": True
            },
            "telegram_channels": []
        }
        
        with open("config.json", 'w') as f:
            json.dump(default_config, f, indent=2)
        logger.info("✅ Nouveau config.json créé")
        
        # 6. Réinitialiser les services
        try:
            if 'analyzer' in globals():
                analyzer.clear_history()
        except:
            pass
        
        try:
            if 'recorder' in globals():
                recorder.clear_all()
        except:
            pass
        
        try:
            from app.services.portfolio_service import PortfolioService
            portfolio = PortfolioService()
            portfolio.reset_portfolio()
        except:
            pass
        
        logger.info(f"✅ Bot réinitialisé avec succès. {len(deleted_files)} fichiers supprimés.")
        return {
            "success": True, 
            "message": f"Bot réinitialisé avec succès. {len(deleted_files)} fichiers supprimés.",
            "deleted_files": deleted_files
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur reset: {e}")
        return {"success": False, "error": str(e)}

@router.get("/api/test-deepseek")
async def test_deepseek_route(password: str = Header(default=None)):
    """Tester l'API DeepSeek"""
    check_auth(password)
    
    try:
        from app.services.analyzer_service import AnalyzerService
        
        analyzer = AnalyzerService()
        result = await analyzer.analyze_message(
            "Bitcoin a augmenté de 5% cette semaine suite à l'annonce d'adoption institutionnelle.",
            "test_manual"
        )
        
        if result:
            return {"success": True, "analysis": result}
        return {"success": False, "error": "Échec de l'analyse DeepSeek"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================
# ROUTE D'AIDE POUR LES PARAMÈTRES
# ============================================

@router.get("/api/settings/help")
async def get_settings_help(password: str = Header(default=None)):
    """Obtenir de l'aide sur les paramètres disponibles"""
    check_auth(password)
    
    return {
        "success": True,
        "available_settings": {
            "price_interval": {
                "type": "integer",
                "description": "Intervalle en minutes entre les vérifications de prix",
                "default": 30,
                "min": 1,
                "max": 1440
            },
            "alert_threshold": {
                "type": "float",
                "description": "Seuil de variation de prix en pourcentage pour déclencher une alerte",
                "default": 5.0,
                "min": 0.5,
                "max": 50.0
            },
            "notifications": {
                "type": "object",
                "description": "Activer/désactiver les notifications",
                "fields": {
                    "price": "Alertes de prix",
                    "news": "Alertes d'actualités",
                    "weekly": "Rapport hebdomadaire"
                }
            }
        }
    }

# ============================================
# ROUTES CHAÎNES TELEGRAM
# ============================================

@router.get("/api/settings/channels")
async def get_channels(password: str = Header(default=None)):
    """Obtenir la liste des chaînes Telegram surveillées"""
    check_auth(password)
    
    import json
    import os
    
    config_file = "config.json"
    config_data = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except:
            config_data = {}
    
    channels = config_data.get('telegram_channels', [])
    return {"success": True, "channels": channels}

@router.post("/api/settings/channels/add")
async def add_channel(request: Dict, password: str = Header(default=None)):
    """Ajouter une chaîne Telegram à surveiller"""
    check_auth(password)
    
    import json
    import os
    
    channel = request.get("channel", "").strip()
    if not channel:
        return {"success": False, "error": "Nom de chaîne requis"}
    
    if not channel.startswith('@'):
        channel = '@' + channel
    
    config_file = "config.json"
    config_data = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except:
            config_data = {}
    
    if 'telegram_channels' not in config_data:
        config_data['telegram_channels'] = []
    
    for ch in config_data['telegram_channels']:
        if ch['channel'].lower() == channel.lower():
            return {"success": False, "error": "Cette chaîne est déjà dans la liste"}
    
    config_data['telegram_channels'].append({
        "channel": channel,
        "active": True
    })
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    logger.info(f"✅ Chaîne Telegram ajoutée: {channel}")
    return {"success": True, "message": f"Chaîne {channel} ajoutée"}

@router.post("/api/settings/channels/remove")
async def remove_channel(request: Dict, password: str = Header(default=None)):
    """Supprimer une chaîne Telegram"""
    check_auth(password)
    
    import json
    import os
    
    index = request.get("index", -1)
    if index < 0:
        return {"success": False, "error": "Index invalide"}
    
    config_file = "config.json"
    if not os.path.exists(config_file):
        return {"success": False, "error": "Aucune configuration trouvée"}
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except:
        return {"success": False, "error": "Erreur de lecture du fichier de configuration"}
    
    channels = config_data.get('telegram_channels', [])
    if index >= len(channels):
        return {"success": False, "error": "Chaîne non trouvée"}
    
    removed_channel = channels.pop(index)['channel']
    config_data['telegram_channels'] = channels
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    logger.info(f"✅ Chaîne Telegram supprimée: {removed_channel}")
    return {"success": True, "message": f"Chaîne {removed_channel} supprimée"}

@router.post("/api/settings/channels/toggle")
async def toggle_channel(request: Dict, password: str = Header(default=None)):
    """Activer/Désactiver une chaîne Telegram"""
    check_auth(password)
    
    import json
    import os
    
    index = request.get("index", -1)
    if index < 0:
        return {"success": False, "error": "Index invalide"}
    
    config_file = "config.json"
    if not os.path.exists(config_file):
        return {"success": False, "error": "Aucune configuration trouvée"}
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except:
        return {"success": False, "error": "Erreur de lecture du fichier de configuration"}
    
    channels = config_data.get('telegram_channels', [])
    if index >= len(channels):
        return {"success": False, "error": "Chaîne non trouvée"}
    
    channels[index]['active'] = not channels[index]['active']
    new_status = "activée" if channels[index]['active'] else "désactivée"
    
    config_data['telegram_channels'] = channels
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    logger.info(f"✅ Chaîne {channels[index]['channel']} {new_status}")
    return {"success": True, "message": f"Chaîne {new_status}"}

@router.post("/api/settings/channels/reload")
async def reload_channels(password: str = Header(default=None)):
    """Recharger les chaînes Telegram sans redémarrer le bot"""
    check_auth(password)
    
    try:
        global telegram
        result = await telegram.reload_channels()
        
        if result:
            logger.info("✅ Chaînes rechargées avec succès")
            return {"success": True, "message": "Chaînes rechargées avec succès"}
        else:
            return {"success": False, "error": "Erreur lors du rechargement des chaînes"}
            
    except Exception as e:
        logger.error(f"❌ Erreur rechargement: {e}")
        return {"success": False, "error": str(e)}