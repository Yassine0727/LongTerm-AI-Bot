from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn
import logging
import os
import asyncio
import threading
import secrets
import base64
import json
from datetime import datetime

# ===== LOGGER - DOIT ÊTRE ICI AVANT SUPABASE =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== SUPABASE (OPTIONNEL - VIA REST API) =====
try:
    from app.supabase_storage import SupabaseStorage
    supabase_storage = SupabaseStorage()
    if supabase_storage.connected:
        logger.info("✅ Supabase connecté (via REST API)")
    else:
        supabase_storage = None
        logger.warning("⚠️ Supabase non connecté, fallback sur JSON")
except ImportError:
    supabase_storage = None
    logger.warning("⚠️ SupabaseStorage non disponible, fallback sur JSON")
except Exception as e:
    supabase_storage = None
    logger.warning(f"⚠️ Erreur Supabase: {e}, fallback sur JSON")

app = FastAPI(title="LongTerm AI Bot", version="3.0")

# ===== CRÉATION DU DOSSIER DATA =====
os.makedirs("data", exist_ok=True)

# ===== INITIALISATION DES FICHIERS =====
def init_data_files():
    """Initialise les fichiers de données s'ils n'existent pas"""
    try:
        # analyses_history.json
        history_file = "data/analyses_history.json"
        if not os.path.exists(history_file):
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            logger.info("✅ Fichier analyses_history.json créé")
        
        # stats.json
        stats_file = "data/stats.json"
        if not os.path.exists(stats_file):
            default_stats = {
                "total_analyses": 0,
                "total_alerts": 0,
                "total_reports": 0,
                "last_update": datetime.now().isoformat()
            }
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(default_stats, f, indent=2, ensure_ascii=False)
            logger.info("✅ Fichier stats.json créé")
        
        return True
    except Exception as e:
        logger.error(f"❌ Erreur création fichiers: {e}")
        return False

# Appeler au démarrage
init_data_files()

# ===== FONCTIONS DE LECTURE/ÉCRITURE =====

def load_stats():
    """Charge les statistiques depuis stats.json"""
    stats_file = "data/stats.json"
    default_stats = {
        "total_analyses": 0,
        "total_alerts": 0,
        "total_reports": 0,
        "last_update": datetime.now().isoformat()
    }
    
    if os.path.exists(stats_file):
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
                # S'assurer que toutes les clés existent
                for key in default_stats:
                    if key not in stats:
                        stats[key] = default_stats[key]
                return stats
        except Exception as e:
            logger.error(f"❌ Erreur lecture stats.json: {e}")
            return default_stats
    
    return default_stats

def save_stats(stats):
    """Sauvegarde les statistiques dans stats.json"""
    try:
        with open("data/stats.json", 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde stats.json: {e}")
        return False

def load_history():
    """Charge l'historique des analyses depuis analyses_history.json"""
    history_file = "data/analyses_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Erreur lecture historique: {e}")
            return []
    
    # Si le fichier n'existe pas, le créer
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        logger.info("✅ Fichier analyses_history.json créé")
    except Exception as e:
        logger.error(f"❌ Erreur création historique: {e}")
    
    return []

def save_history(history):
    """Sauvegarde l'historique des analyses dans analyses_history.json"""
    try:
        with open("data/analyses_history.json", 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde historique: {e}")
        return False

def add_analysis_to_history(analysis_data):
    """Ajoute une analyse à l'historique"""
    try:
        history = load_history()
        history.append(analysis_data)
        # Garder seulement les 200 dernières analyses
        if len(history) > 200:
            history = history[-200:]
        return save_history(history)
    except Exception as e:
        logger.error(f"❌ Erreur ajout historique: {e}")
        return False

# ===== CHARGER LES STATS AU DÉMARRAGE =====
stats_data = load_stats()
total_analyses = stats_data.get("total_analyses", 0)
total_alerts = stats_data.get("total_alerts", 0)
total_reports = stats_data.get("total_reports", 0)

logger.info(f"📊 Statistiques chargées: Analyses={total_analyses}, Alertes={total_alerts}, Reports={total_reports}")
logger.info(f"📊 Historique chargé: {len(load_history())} analyses")

# ===== CORS CONFIGURATION SÉCURISÉE =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ===== SÉCURITÉ : HOSTS AUTORISÉS =====
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# ===== ROUTES =====
from app.api.routes import router
from app.history_page import router as history_router

app.include_router(router)
app.include_router(history_router)

# ===== AUTHENTIFICATION =====
security = HTTPBasic()

# ===== CHANGEZ CES IDENTIFIANTS ! =====
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
SECRET_KEY = "votre_cle_secrete_tres_longue_et_aleatoire"

# ===== MIDDLEWARE DE SÉCURITÉ POUR LES API =====
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Middleware simplifié - sans redirection vers login"""
    
    public_routes = ["/api/ping", "/telegram-login", "/", "/settings", "/history", "/web"]
    
    if request.url.path in public_routes:
        return await call_next(request)
    
    if request.url.path.startswith("/api/telegram/auth"):
        return await call_next(request)
    
    if request.url.path.startswith("/api/"):
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentification requise", "error": "Unauthorized"}
            )
        
        try:
            auth = auth_header.split(" ")[1]
            decoded = base64.b64decode(auth).decode("utf-8")
            username, password = decoded.split(":")
            
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                return await call_next(request)
            else:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Identifiants incorrects", "error": "Unauthorized"}
                )
        except:
            return JSONResponse(
                status_code=401,
                content={"detail": "Format d'authentification invalide", "error": "Unauthorized"}
            )
    
    return await call_next(request)

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

def check_auth_header(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return False
    
    try:
        auth = auth_header.split(" ")[1]
        decoded = base64.b64decode(auth).decode("utf-8")
        username, password = decoded.split(":")
        return username == ADMIN_USERNAME and password == ADMIN_PASSWORD
    except:
        return False

# ===== ROUTE PUBLIQUE POUR UPTIME ROBOT =====
@app.api_route("/api/ping", methods=["GET", "HEAD"])
async def ping(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0",
        "message": "LongTerm AI Bot is alive!"
    }

# ============================================
# CONFIGURATION ET RECHARGEMENT
# ============================================

CONFIG_FILE = "config.json"

def load_config():
    default_config = {
        "price_interval": 30,
        "alert_threshold": 5,
        "telegram_channels": [],
        "notifications": {
            "price": True,
            "news": True,
            "weekly": True
        },
        "telegram": {
            "api_id": "",
            "api_hash": "",
            "phone": "",
            "channel": ""
        }
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except Exception as e:
            logger.error(f"❌ Erreur lecture config.json: {e}")
            return default_config
    
    return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde config.json: {e}")
        return False

config_data = load_config()

# ============================================
# IMPORT DU SERVICE TELEGRAM
# ============================================

try:
    from app.services.telegram_service import TelegramService
    TELEGRAM_AVAILABLE = True
    logger.info("✅ TelegramService chargé avec succès")
except ImportError as e:
    TELEGRAM_AVAILABLE = False
    logger.error(f"❌ TelegramService non trouvé: {e}")

# ============================================
# INITIALISATION DES SERVICES
# ============================================

try:
    from app.services.ai_service import AIService
    ai_service = AIService()
    logger.info("✅ AIService chargé")
except ImportError as e:
    ai_service = None
    logger.error(f"❌ AIService non trouvé: {e}")

telegram_service = None
telegram_task = None
telegram_running = False

def get_telegram_service():
    global telegram_service
    if telegram_service is None and TELEGRAM_AVAILABLE:
        telegram_service = TelegramService()
        logger.info("✅ Instance TelegramService créée")
    return telegram_service

# ============================================
# AUTHENTIFICATION TELEGRAM VIA WEB
# ============================================

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

telegram_auth_client = None
telegram_auth_phone = None

@app.get("/telegram-login")
async def telegram_login_page():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connexion Telegram</title>
        <style>
            body { background: #0a0a0a; color: #e5e5e5; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
            .container { background: #1a1a1a; padding: 40px; border-radius: 16px; border: 1px solid #333; max-width: 400px; width: 100%; text-align: center; }
            h1 { color: #f7931a; margin-bottom: 10px; }
            .subtitle { color: #888; font-size: 14px; margin-bottom: 30px; }
            .btn-telegram { background: #0088cc; color: white; border: none; padding: 14px 30px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%; transition: all 0.3s; }
            .btn-telegram:hover { background: #006699; transform: scale(1.02); }
            .btn-telegram:disabled { opacity: 0.5; cursor: not-allowed; }
            .input-group { margin: 15px 0; display: none; }
            .input-group.show { display: block; }
            .input-group input { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #333; background: #0a0a0a; color: white; font-size: 16px; text-align: center; }
            .input-group input:focus { outline: none; border-color: #f7931a; }
            .status { margin-top: 15px; padding: 10px; border-radius: 8px; font-size: 14px; }
            .status.success { background: #064e3b; color: #34d399; }
            .status.error { background: #4a1a1a; color: #f87171; }
            .status.info { background: #1a2a4a; color: #60a5fa; }
            .back-link { display: block; margin-top: 20px; color: #888; text-decoration: none; font-size: 14px; }
            .back-link:hover { color: #f7931a; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Telegram</h1>
            <p class="subtitle">Connectez votre compte Telegram</p>
            <button class="btn-telegram" onclick="startAuth()" id="btnStart">📱 Se connecter avec Telegram</button>
            <div class="input-group" id="codeGroup">
                <p style="color:#888;font-size:14px;">Code reçu sur Telegram</p>
                <input type="text" id="codeInput" placeholder="Ex: 12345" maxlength="10">
                <button class="btn-telegram" onclick="submitCode()" style="margin-top:10px;background:#f7931a;">✅ Valider le code</button>
            </div>
            <div id="status"></div>
            <a href="/" class="back-link">← Retour au Dashboard</a>
        </div>
        <script>
            async function startAuth() {
                const btn = document.getElementById('btnStart');
                const status = document.getElementById('status');
                btn.disabled = true;
                btn.textContent = '⏳ Envoi du code...';
                try {
                    const response = await fetch('/api/telegram/auth/start', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
                    const data = await response.json();
                    if (data.success) {
                        status.className = 'status info';
                        status.textContent = '✅ Code envoyé ! Vérifiez Telegram';
                        document.getElementById('codeGroup').classList.add('show');
                        btn.textContent = '📱 Se connecter avec Telegram';
                        btn.disabled = false;
                    } else {
                        status.className = 'status error';
                        status.textContent = '❌ ' + data.error;
                        btn.textContent = '📱 Se connecter avec Telegram';
                        btn.disabled = false;
                    }
                } catch(e) {
                    status.className = 'status error';
                    status.textContent = '❌ Erreur: ' + e.message;
                    btn.textContent = '📱 Se connecter avec Telegram';
                    btn.disabled = false;
                }
            }
            async function submitCode() {
                const code = document.getElementById('codeInput').value;
                const status = document.getElementById('status');
                const btn = document.querySelector('.btn-telegram[onclick="submitCode()"]');
                if (!code) {
                    status.className = 'status error';
                    status.textContent = '❌ Entrez le code reçu';
                    return;
                }
                btn.disabled = true;
                btn.textContent = '⏳ Connexion...';
                try {
                    const response = await fetch('/api/telegram/auth/verify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: code }) });
                    const data = await response.json();
                    if (data.success) {
                        status.className = 'status success';
                        status.textContent = '✅ ' + data.message + ' 🎉';
                        document.getElementById('codeGroup').classList.remove('show');
                        btn.textContent = '✅ Connecté !';
                        setTimeout(() => { window.location.href = '/'; }, 2000);
                    } else {
                        status.className = 'status error';
                        status.textContent = '❌ ' + data.error;
                        btn.textContent = '✅ Valider le code';
                        btn.disabled = false;
                    }
                } catch(e) {
                    status.className = 'status error';
                    status.textContent = '❌ Erreur: ' + e.message;
                    btn.textContent = '✅ Valider le code';
                    btn.disabled = false;
                }
            }
        </script>
    </body>
    </html>
    '''
    return HTMLResponse(html)

@app.post("/api/telegram/auth/start")
async def telegram_auth_start():
    global telegram_auth_client, telegram_auth_phone
    try:
        service = get_telegram_service()
        if not service:
            return {"success": False, "error": "Service non disponible"}
        telegram_auth_client = TelegramClient("session/telegram_render", service.api_id, service.api_hash)
        telegram_auth_phone = service.phone
        await telegram_auth_client.connect()
        await telegram_auth_client.send_code_request(telegram_auth_phone)
        return {"success": True, "message": "Code envoyé !"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/telegram/auth/verify")
async def telegram_auth_verify(data: dict):
    global telegram_auth_client, telegram_auth_phone
    try:
        code = data.get("code", "").strip()
        if not code:
            return {"success": False, "error": "Code requis"}
        if telegram_auth_client is None:
            return {"success": False, "error": "Session expirée, recommencez"}
        await telegram_auth_client.sign_in(telegram_auth_phone, code)
        await telegram_auth_client.disconnect()
        logger.info("🔄 Redémarrage du service Telegram...")
        await stop_telegram_service()
        await start_telegram_service()
        return {"success": True, "message": "Connexion réussie ! Bot redémarré"}
    except SessionPasswordNeededError:
        return {"success": False, "error": "Mot de passe 2FA requis"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

# ===== GESTIONNAIRES DE MESSAGES =====

async def handle_telegram_message(text: str, message_id: str, date):
    try:
        logger.info(f"📩 MESSAGE REÇU - ID: {message_id}")
        logger.info(f"📝 Contenu: {text[:200]}...")
        
        if text.startswith('/'):
            await handle_telegram_command(text, message_id)
        else:
            await process_market_analysis(text, message_id, date)
            
    except Exception as e:
        logger.error(f"❌ Erreur traitement message: {e}")

async def handle_telegram_command(text: str, message_id: str):
    global total_reports, stats_data
    
    try:
        command = text.strip().lower()
        service = get_telegram_service()
        if not service or not service.is_connected:
            logger.warning("⚠️ Service Telegram non connecté")
            return
        
        channel = config_data.get("telegram", {}).get("channel")
        if not channel:
            channel = os.getenv("TELEGRAM_CHANNEL", "@Trading_longterme_bot")
        
        logger.info(f"📟 Commande reçue: {command}")
        
        if command == '/start':
            await service.client.send_message(
                channel,
                "🤖 **LongTerm AI Bot**\n\n"
                "✅ Bot actif et à l'écoute !\n\n"
                "Commandes disponibles :\n"
                "• `/status` - État du bot\n"
                "• `/prices` - Prix des actifs\n"
                "• `/portfolio` - Portefeuille\n"
                "• `/analyze` - Analyser les marchés\n"
                "• `/weekly_report` - Rapport hebdomadaire\n"
                "• `/help` - Aide"
            )
            logger.info(f"✅ Commande /start envoyée à {channel}")
            
        elif command == '/status':
            status = "🟢 **En ligne**" if telegram_running else "🔴 **Hors ligne**"
            
            # Récupérer les stats (Supabase ou local)
            if supabase_storage and supabase_storage.connected:
                stats = supabase_storage.get_stats()
                total_analyses = stats.get('total_analyses', 0)
                total_alerts = stats.get('total_alerts', 0)
                storage_type = "Supabase"
            else:
                stats_data = load_stats()
                total_analyses = stats_data.get("total_analyses", 0)
                total_alerts = stats_data.get("total_alerts", 0)
                storage_type = "Local JSON"
            
            await service.client.send_message(
                channel,
                f"📊 **État du bot**\n\n"
                f"Statut : {status}\n"
                f"Canaux écoutés : {len(service.channel_handlers) if hasattr(service, 'channel_handlers') else 0}\n"
                f"Messages traités : {len(service.processed_messages) if hasattr(service, 'processed_messages') else 0}\n"
                f"📈 Analyses totales : {total_analyses}\n"
                f"🔔 Alertes : {total_alerts}\n"
                f"📊 Rapports : {total_reports}\n"
                f"📁 Stockage : {storage_type}"
            )
            logger.info("✅ Commande /status envoyée")
            
        elif command == '/prices':
            await service.client.send_message(
                channel,
                "💰 **Prix actuels**\n\n"
                "• Bitcoin (BTC) : $65,432\n"
                "• Ethereum (ETH) : $3,456\n"
                "• Gold (XAU) : $2,050"
            )
            logger.info("✅ Commande /prices envoyée")
            
        elif command == '/portfolio':
            await service.client.send_message(
                channel,
                "💼 **Portefeuille**\n\n"
                "• BTC : 0.5 (≈ $32,716)\n"
                "• ETH : 2.0 (≈ $6,912)\n"
                "• Total : $39,628\n\n"
                "📈 ROI : +5.2%"
            )
            logger.info("✅ Commande /portfolio envoyée")
            
        elif command == '/analyze':
            total_reports += 1
            stats_data["total_reports"] = total_reports
            stats_data["last_update"] = datetime.now().isoformat()
            save_stats(stats_data)
            await service.client.send_message(
                channel,
                "🔍 **Analyse des marchés en cours...**\n\n"
                f"📊 Rapports générés : {total_reports}"
            )
            logger.info("✅ Commande /analyze envoyée")
            
        elif command == '/weekly_report':
            total_reports += 1
            stats_data["total_reports"] = total_reports
            stats_data["last_update"] = datetime.now().isoformat()
            save_stats(stats_data)
            await service.client.send_message(
                channel,
                f"📊 **Rapport Hebdomadaire**\n\n"
                f"📈 Analyses totales : {total_analyses}\n"
                f"🔔 Alertes : {total_alerts}\n"
                f"📊 Rapports générés : {total_reports}\n\n"
                f"✅ Bot actif 24h/7j"
            )
            logger.info("✅ Commande /weekly_report envoyée")
            
        elif command == '/help':
            await service.client.send_message(
                channel,
                "📚 **Aide**\n\n"
                "Commandes disponibles :\n"
                "• `/start` - Démarrer le bot\n"
                "• `/status` - État du bot\n"
                "• `/prices` - Prix des actifs\n"
                "• `/portfolio` - Voir le portefeuille\n"
                "• `/analyze` - Analyser les marchés\n"
                "• `/weekly_report` - Rapport hebdomadaire\n"
                "• `/help` - Aide"
            )
            logger.info("✅ Commande /help envoyée")
            
        else:
            await service.client.send_message(
                channel,
                f"❌ Commande inconnue. Tapez `/help` pour voir les commandes disponibles."
            )
            logger.info(f"❌ Commande inconnue: {command}")
            
    except Exception as e:
        logger.error(f"❌ Erreur commande: {e}")

async def process_market_analysis(text: str, message_id: str, date):
    global total_analyses, total_alerts, stats_data
    
    try:
        logger.info(f"📊 Analyse du message: {text[:100]}...")
        logger.info(f"🆔 Message ID: {message_id}")
        
        # === INCÉMENTER LE COMPTEUR ===
        total_analyses += 1
        stats_data["total_analyses"] = total_analyses
        stats_data["last_update"] = datetime.now().isoformat()
        save_stats(stats_data)
        logger.info(f"📊 Total analyses: {total_analyses}")
        
        # === PRÉPARER L'ANALYSE ===
        analysis_data = {
            "id": message_id,
            "timestamp": datetime.now().isoformat(),
            "text": text[:300],
            "analysis": {},
            "message_id": message_id
        }
        
        # === ANALYSE AVEC DEEPSEEK ===
        if ai_service:
            try:
                result = await ai_service.analyze(text)
                logger.info(f"🔍 Résultat DeepSeek: {result}")
            except Exception as e:
                logger.error(f"❌ Erreur DeepSeek: {e}")
                result = None
        else:
            result = None
        
        # === PRÉPARER L'ANALYSE ===
        if result and result.get("success"):
            analysis = result.get("analysis", {})
            score = analysis.get("score", 0)
            
            if score >= 7:
                total_alerts += 1
                stats_data["total_alerts"] = total_alerts
                save_stats(stats_data)
                logger.info(f"🔔 Alerte ! Score: {score}/10")
            
            analysis_data["analysis"] = {
                "asset": analysis.get("asset", "OTHER"),
                "impact": analysis.get("impact", "neutral"),
                "score": score,
                "time_horizon": analysis.get("time_horizon", "medium_term"),
                "summary": analysis.get("summary", "") or analysis.get("reason", ""),
                "confidence": analysis.get("confidence", "medium")
            }
            analysis_data["asset"] = analysis.get("asset", "OTHER")
            analysis_data["impact"] = analysis.get("impact", "neutral")
            analysis_data["score"] = score
            analysis_data["summary"] = analysis.get("summary", "") or analysis.get("reason", "")
            
        else:
            analysis_data["analysis"] = {
                "asset": "OTHER",
                "impact": "neutral",
                "score": 0,
                "time_horizon": "unknown",
                "summary": text[:200],
                "confidence": "low"
            }
            analysis_data["asset"] = "OTHER"
            analysis_data["impact"] = "neutral"
            analysis_data["score"] = 0
            analysis_data["summary"] = text[:200]
        
        # === SAUVEGARDER DANS SUPABASE ===
        supabase_success = False
        if supabase_storage and supabase_storage.connected:
            logger.info("💾 Sauvegarde sur Supabase...")
            supabase_success = supabase_storage.save_analysis(analysis_data)
            if supabase_success:
                logger.info("✅ Analyse sauvegardée sur Supabase")
            else:
                logger.error("❌ Échec de la sauvegarde sur Supabase")
        
        # === SAUVEGARDER DANS L'HISTORIQUE LOCAL (toujours) ===
        add_analysis_to_history(analysis_data)
        logger.info(f"✅ Analyse sauvegardée dans l'historique local (total: {total_analyses})")
        
        # === CONSTRUIRE LE MESSAGE À ENVOYER ===
        if result and result.get("success"):
            analysis = result.get("analysis", {})
            score = analysis.get("score", 0)
            emoji = "🟢" if analysis.get('impact') == 'positive' else "🔴" if analysis.get('impact') == 'negative' else "🟡"
            message = f"""{emoji} **Analyse LongTerm AI**

**Actif:** {analysis.get('asset', 'OTHER')}
**Impact:** {analysis.get('impact', 'neutral')} (Score: {score}/10)
**Horizon:** {analysis.get('time_horizon', 'medium_term')}
**Confiance:** {analysis.get('confidence', 'medium')}

**Résumé:**
{analysis.get('summary', '') or analysis.get('reason', '')}

**Analyse détaillée:**
{analysis.get('detailed_analysis', '')}

**Impact par actif:**
• **BTC:** {analysis.get('btc_impact', 'Non spécifié')}
• **ETH:** {analysis.get('eth_impact', 'Non spécifié')}
• **GOLD:** {analysis.get('gold_impact', 'Non spécifié')}

📁 Stockage: {'☁️ Supabase' if supabase_success else '💾 Local'}"""
        else:
            message = f"""📩 **Nouveau message analysé**

**ID:** {message_id}
**Contenu:** {text[:200]}...

⚠️ Analyse détaillée non disponible

📁 Stockage: {'☁️ Supabase' if supabase_success else '💾 Local'}"""
        
        # === ENVOYER LA NOTIFICATION ===
        service = get_telegram_service()
        if service and service.is_connected:
            channel = config_data.get("telegram", {}).get("channel")
            if not channel:
                channel = os.getenv("TELEGRAM_CHANNEL", "@Trading_longterme_bot")
            
            await service.client.send_message(channel, message)
            logger.info(f"✅ Notification envoyée à {channel}")
        else:
            logger.error("❌ Service Telegram non connecté")
        
        logger.info(f"✅ Message analysé - ID: {message_id}")
        
    except Exception as e:
        logger.error(f"❌ Erreur analyse: {e}")
        import traceback
        logger.error(traceback.format_exc())

# ===== SERVICE TELEGRAM =====

async def start_telegram_service():
    global telegram_running, telegram_task, telegram_service
    
    if not TELEGRAM_AVAILABLE:
        logger.error("❌ TelegramService non disponible")
        return False
    
    try:
        logger.info("🚀 Démarrage du service Telegram...")
        
        service = get_telegram_service()
        if not service:
            logger.error("❌ Impossible de créer le service Telegram")
            return False
        
        logger.info("📡 Connexion à Telegram...")
        if not await service.connect():
            logger.error("❌ Impossible de se connecter à Telegram")
            return False
        
        logger.info("✅ Connecté à Telegram avec succès")
        
        telegram_running = True
        logger.info("👀 Démarrage de l'écoute Telegram...")
        
        telegram_task = asyncio.create_task(
            service.start_listening_multiple(handle_telegram_message)
        )
        
        logger.info("✅ Service Telegram démarré avec succès !")
        channels = config_data.get("telegram_channels", [])
        if channels:
            logger.info(f"📡 Canaux configurés: {channels}")
        else:
            logger.warning("⚠️ Aucun canal configuré dans config.json")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur démarrage: {e}")
        telegram_running = False
        return False

async def stop_telegram_service():
    global telegram_running, telegram_task, telegram_service
    
    try:
        logger.info("🛑 Arrêt du service Telegram...")
        telegram_running = False
        
        if telegram_task and not telegram_task.done():
            telegram_task.cancel()
            try:
                await telegram_task
            except asyncio.CancelledError:
                pass
        
        if telegram_service:
            await telegram_service.disconnect()
        
        logger.info("✅ Service Telegram arrêté")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur arrêt: {e}")
        return False

# ===== ÉVÉNEMENTS DE DÉMARRAGE =====

@app.on_event("startup")
async def startup_event():
    global config_data, stats_data, total_analyses, total_alerts, total_reports
    
    logger.info("=" * 50)
    logger.info("🚀 LANCEMENT LONGTEM AI BOT")
    logger.info("=" * 50)
    
    config_data = load_config()
    
    stats_data = load_stats()
    total_analyses = stats_data.get("total_analyses", 0)
    total_alerts = stats_data.get("total_alerts", 0)
    total_reports = stats_data.get("total_reports", 0)
    
    history_count = len(load_history())
    
    logger.info(f"📊 Statistiques: Analyses={total_analyses}, Alertes={total_alerts}, Reports={total_reports}")
    logger.info(f"📊 Historique: {history_count} analyses enregistrées")
    
    # Vérifier Supabase
    if supabase_storage and supabase_storage.connected:
        logger.info("✅ Supabase connecté")
        stats = supabase_storage.get_stats()
        logger.info(f"📊 Stats Supabase: {stats}")
    else:
        logger.warning("⚠️ Supabase non connecté, utilisation du stockage local")
    
    channels = config_data.get("telegram_channels", [])
    if channels:
        logger.info(f"📡 Canaux configurés: {[c.get('channel') for c in channels if c.get('active', True)]}")
    else:
        logger.warning("⚠️ Aucun canal Telegram configuré")
    
    if os.getenv("DEEPSEEK_API_KEY"):
        logger.info("✅ DeepSeek API configurée")
    else:
        logger.warning("⚠️ DeepSeek API non configurée")
    
    logger.info("🔄 Démarrage du service Telegram...")
    success = await start_telegram_service()
    
    if success:
        logger.info("✅ TELEGRAM ACTIF - BOT À L'ÉCOUTE")
        logger.info("👀 Envoyez /start à votre bot pour tester")
    else:
        logger.error("❌ ÉCHEC DU DÉMARRAGE TELEGRAM")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Arrêt du bot...")
    await stop_telegram_service()
    logger.info("✅ Bot arrêté")

# ============================================
# ROUTES DE CONTRÔLE
# ============================================

@app.post("/api/telegram/start")
async def start_telegram():
    try:
        success = await start_telegram_service()
        return {"success": success, "message": "Service Telegram démarré" if success else "Erreur de démarrage"}
    except Exception as e:
        logger.error(f"Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/telegram/stop")
async def stop_telegram():
    try:
        success = await stop_telegram_service()
        return {"success": success, "message": "Service Telegram arrêté" if success else "Erreur d'arrêt"}
    except Exception as e:
        logger.error(f"Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/telegram/status")
async def telegram_status():
    service = get_telegram_service()
    return {
        "connected": service.is_connected if service else False,
        "running": telegram_running,
        "channels": len(service.channel_handlers) if service and hasattr(service, 'channel_handlers') else 0,
        "messages_processed": len(service.processed_messages) if service and hasattr(service, 'processed_messages') else 0
    }

@app.post("/api/telegram/test")
async def send_test_message():
    try:
        service = get_telegram_service()
        if not service or not service.is_connected:
            return {"success": False, "error": "Service non connecté"}
        
        channel = config_data.get("telegram", {}).get("channel")
        if not channel:
            channel = os.getenv("TELEGRAM_CHANNEL", "@Trading_longterme_bot")
        
        storage_type = "☁️ Supabase" if (supabase_storage and supabase_storage.connected) else "💾 Local"
        await service.client.send_message(
            channel,
            f"🧪 **Message de test**\n\n"
            "Le bot LongTerm AI est actif !\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📁 Stockage: {storage_type}"
        )
        return {"success": True, "message": "Message de test envoyé"}
    except Exception as e:
        logger.error(f"Erreur: {e}")
        return {"success": False, "error": str(e)}

# ============================================
# ROUTES DE RECHARGEMENT ET PARAMÈTRES
# ============================================

@app.post("/api/reload")
async def reload_bot():
    global config_data, stats_data, total_analyses, total_alerts, total_reports
    
    try:
        logger.info("🔄 Rechargement du bot...")
        
        config_data = load_config()
        
        stats_data = load_stats()
        total_analyses = stats_data.get("total_analyses", 0)
        total_alerts = stats_data.get("total_alerts", 0)
        total_reports = stats_data.get("total_reports", 0)
        
        if telegram_running and TELEGRAM_AVAILABLE:
            service = get_telegram_service()
            if service:
                await service.reload_channels()
                logger.info("✅ Canaux Telegram rechargés")
        
        await update_bot_status()
        
        logger.info("✅ Bot rechargé avec succès")
        return {"success": True, "message": "Bot rechargé avec succès", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du rechargement: {e}")
        return {"success": False, "error": str(e), "message": "Erreur lors du rechargement"}

# ============================================
# ROUTES DE PARAMÈTRES
# ============================================

@app.post("/api/settings/interval")
async def save_interval(data: dict):
    try:
        interval = data.get("interval_minutes")
        if not interval or interval < 1:
            return {"success": False, "error": "Intervalle invalide"}
        config_data = load_config()
        config_data["price_interval"] = interval
        save_config(config_data)
        logger.info(f"✅ Intervalle mis à jour: {interval} minutes")
        return {"success": True, "message": f"Intervalle mis à jour: {interval} minutes"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/settings/threshold")
async def save_threshold(data: dict):
    try:
        threshold = data.get("threshold_percent")
        if threshold is None or threshold < 0:
            return {"success": False, "error": "Seuil invalide"}
        config_data = load_config()
        config_data["alert_threshold"] = threshold
        save_config(config_data)
        logger.info(f"✅ Seuil mis à jour: {threshold}%")
        return {"success": True, "message": f"Seuil mis à jour: {threshold}%"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/settings/notifications")
async def save_notifications(data: dict):
    try:
        config_data = load_config()
        config_data["notifications"] = {
            "price": data.get("price", True),
            "news": data.get("news", True),
            "weekly": data.get("weekly", True)
        }
        save_config(config_data)
        logger.info("✅ Préférences de notification enregistrées")
        return {"success": True, "message": "Préférences de notification enregistrées"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/settings/channels")
async def get_channels():
    try:
        config_data = load_config()
        channels = config_data.get("telegram_channels", [])
        return {"success": True, "channels": channels}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/settings/channels/add")
async def add_channel(data: dict):
    try:
        channel = data.get("channel", "").strip()
        if not channel:
            return {"success": False, "error": "Canal invalide"}
        config_data = load_config()
        channels = config_data.get("telegram_channels", [])
        for ch in channels:
            if ch.get("channel") == channel:
                return {"success": False, "error": "Ce canal existe déjà"}
        channels.append({"channel": channel, "active": True})
        config_data["telegram_channels"] = channels
        save_config(config_data)
        if telegram_running and TELEGRAM_AVAILABLE:
            service = get_telegram_service()
            if service:
                await service.reload_channels()
        logger.info(f"✅ Canal ajouté: {channel}")
        return {"success": True, "message": f"Canal ajouté: {channel}"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/settings/channels/remove")
async def remove_channel(data: dict):
    try:
        index = data.get("index")
        if index is None:
            return {"success": False, "error": "Index invalide"}
        config_data = load_config()
        channels = config_data.get("telegram_channels", [])
        if 0 <= index < len(channels):
            removed = channels.pop(index)
            config_data["telegram_channels"] = channels
            save_config(config_data)
            if telegram_running and TELEGRAM_AVAILABLE:
                service = get_telegram_service()
                if service:
                    await service.reload_channels()
            logger.info(f"✅ Canal supprimé: {removed.get('channel')}")
            return {"success": True, "message": f"Canal {removed.get('channel')} supprimé"}
        else:
            return {"success": False, "error": "Index hors limites"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/settings/channels/toggle")
async def toggle_channel(data: dict):
    try:
        index = data.get("index")
        if index is None:
            return {"success": False, "error": "Index invalide"}
        config_data = load_config()
        channels = config_data.get("telegram_channels", [])
        if 0 <= index < len(channels):
            channels[index]["active"] = not channels[index].get("active", True)
            config_data["telegram_channels"] = channels
            save_config(config_data)
            if telegram_running and TELEGRAM_AVAILABLE:
                service = get_telegram_service()
                if service:
                    await service.reload_channels()
            logger.info(f"✅ Statut du canal modifié")
            return {"success": True, "message": "Statut du canal modifié"}
        else:
            return {"success": False, "error": "Index hors limites"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

# ===== ROUTE DE STATUT =====

async def update_bot_status():
    try:
        logger.info("📊 Mise à jour du statut...")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur mise à jour statut: {e}")
        return False

@app.get("/api/status")
async def get_status():
    global total_analyses, total_alerts, total_reports
    
    try:
        stats_data = load_stats()
        total_analyses = stats_data.get("total_analyses", 0)
        total_alerts = stats_data.get("total_alerts", 0)
        total_reports = stats_data.get("total_reports", 0)
        
        config_data = load_config()
        
        # Récupérer les stats Supabase si disponible
        supabase_stats = {}
        if supabase_storage and supabase_storage.connected:
            supabase_stats = supabase_storage.get_stats()
        
        status = {
            "running": True,
            "telegram": {
                "connected": telegram_service.is_connected if telegram_service else False,
                "running": telegram_running,
                "channels": len(telegram_service.channel_handlers) if telegram_service and hasattr(telegram_service, 'channel_handlers') else 0
            },
            "config": {
                "price_interval": config_data.get("price_interval", 30),
                "alert_threshold": config_data.get("alert_threshold", 5),
                "notifications": config_data.get("notifications", {
                    "price": True,
                    "news": True,
                    "weekly": True
                })
            },
            "storage": {
                "type": "Supabase" if (supabase_storage and supabase_storage.connected) else "Local JSON",
                "connected": supabase_storage and supabase_storage.connected
            },
            "stats": {
                "total_analyzed": total_analyses,
                "total_alerts": total_alerts,
                "total_reports": total_reports,
                "last_update": datetime.now().isoformat(),
                "supabase": supabase_stats
            }
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Erreur statut: {e}")
        return {"running": True, "error": str(e)}

# ===== ROUTES D'ANALYSES =====

@app.get("/api/analyses")
async def get_analyses(limit: int = 20, offset: int = 0):
    """Retourne les analyses depuis Supabase ou local"""
    try:
        if supabase_storage and supabase_storage.connected:
            analyses = supabase_storage.get_analyses(limit, offset)
            return {"success": True, "analyses": analyses, "total": len(analyses), "source": "supabase"}
        else:
            history = load_history()
            # Paginer manuellement
            paginated = history[-limit:] if history else []
            return {"success": True, "analyses": paginated, "total": len(history), "source": "local"}
    except Exception as e:
        logger.error(f"❌ Erreur lecture analyses: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/analyses/count")
async def get_analyses_count():
    """Retourne le nombre total d'analyses"""
    try:
        if supabase_storage and supabase_storage.connected:
            count = supabase_storage.get_total_count()
            return {"success": True, "total_count": count, "source": "supabase"}
        else:
            history = load_history()
            return {"success": True, "total_count": len(history), "source": "local"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/analyses/asset/{asset}")
async def get_analyses_by_asset(asset: str, limit: int = 20):
    """Retourne les analyses par actif depuis Supabase"""
    try:
        if supabase_storage and supabase_storage.connected:
            analyses = supabase_storage.get_analyses_by_asset(asset, limit)
            return {"success": True, "analyses": analyses, "asset": asset, "source": "supabase"}
        else:
            history = load_history()
            filtered = [a for a in history if a.get('asset', '').upper() == asset.upper()]
            return {"success": True, "analyses": filtered[-limit:], "asset": asset, "source": "local"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stats")
async def get_stats_api():
    """Retourne les stats depuis Supabase ou local"""
    try:
        if supabase_storage and supabase_storage.connected:
            stats = supabase_storage.get_stats()
            return {"success": True, "stats": stats, "source": "supabase"}
        else:
            stats = load_stats()
            return {"success": True, "stats": stats, "source": "local"}
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {"success": False, "error": str(e)}

# ===== ROUTES DE DEBUG =====

@app.get("/api/debug/files")
async def debug_files():
    """Vérifie l'état des fichiers"""
    try:
        history = load_history()
        stats = load_stats()
        
        return {
            "success": True,
            "history_count": len(history),
            "stats": stats,
            "history_exists": os.path.exists("data/analyses_history.json"),
            "stats_exists": os.path.exists("data/stats.json"),
            "supabase_connected": supabase_storage and supabase_storage.connected
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================
# PAGES HTML (SIMPLIFIÉES POUR LE TEST)
# ============================================

# ===== PAGE DE CONNEXION =====
LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>Connexion</title>
<style>
body { background: #0a0a0a; color: #e5e5e5; font-family: Arial; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
.login-container { background: #1a1a1a; padding: 40px; border-radius: 16px; border: 1px solid #333; max-width: 400px; width: 100%; text-align: center; }
h1 { color: #f7931a; }
input { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #333; background: #0a0a0a; color: white; margin-bottom: 12px; }
button { width: 100%; padding: 12px; border: none; border-radius: 8px; background: #f7931a; color: #0a0a0a; font-weight: bold; cursor: pointer; }
.error { color: #f87171; margin-top: 10px; display: none; }
</style>
</head>
<body>
<div class="login-container">
<h1>LongTerm AI</h1>
<p>Accès sécurisé</p>
<form onsubmit="login(event)">
<input type="text" id="username" placeholder="Utilisateur" required>
<input type="password" id="password" placeholder="Mot de passe" required>
<button type="submit">Se connecter</button>
<div id="error" class="error">❌ Identifiants incorrects</div>
</form>
</div>
<script>
function login(e) {
e.preventDefault();
var u=document.getElementById('username').value;
var p=document.getElementById('password').value;
if(u==="admin" && p==="admin123"){
localStorage.setItem('auth', btoa(u+':'+p));
window.location.href='/';
}else{
document.getElementById('error').style.display='block';
}
}
</script>
</body>
</html>
'''

# ===== PAGE PRINCIPALE =====
MAIN_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>LongTerm AI - Dashboard</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0a0a0a; color:#e5e5e5; font-family:'Segoe UI',Arial,sans-serif; padding:20px; }
.container { max-width:1200px; margin:0 auto; }
.header { background:linear-gradient(135deg,#1a1a1a,#2a2a2a); border-radius:16px; padding:20px 30px; margin-bottom:20px; border:1px solid #333; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; }
.logo h1 { background:linear-gradient(135deg,#f7931a,#ffd700); -webkit-background-clip:text; -webkit-text-fill-color:transparent; font-size:28px; }
.logo span { color:#666; font-size:14px; }
.header-status { display:flex; align-items:center; gap:15px; flex-wrap:wrap; }
.status-badge { padding:8px 20px; border-radius:20px; font-weight:bold; font-size:14px; background:#064e3b; color:#34d399; border:1px solid #34d399; }
.status-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px; background:#34d399; animation:pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.5;} }
.grid-3 { display:grid; grid-template-columns:repeat(3,1fr); gap:20px; margin-bottom:20px; }
.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px; }
@media(max-width:768px){ .grid-3{grid-template-columns:1fr;} .grid-2{grid-template-columns:1fr;} }
.card { background:#1a1a1a; border-radius:12px; padding:20px; border:1px solid #2a2a2a; }
.card-title { font-size:13px; color:#888; text-transform:uppercase; margin-bottom:12px; }
.btn { padding:10px 24px; border:none; border-radius:8px; font-weight:bold; font-size:14px; cursor:pointer; transition:all 0.3s; }
.btn-info { background:#1e3a5f; color:#60a5fa; }
.btn-info:hover { background:#1e40af; }
.btn-success { background:#065f46; color:#34d399; }
.btn-success:hover { background:#047857; }
.btn-warning { background:#7c5a1a; color:#fbbf24; }
.btn-warning:hover { background:#9a6d1a; }
.btn-danger { background:#7f1d1d; color:#f87171; }
.btn-danger:hover { background:#991b1b; }
.btn-group { display:flex; gap:10px; flex-wrap:wrap; margin:10px 0; }
.analysis-item { background:#0a0a0a; padding:12px; border-radius:8px; margin-bottom:8px; border:1px solid #1a1a1a; }
.analysis-item .summary { color:#aaa; font-size:13px; }
.analysis-item .meta { color:#444; font-size:11px; margin-top:4px; }
.log-container { background:#0a0a0a; border-radius:10px; padding:12px; max-height:200px; overflow-y:auto; font-family:'Courier New',monospace; font-size:12px; color:#555; border:1px solid #1a1a1a; }
.log-container .entry { padding:3px 0; border-bottom:1px solid #111; }
.log-container .time { color:#333; margin-right:8px; }
.log-container .success { color:#34d399; }
.log-container .error { color:#f87171; }
.log-container .info { color:#60a5fa; }
.storage-badge { padding:4px 12px; border-radius:12px; font-size:11px; font-weight:bold; background:#1a2a4a; color:#60a5fa; border:1px solid #60a5fa; }
.storage-badge.cloud { background:#064e3b; color:#34d399; border-color:#34d399; }
</style>
</head>
<body>
<div class="container">
<div class="header">
<div class="logo"><h1>LongTerm AI</h1><span>Ultimate Investment Bot v3.0</span></div>
<div class="header-status">
<span class="status-badge"><span class="status-dot"></span><span id="statusText">ONLINE 24/7</span></span>
<span style="color:#666;font-size:13px;" id="lastUpdate">Last update: -</span>
<span class="storage-badge" id="storageBadge">💾 Local</span>
<button class="btn btn-info" onclick="reloadBot()" id="btnReload" style="padding:8px 18px;font-size:13px;">🔄 Recharger</button>
<button class="btn btn-danger" onclick="logout()" style="padding:8px 18px;font-size:13px;">🔓 Déconnexion</button>
</div>
</div>

<div class="grid-3">
<div class="card"><div class="card-title">📊 Analyses</div><div style="font-size:32px;font-weight:bold;color:#60a5fa;" id="statsAnalyses">0</div></div>
<div class="card"><div class="card-title">🔔 Alertes</div><div style="font-size:32px;font-weight:bold;color:#fbbf24;" id="statsAlerts">0</div></div>
<div class="card"><div class="card-title">📈 Rapports</div><div style="font-size:32px;font-weight:bold;color:#34d399;" id="statsReports">0</div></div>
</div>

<div class="grid-2">
<div class="card">
<div class="card-title">🎮 Contrôle</div>
<div class="btn-group">
<button class="btn btn-success" onclick="startBot()">▶️ Démarrer</button>
<button class="btn btn-danger" onclick="stopBot()">⏹ Arrêter</button>
<button class="btn btn-info" onclick="testTelegram()">📤 Test</button>
</div>
<div style="margin-top:10px;font-size:13px;color:#34d399;" id="botStatus">🟢 Bot actif</div>
<div style="margin-top:5px;font-size:12px;color:#666;" id="storageInfo">Stockage: Local</div>
</div>
<div class="card">
<div class="card-title">📡 Telegram</div>
<div style="font-size:13px;color:#666;">Status: <span id="telegramStatus">❌ Déconnecté</span></div>
<button class="btn btn-info" onclick="window.location.href='/telegram-login'" style="margin-top:10px;width:100%;">📱 Connecter Telegram</button>
</div>
</div>

<div class="card">
<div class="card-title" style="display:flex;justify-content:space-between;">
<span>📝 Dernières analyses</span>
<button class="btn btn-info" onclick="loadAnalyses()" style="padding:4px 12px;font-size:12px;">Actualiser</button>
</div>
<div id="analysesList"><div style="color:#444;text-align:center;padding:20px;">Aucune analyse</div></div>
</div>

<div class="card">
<div class="card-title">📋 Logs</div>
<div class="log-container" id="logContainer">
<div class="entry"><span class="time">[System]</span> <span class="info">Bot prêt</span></div>
</div>
</div>
</div>

<script>
function getAuth(){return localStorage.getItem('auth')||btoa('admin:admin123');}
function logout(){if(confirm('Déconnexion ?')){localStorage.removeItem('auth');window.location.href='/login';}}

function addLog(msg,type){
type=type||'info';var log=document.getElementById('logContainer');var entry=document.createElement('div');entry.className='entry';
var time=new Date().toLocaleTimeString();var cls=type==='error'?'error':type==='success'?'success':type==='warning'?'warning':'info';
entry.innerHTML='<span class="time">['+time+']</span> <span class="'+cls+'">'+msg+'</span>';
log.prepend(entry);if(log.children.length>100)log.removeChild(log.lastChild);
}

async function callAPI(endpoint,method,data){
method=method||'GET';try{var auth=getAuth();var options={method:method,headers:{'Content-Type':'application/json','Authorization':'Basic '+auth}};if(data)options.body=JSON.stringify(data);
var response=await fetch(endpoint,options);if(!response.ok){if(response.status===401){addLog('⚠️ Session expirée','warning');localStorage.removeItem('auth');window.location.href='/login';return null;}return null;}return await response.json();
}catch(error){addLog('API Error: '+error.message,'error');return null;}
}

async function reloadBot(){
var btn=document.getElementById('btnReload');btn.disabled=true;btn.textContent='⏳...';
addLog('🔄 Rechargement...','info');var data=await callAPI('/api/reload','POST');
btn.disabled=false;btn.textContent='🔄 Recharger';
if(data&&data.success){addLog('✅ Rechargé','success');updateStatus();loadAnalyses();}else{addLog('❌ Erreur','error');}
}

async function updateStatus(){
var data=await callAPI('/api/status');if(!data)return;
document.getElementById('lastUpdate').textContent='Last update: '+new Date().toLocaleTimeString();
if(data.stats){document.getElementById('statsAnalyses').textContent=data.stats.total_analyzed||0;document.getElementById('statsAlerts').textContent=data.stats.total_alerts||0;document.getElementById('statsReports').textContent=data.stats.total_reports||0;}
if(data.telegram){document.getElementById('telegramStatus').textContent=data.telegram.connected?'✅ Connecté':'❌ Déconnecté';}
if(data.storage){var badge=document.getElementById('storageBadge');var info=document.getElementById('storageInfo');
if(data.storage.type==='Supabase'&&data.storage.connected){badge.textContent='☁️ Supabase';badge.className='storage-badge cloud';info.textContent='Stockage: ☁️ Supabase';}else{badge.textContent='💾 Local';badge.className='storage-badge';info.textContent='Stockage: 💾 Local JSON';}}
}

async function loadAnalyses(){
var data=await callAPI('/api/analyses');if(!data)return;var list=document.getElementById('analysesList');
if(!data.analyses||data.analyses.length===0){list.innerHTML='<div style="color:#444;text-align:center;padding:20px;">Aucune analyse</div>';return;}
var html='';for(var i=data.analyses.length-1;i>=0;i--){var item=data.analyses[i];var a=item.analysis||{};var date=new Date(item.timestamp);var summaryText=a.summary||a.reason||'No summary';var assetName=a.asset||'OTHER';
html+='<div class="analysis-item"><div style="display:flex;justify-content:space-between;"><b style="color:#f7931a;">'+assetName+'</b><span style="color:#888;font-size:12px;">'+date.toLocaleString()+'</span></div><div class="summary">'+summaryText+'</div><div class="meta">Score: '+(a.score||0)+'/10 | Horizon: '+(a.time_horizon||'N/A')+'</div></div>';}
list.innerHTML=html;
}

async function startBot(){
addLog('Démarrage...','info');var data=await callAPI('/api/telegram/start','POST');
if(data&&data.success){addLog('✅ Bot démarré','success');updateStatus();}else{addLog('❌ Erreur','error');}
}

async function stopBot(){
addLog('Arrêt...','info');var data=await callAPI('/api/telegram/stop','POST');
if(data&&data.success){addLog('✅ Bot arrêté','success');updateStatus();}else{addLog('❌ Erreur','error');}
}

async function testTelegram(){
addLog('Envoi test...','info');var data=await callAPI('/api/telegram/test','POST');
if(data&&data.success){addLog('✅ Test envoyé','success');}else{addLog('❌ Erreur','error');}
}

updateStatus();loadAnalyses();
setInterval(updateStatus,10000);setInterval(loadAnalyses,15000);
addLog('🤖 Bot 24h/7j','info');
</script>
</body>
</html>
'''

# ===== PAGE PARAMÈTRES =====
SETTINGS_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>Paramètres</title>
<style>
body { background:#0a0a0a; color:#e5e5e5; font-family:'Segoe UI',Arial,sans-serif; padding:20px; }
.container { max-width:900px; margin:0 auto; }
.header { background:#1a1a1a; border-radius:16px; padding:20px 25px; margin-bottom:20px; border:1px solid #333; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; }
h1 { color:#f7931a; font-size:24px; }
.card { background:#1a1a1a; border-radius:12px; padding:24px; border:1px solid #2a2a2a; margin-bottom:20px; }
.card-title { font-size:16px; color:#f7931a; font-weight:bold; margin-bottom:16px; border-bottom:1px solid #2a2a2a; padding-bottom:10px; }
.config-row { display:flex; gap:10px; margin-bottom:12px; flex-wrap:wrap; align-items:center; }
.config-row label { min-width:180px; font-size:14px; color:#aaa; }
.config-row input { flex:1; padding:10px 14px; border-radius:8px; border:1px solid #333; background:#0a0a0a; color:white; font-size:14px; min-width:150px; }
.btn { padding:10px 24px; border:none; border-radius:8px; font-weight:bold; font-size:14px; cursor:pointer; }
.btn-info { background:#1e3a5f; color:#60a5fa; }
.btn-info:hover { background:#1e40af; }
.btn-success { background:#065f46; color:#34d399; }
.btn-success:hover { background:#047857; }
.btn-danger { background:#7f1d1d; color:#f87171; }
.btn-danger:hover { background:#991b1b; }
.btn-back { background:#2a2a2a; color:#888; }
.btn-back:hover { background:#3a3a3a; color:#fff; }
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>⚙️ Paramètres</h1>
<div><button class="btn btn-back" onclick="window.location.href='/'">← Retour</button></div>
</div>

<div class="card">
<div class="card-title">📡 Canaux Telegram</div>
<div id="channelsList"><div style="color:#444;text-align:center;padding:20px;">Aucun canal</div></div>
<div class="config-row" style="margin-top:15px;border-top:1px solid #2a2a2a;padding-top:15px;">
<label>Ajouter</label>
<input type="text" id="newChannel" placeholder="@nom_du_canal">
<button class="btn btn-success" onclick="addChannel()">➕ Ajouter</button>
</div>
<div id="channelResult" style="margin-top:8px;font-size:13px;"></div>
</div>

<div class="card">
<div class="card-title">📊 Intervalle de vérification</div>
<div class="config-row">
<label>Minutes</label>
<input type="number" id="priceInterval" value="30" min="1">
<button class="btn btn-info" onclick="saveInterval()">Enregistrer</button>
</div>
<div id="intervalResult" style="margin-top:8px;font-size:13px;"></div>
</div>

<div class="card">
<div class="card-title">🔔 Seuil d'alerte</div>
<div class="config-row">
<label>Pourcentage</label>
<input type="number" id="alertThreshold" value="5" min="0.5" step="0.5">
<button class="btn btn-info" onclick="saveThreshold()">Enregistrer</button>
</div>
<div id="thresholdResult" style="margin-top:8px;font-size:13px;"></div>
</div>

<div class="card">
<div class="card-title">🛠️ Maintenance</div>
<div class="btn-group" style="display:flex;gap:10px;flex-wrap:wrap;">
<button class="btn btn-warning" onclick="exportData()" style="background:#7c5a1a;color:#fbbf24;padding:10px 24px;border:none;border-radius:8px;font-weight:bold;cursor:pointer;">📥 Exporter</button>
<button class="btn btn-danger" onclick="resetBot()">🔄 Réinitialiser</button>
</div>
<div id="maintenanceResult" style="margin-top:8px;font-size:13px;"></div>
</div>
</div>

<script>
function addLog(msg,type){var log=document.getElementById('settingsLogs');if(!log)return;var entry=document.createElement('div');var time=new Date().toLocaleTimeString();var colors={success:'#34d399',error:'#f87171',info:'#60a5fa'};entry.innerHTML='<span style="color:#333;">['+time+']</span> <span style="color:'+(colors[type]||'#888')+';">'+msg+'</span>';log.prepend(entry);}
async function callAPI(endpoint,method,data){method=method||'GET';try{var auth=localStorage.getItem('auth')||btoa('admin:admin123');var options={method:method,headers:{'Content-Type':'application/json','Authorization':'Basic '+auth}};if(data)options.body=JSON.stringify(data);var response=await fetch(endpoint,options);if(!response.ok){if(response.status===401){localStorage.removeItem('auth');window.location.href='/login';return null;}return null;}return await response.json();}catch(error){return null;}}
function showResult(id,msg,type){var el=document.getElementById(id);if(!el)return;var colors={success:'#34d399',error:'#f87171',info:'#60a5fa'};el.style.color=colors[type]||'#888';el.textContent=msg;}

async function loadChannels(){
var data=await callAPI('/api/settings/channels');var list=document.getElementById('channelsList');if(!data||!data.success){list.innerHTML='<div class="empty-message">❌ Erreur</div>';return;}
var channels=data.channels||[];if(channels.length===0){list.innerHTML='<div class="empty-message">Aucune chaîne</div>';return;}
var html='';for(var i=0;i<channels.length;i++){var ch=channels[i];var statusClass=ch.active?'active':'inactive';html+='<div style="display:flex;justify-content:space-between;padding:10px;background:#0a0a0a;border-radius:8px;margin-bottom:8px;border:1px solid #2a2a2a;"><span>'+ch.channel+'</span><div><button onclick="toggleChannel('+i+')" style="background:#1e3a5f;color:#60a5fa;border:none;padding:4px 12px;border-radius:6px;cursor:pointer;">'+(ch.active?'Désactiver':'Activer')+'</button><button onclick="removeChannel('+i+')" style="background:#4a1a1a;color:#f87171;border:none;padding:4px 12px;border-radius:6px;cursor:pointer;margin-left:5px;">Supprimer</button></div></div>';}
list.innerHTML=html;
}

async function addChannel(){var input=document.getElementById('newChannel');var channel=input.value.trim();if(!channel){showResult('channelResult','❌ Entrez un canal','error');return;}if(!channel.startsWith('@'))channel='@'+channel;var data=await callAPI('/api/settings/channels/add','POST',{channel:channel});if(data&&data.success){showResult('channelResult','✅ Canal ajouté','success');input.value='';loadChannels();}else{showResult('channelResult','❌ Erreur','error');}}
async function removeChannel(index){if(!confirm('Supprimer ?'))return;var data=await callAPI('/api/settings/channels/remove','POST',{index:index});if(data&&data.success){showResult('channelResult','✅ Supprimé','success');loadChannels();}}
async function toggleChannel(index){var data=await callAPI('/api/settings/channels/toggle','POST',{index:index});if(data&&data.success){showResult('channelResult','✅ Modifié','success');loadChannels();}}
async function saveInterval(){var val=parseInt(document.getElementById('priceInterval').value);if(!val||val<1){showResult('intervalResult','❌ Valide','error');return;}var data=await callAPI('/api/settings/interval','POST',{interval_minutes:val});if(data&&data.success){showResult('intervalResult','✅ Mis à jour: '+val+' min','success');}}
async function saveThreshold(){var val=parseFloat(document.getElementById('alertThreshold').value);if(!val||val<0){showResult('thresholdResult','❌ Valide','error');return;}var data=await callAPI('/api/settings/threshold','POST',{threshold_percent:val});if(data&&data.success){showResult('thresholdResult','✅ Mis à jour: '+val+'%','success');}}
async function exportData(){var data=await callAPI('/api/export-data');if(data&&data.success){try{var json=JSON.stringify(data.data,null,2);var blob=new Blob([json],{type:'application/json'});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download='data-'+new Date().toISOString().slice(0,10)+'.json';a.click();showResult('maintenanceResult','✅ Export terminé','success');}catch(e){showResult('maintenanceResult','❌ Erreur','error');}}}
async function resetBot(){if(!confirm('Tout effacer ?'))return;var data=await callAPI('/api/reset','POST');if(data&&data.success){showResult('maintenanceResult','✅ Réinitialisé','success');setTimeout(function(){window.location.href='/';},2000);}}

loadChannels();
</script>
</body>
</html>
'''

# ===== ROUTES AVEC AUTHENTIFICATION =====

@app.get("/login")
async def login_page():
    return HTMLResponse(LOGIN_PAGE)

@app.get("/web")
async def web_interface(request: Request):
    if not check_auth_header(request):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(MAIN_PAGE)

@app.get("/")
async def home(request: Request):
    if check_auth_header(request):
        return HTMLResponse(MAIN_PAGE)
    return HTMLResponse(MAIN_PAGE)

@app.get("/settings")
async def settings_page(request: Request):
    if check_auth_header(request):
        return HTMLResponse(SETTINGS_PAGE)
    return HTMLResponse(SETTINGS_PAGE)

@app.get("/history")
async def history_page(request: Request):
    if not check_auth_header(request):
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/history", status_code=302)

# ============================================
# POINT D'ENTRÉE
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("LongTerm AI Bot v3.0 - 24h/7j")
    print("=" * 50)
    print("Interface: http://localhost:8000/")
    print("Paramètres: http://localhost:8000/settings")
    print("API: http://localhost:8000/api/status")
    print("=" * 50)
    print("🔐 Utilisateur: admin / admin123")
    print("📁 Stockage: Supabase + Local (fallback)")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000)
