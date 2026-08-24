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

from app.api.routes import router
from app.history_page import router as history_router
from app.services.ai_service import AIService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    """Charge l'historique des analyses"""
    history_file = "data/analyses_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Erreur lecture historique: {e}")
            return []
    return []

def save_history(history):
    """Sauvegarde l'historique des analyses"""
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
        # Garder seulement les 100 dernières
        if len(history) > 100:
            history = history[-100:]
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

ai_service = AIService()

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
            await service.client.send_message(
                channel,
                f"📊 **État du bot**\n\n"
                f"Statut : {status}\n"
                f"Canaux écoutés : {len(service.channel_handlers) if hasattr(service, 'channel_handlers') else 0}\n"
                f"Messages traités : {len(service.processed_messages) if hasattr(service, 'processed_messages') else 0}\n"
                f"📈 Analyses totales : {total_analyses}\n"
                f"🔔 Alertes : {total_alerts}\n"
                f"📊 Rapports : {total_reports}"
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
        
        # === INCÉMENTER LE COMPTEUR ===
        total_analyses += 1
        stats_data["total_analyses"] = total_analyses
        save_stats(stats_data)
        logger.info(f"📊 Total analyses: {total_analyses}")
        
        # === PRÉPARER L'ANALYSE ===
        analysis_data = {
            "id": message_id,
            "timestamp": datetime.now().isoformat(),
            "text": text[:300],
            "analysis": {}
        }
        
        # === ANALYSE AVEC DEEPSEEK ===
        try:
            result = await ai_service.analyze(text)
            logger.info(f"🔍 Résultat DeepSeek: {result}")
        except Exception as e:
            logger.error(f"❌ Erreur DeepSeek: {e}")
            result = None
        
        # === TOUJOURS SAUVEGARDER ===
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
            
            # === SAUVEGARDER L'HISTORIQUE ===
            add_analysis_to_history(analysis_data)
            logger.info(f"✅ Analyse sauvegardée dans l'historique")
            
            # === CONSTRUIRE LE MESSAGE ===
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
• **GOLD:** {analysis.get('gold_impact', 'Non spécifié')}"""
        else:
            # Fallback si DeepSeek échoue
            analysis_data["analysis"] = {
                "asset": "OTHER",
                "impact": "neutral",
                "score": 0,
                "time_horizon": "unknown",
                "summary": text[:200],
                "confidence": "low"
            }
            
            # === SAUVEGARDER L'HISTORIQUE (TOUJOURS) ===
            add_analysis_to_history(analysis_data)
            logger.info(f"✅ Analyse de secours sauvegardée dans l'historique")
            
            message = f"""📩 **Nouveau message analysé**

**ID:** {message_id}
**Contenu:** {text[:200]}...

⚠️ Analyse détaillée non disponible - Notification de secours"""
        
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
        
        await service.client.send_message(
            channel,
            "🧪 **Message de test**\n\n"
            "Le bot LongTerm AI est actif !\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
            "stats": {
                "total_analyzed": total_analyses,
                "total_alerts": total_alerts,
                "total_reports": total_reports,
                "last_update": datetime.now().isoformat()
            }
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Erreur statut: {e}")
        return {"running": True, "error": str(e)}

# ===== ROUTE D'ANALYSES =====

@app.get("/api/analyses")
async def get_analyses():
    try:
        history = load_history()
        return {"success": True, "analyses": history}
    except Exception as e:
        logger.error(f"❌ Erreur lecture analyses: {e}")
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
            "stats_exists": os.path.exists("data/stats.json")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================
# PAGES HTML
# ============================================

# ===== PAGE DE CONNEXION =====
LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LongTerm AI - Connexion</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            color: #e5e5e5;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: #1a1a1a;
            padding: 40px;
            border-radius: 16px;
            border: 1px solid #2a2a2a;
            max-width: 400px;
            width: 100%;
            text-align: center;
        }
        .login-container h1 {
            background: linear-gradient(135deg, #f7931a, #ffd700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 28px;
            margin-bottom: 8px;
        }
        .login-container p {
            color: #666;
            font-size: 14px;
            margin-bottom: 25px;
        }
        .login-container input {
            width: 100%;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid #333;
            background: #0a0a0a;
            color: white;
            font-size: 14px;
            margin-bottom: 12px;
        }
        .login-container input:focus {
            outline: none;
            border-color: #f7931a;
        }
        .login-container button {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: linear-gradient(135deg, #f7931a, #ffd700);
            color: #0a0a0a;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .login-container button:hover {
            transform: scale(1.02);
            opacity: 0.9;
        }
        .error {
            color: #f87171;
            font-size: 13px;
            margin-top: 10px;
            display: none;
        }
        .error.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>LongTerm AI</h1>
        <p>Accès sécurisé</p>
        <form onsubmit="login(event)">
            <input type="text" id="username" placeholder="Nom d'utilisateur" required>
            <input type="password" id="password" placeholder="Mot de passe" required>
            <button type="submit">Se connecter</button>
            <div id="error" class="error">❌ Identifiants incorrects</div>
        </form>
    </div>
    <script>
        function login(event) {
            event.preventDefault();
            var username = document.getElementById('username').value;
            var password = document.getElementById('password').value;
            if (username === "admin" && password === "admin123") {
                var auth = btoa(username + ':' + password);
                localStorage.setItem('auth', auth);
                window.location.href = '/';
            } else {
                document.getElementById('error').classList.add('show');
            }
        }
    </script>
</body>
</html>
'''

# ===== PAGE PRINCIPALE =====
MAIN_PAGE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LongTerm AI - Ultimate Bot</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            color: #e5e5e5;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #1a1a1a, #2a2a2a);
            border-radius: 16px;
            padding: 25px 30px;
            margin-bottom: 25px;
            border: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .logo h1 {
            background: linear-gradient(135deg, #f7931a, #ffd700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 28px;
        }
        .logo span { color: #666; font-size: 14px; display: block; }
        .header-status {
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        .telegram-login-btn {
            background: #0088cc;
            border: none;
            color: white;
            padding: 8px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .telegram-login-btn:hover {
            background: #006699;
            transform: scale(1.02);
        }
        .status-badge {
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
            background: #064e3b;
            color: #34d399;
            border: 1px solid #34d399;
        }
        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
            background: #34d399;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.9); }
        }
        .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 25px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }
        @media (max-width: 768px) { .grid-3 { grid-template-columns: 1fr; } .grid-2 { grid-template-columns: 1fr; } }
        .card {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a2a;
            transition: all 0.3s;
        }
        .card:hover { border-color: #444; }
        .card-title {
            font-size: 13px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }
        .asset-card {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a2a;
            position: relative;
            overflow: hidden;
        }
        .asset-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
        .asset-card.btc::before { background: #f7931a; }
        .asset-card.eth::before { background: #627EEA; }
        .asset-card.gold::before { background: #ffd700; }
        .asset-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .asset-name { font-size: 18px; font-weight: bold; }
        .asset-symbol { font-size: 12px; color: #666; }
        .asset-price { font-size: 24px; font-weight: bold; }
        .asset-change { font-size: 14px; font-weight: bold; }
        .asset-change.positive { color: #34d399; }
        .asset-change.negative { color: #f87171; }
        .asset-stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #2a2a2a; }
        .asset-stat { text-align: center; }
        .asset-stat-label { font-size: 10px; color: #666; text-transform: uppercase; }
        .asset-stat-value { font-size: 14px; font-weight: bold; margin-top: 2px; }
        .btn {
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .btn-info { background: #1e3a5f; color: #60a5fa; }
        .btn-info:hover:not(:disabled) { background: #1e40af; transform: scale(1.02); }
        .btn-success { background: #065f46; color: #34d399; }
        .btn-success:hover:not(:disabled) { background: #047857; transform: scale(1.02); }
        .btn-warning { background: #7c5a1a; color: #fbbf24; }
        .btn-warning:hover:not(:disabled) { background: #9a6d1a; transform: scale(1.02); }
        .btn-danger { background: #7f1d1d; color: #f87171; }
        .btn-danger:hover:not(:disabled) { background: #991b1b; transform: scale(1.02); }
        .btn-group { display: flex; gap: 10px; flex-wrap: wrap; margin: 10px 0; }
        .config-row { display: flex; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
        .config-row input, .config-row select {
            flex: 1;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #333;
            background: #0a0a0a;
            color: white;
            font-size: 13px;
            min-width: 150px;
        }
        .config-row input::placeholder { color: #444; }
        .config-row input:focus, .config-row select:focus { outline: none; border-color: #f7931a; }
        .config-row button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            background: #1e3a5f;
            color: #60a5fa;
            cursor: pointer;
            font-weight: bold;
            white-space: nowrap;
        }
        .config-row button:hover { background: #1e40af; }
        .analyses-list { max-height: 300px; overflow-y: auto; }
        .analysis-item {
            background: #0a0a0a;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            border: 1px solid #1a1a1a;
        }
        .analysis-item:hover { border-color: #333; }
        .analysis-item .header-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .analysis-item .asset-tag { font-weight: bold; color: #f7931a; }
        .analysis-item .impact-tag {
            padding: 2px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }
        .analysis-item .impact-tag.positive { background: #064e3b; color: #34d399; }
        .analysis-item .impact-tag.negative { background: #4a1a1a; color: #f87171; }
        .analysis-item .impact-tag.neutral { background: #1e3a5f; color: #60a5fa; }
        .analysis-item .summary { color: #aaa; margin-top: 6px; font-size: 13px; }
        .analysis-item .meta { color: #444; font-size: 11px; margin-top: 4px; }
        .log-container {
            background: #0a0a0a;
            border-radius: 10px;
            padding: 12px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #555;
            border: 1px solid #1a1a1a;
        }
        .log-container .entry { padding: 3px 0; border-bottom: 1px solid #111; }
        .log-container .time { color: #333; margin-right: 8px; }
        .log-container .success { color: #34d399; }
        .log-container .error { color: #f87171; }
        .log-container .info { color: #60a5fa; }
        .log-container .warning { color: #fbbf24; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0a0a0a; border-radius: 10px; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #444; }
        @media (max-width: 600px) {
            .header { flex-direction: column; align-items: stretch; gap: 15px; }
            .header-status { justify-content: center; }
            .config-row { flex-direction: column; }
            .config-row input { min-width: auto; }
            .btn-group { justify-content: center; }
            .asset-stats { grid-template-columns: 1fr; }
        }
        .settings-btn {
            background: #1a1a1a;
            border: 1px solid #333;
            color: #888;
            padding: 8px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .settings-btn:hover { border-color: #f7931a; color: #f7931a; }
        .reload-btn {
            background: #1a3a1a;
            border: 1px solid #34d399;
            color: #34d399;
            padding: 8px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .reload-btn:hover { background: #064e3b; transform: scale(1.02); }
        .reload-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .logout-btn {
            background: #4a1a1a;
            border: 1px solid #f87171;
            color: #f87171;
            padding: 8px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .logout-btn:hover { background: #7f1d1d; transform: scale(1.02); }
        .bot-status-text { color: #34d399; font-size: 14px; font-weight: bold; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo">
            <h1>LongTerm AI</h1>
            <span>Ultimate Investment Bot v3.0</span>
        </div>
        <div class="header-status">
            <span class="status-badge">
                <span class="status-dot"></span>
                <span id="statusText">ONLINE 24/7</span>
            </span>
            <span style="color:#666;font-size:13px;" id="lastUpdate">Last update: -</span>
            <button class="telegram-login-btn" onclick="window.location.href='/telegram-login'">
                📱 Connecter Telegram
            </button>
            <button class="reload-btn" onclick="reloadBot()" id="btnReload">🔄 Recharger</button>
            <button class="settings-btn" onclick="window.location.href='/settings'">⚙️ Paramètres</button>
            <button class="logout-btn" onclick="logout()">🔓 Déconnexion</button>
        </div>
    </div>

    <div class="grid-3" id="assetsContainer">
        <div class="asset-card btc">
            <div class="asset-header">
                <div><span class="asset-name">Bitcoin</span><span class="asset-symbol"> BTC</span></div>
                <span id="btcChange" class="asset-change positive">+0.00%</span>
            </div>
            <div class="asset-price" id="btcPrice">$---</div>
            <div class="asset-stats">
                <div class="asset-stat"><div class="asset-stat-label">24h</div><div class="asset-stat-value" id="btc24h">-</div></div>
                <div class="asset-stat"><div class="asset-stat-label">7d</div><div class="asset-stat-value" id="btc7d">-</div></div>
                <div class="asset-stat"><div class="asset-stat-label">Volume</div><div class="asset-stat-value" id="btcVolume">-</div></div>
            </div>
        </div>
        <div class="asset-card eth">
            <div class="asset-header">
                <div><span class="asset-name">Ethereum</span><span class="asset-symbol"> ETH</span></div>
                <span id="ethChange" class="asset-change positive">+0.00%</span>
            </div>
            <div class="asset-price" id="ethPrice">$---</div>
            <div class="asset-stats">
                <div class="asset-stat"><div class="asset-stat-label">24h</div><div class="asset-stat-value" id="eth24h">-</div></div>
                <div class="asset-stat"><div class="asset-stat-label">7d</div><div class="asset-stat-value" id="eth7d">-</div></div>
                <div class="asset-stat"><div class="asset-stat-label">Volume</div><div class="asset-stat-value" id="ethVolume">-</div></div>
            </div>
        </div>
        <div class="asset-card gold">
            <div class="asset-header">
                <div><span class="asset-name">Gold</span><span class="asset-symbol"> XAU</span></div>
                <span id="goldChange" class="asset-change positive">+0.00%</span>
            </div>
            <div class="asset-price" id="goldPrice">$---</div>
            <div class="asset-stats">
                <div class="asset-stat"><div class="asset-stat-label">24h</div><div class="asset-stat-value" id="gold24h">-</div></div>
                <div class="asset-stat"><div class="asset-stat-label">7d</div><div class="asset-stat-value" id="gold7d">-</div></div>
                <div class="asset-stat"><div class="asset-stat-label">Volume</div><div class="asset-stat-value" id="goldVolume">-</div></div>
            </div>
        </div>
    </div>

    <div class="grid-2">
        <div class="card">
            <div class="card-title">Bot Control</div>
            <div class="btn-group">
                <button id="btnCheckPrices" class="btn btn-info">🔄 Check Prices</button>
                <button id="btnWeeklyReport" class="btn btn-warning">📊 Weekly Report</button>
                <button id="btnPriceHistory" class="btn btn-info" onclick="window.location.href='/history'">📈 History</button>
            </div>
            <div style="margin-top:10px;font-size:13px;color:#34d399;" id="botStatusInfo">🟢 Bot is running 24/7</div>
        </div>
        <div class="card">
            <div class="card-title">Statistics</div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
                <div><div style="font-size:11px;color:#666;">Analyses</div><div style="font-size:24px;font-weight:bold;color:#60a5fa;" id="statsAnalyses">0</div></div>
                <div><div style="font-size:11px;color:#666;">Alerts</div><div style="font-size:24px;font-weight:bold;color:#fbbf24;" id="statsAlerts">0</div></div>
                <div><div style="font-size:11px;color:#666;">Reports</div><div style="font-size:24px;font-weight:bold;color:#34d399;" id="statsReports">0</div></div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-title">Portfolio Management</div>
        <div class="grid-2">
            <div>
                <div class="card-title" style="font-size:12px;color:#666;">Configuration</div>
                <div class="config-row">
                    <input type="number" id="tndUsdRate" placeholder="TND/USD (ex: 3.12)" step="0.01">
                    <button onclick="saveRate()" class="btn btn-info">Rate</button>
                </div>
                <div class="config-row">
                    <input type="number" id="feePercent" placeholder="Fee % (ex: 3.7)" step="0.1">
                    <button onclick="saveFee()" class="btn btn-info">Fee</button>
                </div>
            </div>
            <div>
                <div class="card-title" style="font-size:12px;color:#666;">Buy</div>
                <div class="config-row">
                    <select id="buyAsset" style="flex:1;padding:10px;border-radius:8px;border:1px solid #333;background:#0a0a0a;color:white;">
                        <option value="BTC">BTC</option>
                        <option value="ETH">ETH</option>
                        <option value="GOLD">GOLD</option>
                    </select>
                    <input type="number" id="buyAmount" placeholder="Amount TND" step="0.01">
                    <button onclick="buyAsset()" class="btn btn-success">Buy</button>
                </div>
            </div>
        </div>
        <div id="portfolioSummary" style="margin-top:15px;background:#0a0a0a;padding:15px;border-radius:8px;border:1px solid #222;">
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;">
                <div><div style="color:#666;font-size:11px;">Total Invested</div><div style="font-size:18px;font-weight:bold;color:#60a5fa;" id="portTotalInvested">0 TND</div></div>
                <div><div style="color:#666;font-size:11px;">Current Value</div><div style="font-size:18px;font-weight:bold;color:#34d399;" id="portCurrentValue">0 USD</div></div>
                <div><div style="color:#666;font-size:11px;">Profit/Loss</div><div style="font-size:18px;font-weight:bold;" id="portProfit">0 TND</div></div>
                <div><div style="color:#666;font-size:11px;">ROI</div><div style="font-size:18px;font-weight:bold;" id="portROI">0%</div></div>
            </div>
        </div>
        <div id="portfolioAssets" style="margin-top:10px;"></div>
        <div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;">
            <button onclick="loadPortfolio()" class="btn btn-info">Refresh</button>
            <button onclick="viewPortfolioReport()" class="btn btn-warning">Weekly Report</button>
        </div>
    </div>

    <div class="grid-2">
        <div class="card">
            <div class="card-title">Telegram Configuration</div>
            <div class="config-row"><input type="text" id="telegramApiId" placeholder="API ID"></div>
            <div class="config-row"><input type="password" id="telegramApiHash" placeholder="API Hash"></div>
            <div class="config-row"><input type="text" id="telegramPhone" placeholder="+216XXXXXXXX"></div>
            <div class="config-row"><input type="text" id="telegramChannel" placeholder="@channel_name"></div>
            <button class="btn btn-info" onclick="saveTelegramConfig()" style="width:100%;">Save Telegram Config</button>
            <div style="margin-top:8px;font-size:12px;color:#666;">Status: <span id="telegramStatusLabel">Not configured</span></div>
        </div>
        <div class="card">
            <div class="card-title">API Keys</div>
            <div class="config-row"><input type="password" id="deepseekKey" placeholder="DeepSeek API Key"><button onclick="saveDeepSeekKey()">Save</button></div>
            <div class="config-row"><input type="password" id="binanceApiKey" placeholder="Binance API Key"><button onclick="saveBinanceKey()">Save</button></div>
            <div class="config-row"><input type="password" id="binanceSecret" placeholder="Binance Secret"><button onclick="saveBinanceSecret()">Save</button></div>
            <div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;">
                <button class="btn btn-success" onclick="testDeepSeek()" style="flex:1;">Test DeepSeek</button>
                <button class="btn btn-success" onclick="testBinance()" style="flex:1;">Test Binance</button>
                <button class="btn btn-success" onclick="testTelegramNotify()" style="flex:1;">Test Telegram</button>
            </div>
            <div id="apiTestResult" style="margin-top:10px;font-size:12px;color:#666;"></div>
        </div>
    </div>

    <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
            <span>Recent Analyses</span>
            <button class="btn btn-info" onclick="loadAnalyses()" style="padding:4px 12px;font-size:12px;">Refresh</button>
        </div>
        <div id="analysesList" class="analyses-list"><div style="color:#444;text-align:center;padding:20px;">No analyses yet</div></div>
    </div>

    <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
            <span>Live Logs</span>
            <button onclick="clearLogs()" style="background:none;border:none;color:#444;cursor:pointer;font-size:12px;">Clear</button>
        </div>
        <div class="log-container" id="logContainer">
            <div class="entry"><span class="time">[System]</span> <span class="info">Bot ready - Interface v3.0</span></div>
        </div>
    </div>
</div>

<script>
function getAuth() {
    var auth = localStorage.getItem('auth');
    if (!auth) auth = btoa('admin:admin123');
    return auth;
}

function logout() {
    if (confirm('Voulez-vous vraiment vous déconnecter ?')) {
        localStorage.removeItem('auth');
        window.location.href = '/login';
    }
}

function addLog(msg, type) {
    type = type || 'info';
    var log = document.getElementById('logContainer');
    var entry = document.createElement('div');
    entry.className = 'entry';
    var time = new Date().toLocaleTimeString();
    var cls = type === 'error' ? 'error' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'info';
    entry.innerHTML = '<span class="time">[' + time + ']</span> <span class="' + cls + '">' + msg + '</span>';
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
    if (log.children.length > 100) log.removeChild(log.firstChild);
}

function clearLogs() {
    document.getElementById('logContainer').innerHTML = '';
    addLog('Logs cleared', 'info');
}

async function callAPI(endpoint, method, data) {
    method = method || 'GET';
    try {
        var auth = getAuth();
        var options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + auth
            }
        };
        if (data) options.body = JSON.stringify(data);
        var response = await fetch(endpoint, options);
        if (!response.ok) {
            if (response.status === 401) {
                addLog('⚠️ Session expirée', 'warning');
                localStorage.removeItem('auth');
                window.location.href = '/login';
                return null;
            }
            return null;
        }
        return await response.json();
    } catch (error) {
        addLog('API Error: ' + error.message, 'error');
        return null;
    }
}

async function reloadBot() {
    var btn = document.getElementById('btnReload');
    btn.disabled = true;
    btn.textContent = '⏳ Rechargement...';
    addLog('🔄 Rechargement du bot...', 'info');
    var data = await callAPI('/api/reload', 'POST');
    btn.disabled = false;
    btn.textContent = '🔄 Recharger';
    if (data && data.success) {
        addLog('✅ Bot rechargé avec succès', 'success');
        updateStatus();
        loadAnalyses();
        loadPortfolio();
        updatePrices();
    } else {
        addLog('❌ Erreur lors du rechargement', 'error');
    }
}

async function updateStatus() {
    var data = await callAPI('/api/status');
    if (!data) return;
    document.getElementById('lastUpdate').textContent = 'Last update: ' + new Date().toLocaleTimeString();
    if (data.stats) {
        document.getElementById('statsAnalyses').textContent = data.stats.total_analyzed || 0;
        document.getElementById('statsAlerts').textContent = data.stats.total_alerts || 0;
        document.getElementById('statsReports').textContent = data.stats.total_reports || 0;
    }
    if (data.telegram) {
        document.getElementById('telegramStatusLabel').textContent = data.telegram.connected ? '✅ Connecté' : '❌ Déconnecté';
    }
}

async function updatePrices() {
    addLog('Updating prices...', 'info');
    var data = await callAPI('/api/prices');
    if (!data) {
        addLog('Unable to fetch prices', 'warning');
        return;
    }
    var assets = data.assets || {};
    for (var symbol in assets) {
        var prefix = symbol.toLowerCase();
        var info = assets[symbol];
        var priceEl = document.getElementById(prefix + 'Price');
        var changeEl = document.getElementById(prefix + 'Change');
        var h24El = document.getElementById(prefix + '24h');
        var h7El = document.getElementById(prefix + '7d');
        var volEl = document.getElementById(prefix + 'Volume');
        if (priceEl) priceEl.textContent = '$' + (info.price || 0).toFixed(2);
        if (changeEl) {
            var change = info.change_24h || 0;
            changeEl.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
            changeEl.className = 'asset-change ' + (change >= 0 ? 'positive' : 'negative');
        }
        if (h24El) h24El.textContent = (info.change_24h || 0).toFixed(2) + '%';
        if (h7El) h7El.textContent = (info.change_7d || 0).toFixed(2) + '%';
        if (volEl) volEl.textContent = (info.volume || 0).toFixed(0);
    }
    addLog('Prices updated', 'success');
}

async function loadAnalyses() {
    var data = await callAPI('/api/analyses');
    if (!data) return;
    var list = document.getElementById('analysesList');
    if (!data.analyses || data.analyses.length === 0) {
        list.innerHTML = '<div style="color:#444;text-align:center;padding:20px;">No analyses yet</div>';
        return;
    }
    var html = '';
    for (var i = data.analyses.length - 1; i >= 0; i--) {
        var item = data.analyses[i];
        var a = item.analysis || {};
        var impactClass = a.impact || 'neutral';
        var date = new Date(item.timestamp);
        var summaryText = a.summary || a.reason || 'No summary';
        var score = a.score || a.impact_strength || 0;
        var assetName = a.asset || 'OTHER';
        html += '<div class="analysis-item">';
        html += '<div class="header-row">';
        html += '<span class="asset-tag">' + assetName + '</span>';
        html += '<span class="impact-tag ' + impactClass + '">' + impactClass.toUpperCase() + '</span>';
        html += ' <span style="color:#fbbf24;font-size:12px;">Score: ' + score + '/10</span>';
        html += '</div>';
        html += '<div class="summary">' + summaryText + '</div>';
        html += '<div class="meta">' + date.toLocaleString() + ' | Horizon: ' + (a.time_horizon || 'N/A');
        if (a.confidence) html += ' | Confiance: ' + a.confidence.toUpperCase();
        html += '</div>';
        html += '</div>';
    }
    list.innerHTML = html;
}

async function checkPrices() {
    addLog('Checking prices...', 'info');
    var data = await callAPI('/api/check-prices', 'POST');
    if (data) {
        addLog('Price check completed', 'success');
        updatePrices();
    }
}

async function weeklyReport() {
    addLog('Generating weekly report...', 'info');
    var data = await callAPI('/api/weekly-report', 'POST');
    if (data) addLog('Weekly report generated', 'success');
}

async function saveTelegramConfig() {
    var config = {
        api_id: document.getElementById('telegramApiId').value,
        api_hash: document.getElementById('telegramApiHash').value,
        phone: document.getElementById('telegramPhone').value,
        channel: document.getElementById('telegramChannel').value
    };
    if (!config.api_id || !config.api_hash || !config.phone || !config.channel) {
        addLog('Please fill all Telegram fields', 'error');
        return;
    }
    var data = await callAPI('/api/telegram/config', 'POST', config);
    if (data && data.success) {
        addLog('Telegram config saved', 'success');
        document.getElementById('telegramStatusLabel').textContent = 'Configured';
    }
}

async function saveDeepSeekKey() {
    var key = document.getElementById('deepseekKey').value.trim();
    if (!key) { addLog('Please enter a DeepSeek key', 'error'); return; }
    var data = await callAPI('/api/deepseek/config', 'POST', { api_key: key });
    if (data && data.success) addLog('DeepSeek key saved', 'success');
}

async function saveBinanceKey() {
    var key = document.getElementById('binanceApiKey').value.trim();
    if (!key) { addLog('Please enter a Binance key', 'error'); return; }
    var data = await callAPI('/api/binance/key', 'POST', { api_key: key });
    if (data && data.success) addLog('Binance key saved', 'success');
}

async function saveBinanceSecret() {
    var secret = document.getElementById('binanceSecret').value.trim();
    if (!secret) { addLog('Please enter a Binance secret', 'error'); return; }
    var data = await callAPI('/api/binance/secret', 'POST', { secret: secret });
    if (data && data.success) addLog('Binance secret saved', 'success');
}

async function testDeepSeek() {
    addLog('Testing DeepSeek...', 'info');
    var data = await callAPI('/api/test-deepseek', 'POST', { text: 'Bitcoin increased 5% this week' });
    if (data && data.success) {
        document.getElementById('apiTestResult').textContent = 'DeepSeek: OK';
        addLog('DeepSeek test successful', 'success');
    } else {
        document.getElementById('apiTestResult').textContent = 'DeepSeek: Failed';
        addLog('DeepSeek test failed', 'error');
    }
}

async function testBinance() {
    addLog('Testing Binance...', 'info');
    var data = await callAPI('/api/test-binance', 'POST');
    if (data && data.success) {
        var prices = data.prices || {};
        var msg = 'Binance: ';
        for (var symbol in prices) msg += symbol + ': $' + prices[symbol].toFixed(2) + ' ';
        document.getElementById('apiTestResult').textContent = msg;
        addLog('Binance test successful', 'success');
        updatePrices();
    } else {
        document.getElementById('apiTestResult').textContent = 'Binance: Failed';
        addLog('Binance test failed', 'error');
    }
}

async function testTelegramNotify() {
    addLog('Testing Telegram notifications...', 'info');
    var data = await callAPI('/api/test/telegram', 'POST');
    if (data && data.success) {
        document.getElementById('apiTestResult').textContent = 'Telegram: Message sent!';
        addLog('Telegram test successful', 'success');
    } else {
        document.getElementById('apiTestResult').textContent = 'Telegram: Failed';
        addLog('Telegram test failed', 'error');
    }
}

async function loadPortfolio() {
    var data = await callAPI('/api/portfolio/summary');
    if (data && data.success) {
        var s = data.summary;
        document.getElementById('portTotalInvested').textContent = s.total_invested_tnd.toFixed(2) + ' TND';
        document.getElementById('portCurrentValue').textContent = s.total_current_usd.toFixed(2) + ' USD';
        var profitEl = document.getElementById('portProfit');
        profitEl.textContent = (s.total_profit_tnd >= 0 ? '+' : '') + s.total_profit_tnd.toFixed(2) + ' TND';
        profitEl.style.color = s.total_profit_tnd >= 0 ? '#34d399' : '#f87171';
        var roiEl = document.getElementById('portROI');
        roiEl.textContent = (s.roi_percent >= 0 ? '+' : '') + s.roi_percent.toFixed(2) + '%';
        roiEl.style.color = s.roi_percent >= 0 ? '#34d399' : '#f87171';
        var html = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:10px;">';
        for (var asset in s.assets) {
            var a = s.assets[asset];
            html += '<div style="background:#0a0a0a;padding:10px;border-radius:8px;border:1px solid #222;">';
            html += '<div style="font-weight:bold;color:#f7931a;">' + asset + '</div>';
            html += '<div style="font-size:12px;color:#666;">Quantity: ' + a.quantity.toFixed(8) + '</div>';
            html += '<div style="font-size:12px;color:#666;">Invested: ' + a.invested_tnd.toFixed(2) + ' TND</div>';
            html += '<div style="font-size:12px;color:#666;">Value: ' + a.current_value_usd.toFixed(2) + ' USD</div>';
            html += '<div style="font-size:14px;font-weight:bold;color:' + (a.profit_tnd >= 0 ? '#34d399' : '#f87171') + ';">' + (a.profit_tnd >= 0 ? '+' : '') + a.profit_tnd.toFixed(2) + ' TND (' + (a.roi_percent >= 0 ? '+' : '') + a.roi_percent.toFixed(2) + '%)</div>';
            html += '</div>';
        }
        html += '</div>';
        document.getElementById('portfolioAssets').innerHTML = html;
    }
}

async function saveRate() {
    var rate = parseFloat(document.getElementById('tndUsdRate').value);
    if (!rate || rate <= 0) { addLog('Please enter a valid rate', 'error'); return; }
    var data = await callAPI('/api/portfolio/rate', 'POST', { rate: rate });
    if (data && data.success) {
        addLog('Rate updated: ' + rate, 'success');
        loadPortfolio();
    }
}

async function saveFee() {
    var fee = parseFloat(document.getElementById('feePercent').value);
    if (fee < 0) { addLog('Please enter a valid fee', 'error'); return; }
    var data = await callAPI('/api/portfolio/fee', 'POST', { fee: fee });
    if (data && data.success) addLog('Fee updated: ' + fee + '%', 'success');
}

async function buyAsset() {
    var asset = document.getElementById('buyAsset').value;
    var amount = parseFloat(document.getElementById('buyAmount').value);
    if (!amount || amount <= 0) { addLog('Please enter a valid amount', 'error'); return; }
    addLog('Buying ' + asset + ' for ' + amount + ' TND...', 'info');
    var data = await callAPI('/api/portfolio/buy', 'POST', { asset: asset, amount_tnd: amount });
    if (data && data.success) {
        addLog(data.message, 'success');
        loadPortfolio();
        document.getElementById('buyAmount').value = '';
    } else {
        addLog('Error: ' + (data && data.error ? data.error : 'Unknown'), 'error');
    }
}

async function viewPortfolioReport() {
    addLog('Loading portfolio report...', 'info');
    var data = await callAPI('/api/portfolio/weekly-report');
    if (data && data.success) {
        var r = data.report;
        var s = r.summary;
        var msg = '📊 RAPPORT DU PORTEFEUILLE\\n';
        msg += '='.repeat(40) + '\\n';
        msg += 'Date: ' + new Date().toLocaleDateString() + '\\n\\n';
        msg += '💰 Total Invested: ' + s.total_invested_tnd.toFixed(2) + ' TND\\n';
        msg += '💰 Current Value: ' + s.total_current_usd.toFixed(2) + ' USD\\n';
        msg += '📈 Profit/Loss: ' + (s.total_profit_tnd >= 0 ? '+' : '') + s.total_profit_tnd.toFixed(2) + ' TND\\n';
        msg += '📊 ROI: ' + (s.roi_percent >= 0 ? '+' : '') + s.roi_percent.toFixed(2) + '%\\n';
        msg += '\\n🏆 Best Performer: ' + (r.best_performer || 'N/A') + '\\n';
        msg += '📉 Worst Performer: ' + (r.worst_performer || 'N/A') + '\\n';
        msg += '\\n📋 Week Transactions: ' + r.week_count + '\\n';
        msg += '\\n📊 Details by Asset:\\n';
        for (var asset in s.assets) {
            var a = s.assets[asset];
            msg += '\\n' + asset + ':\\n';
            msg += '   Quantity: ' + a.quantity.toFixed(8) + '\\n';
            msg += '   Invested: ' + a.invested_tnd.toFixed(2) + ' TND\\n';
            msg += '   Value: ' + a.current_value_usd.toFixed(2) + ' USD\\n';
            msg += '   Profit: ' + (a.profit_tnd >= 0 ? '+' : '') + a.profit_tnd.toFixed(2) + ' TND\\n';
            msg += '   ROI: ' + (a.roi_percent >= 0 ? '+' : '') + a.roi_percent.toFixed(2) + '%\\n';
        }
        alert(msg);
        addLog('Portfolio report loaded', 'success');
    }
}

document.getElementById('btnCheckPrices').addEventListener('click', checkPrices);
document.getElementById('btnWeeklyReport').addEventListener('click', weeklyReport);

addLog('🤖 Bot 24h/7j - Initialisation...', 'info');
updateStatus();
updatePrices();
loadAnalyses();
loadPortfolio();

setInterval(updateStatus, 5000);
setInterval(updatePrices, 30000);
setInterval(loadAnalyses, 10000);
setInterval(loadPortfolio, 60000);

addLog('✅ Bot 24h/7j actif - Monitoring permanent', 'success');
</script>
</body>
</html>
'''

# ===== PAGE PARAMÈTRES =====
SETTINGS_PAGE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paramètres - LongTerm AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            color: #e5e5e5;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #1a1a1a, #2a2a2a);
            border-radius: 16px;
            padding: 20px 25px;
            margin-bottom: 25px;
            border: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .logo h1 {
            background: linear-gradient(135deg, #f7931a, #ffd700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 24px;
        }
        .logo span { color: #666; font-size: 13px; display: block; }
        .card {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #2a2a2a;
            margin-bottom: 20px;
        }
        .card-title {
            font-size: 16px;
            color: #f7931a;
            font-weight: bold;
            margin-bottom: 16px;
            border-bottom: 1px solid #2a2a2a;
            padding-bottom: 10px;
        }
        .config-row {
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
            flex-wrap: wrap;
            align-items: center;
        }
        .config-row label {
            min-width: 180px;
            font-size: 14px;
            color: #aaa;
        }
        .config-row input, .config-row select {
            flex: 1;
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid #333;
            background: #0a0a0a;
            color: white;
            font-size: 14px;
            min-width: 150px;
        }
        .config-row input:focus, .config-row select:focus { outline: none; border-color: #f7931a; }
        .config-row input::placeholder { color: #444; }
        .btn {
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-info { background: #1e3a5f; color: #60a5fa; }
        .btn-info:hover:not(:disabled) { background: #1e40af; transform: scale(1.02); }
        .btn-success { background: #065f46; color: #34d399; }
        .btn-success:hover:not(:disabled) { background: #047857; transform: scale(1.02); }
        .btn-danger { background: #7f1d1d; color: #f87171; }
        .btn-danger:hover:not(:disabled) { background: #991b1b; transform: scale(1.02); }
        .btn-warning { background: #7c5a1a; color: #fbbf24; }
        .btn-warning:hover:not(:disabled) { background: #9a6d1a; transform: scale(1.02); }
        .btn-back { background: #2a2a2a; color: #888; }
        .btn-back:hover { background: #3a3a3a; color: #fff; }
        .logout-btn {
            background: #4a1a1a;
            border: 1px solid #f87171;
            color: #f87171;
            padding: 8px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .logout-btn:hover { background: #7f1d1d; transform: scale(1.02); }
        .checkbox-group {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .checkbox-group label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: #aaa;
            cursor: pointer;
        }
        .checkbox-group input[type="checkbox"] { width: 18px; height: 18px; accent-color: #f7931a; cursor: pointer; }
        .result-message {
            margin-top: 12px;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 14px;
            display: none;
        }
        .result-message.success { display: block; background: #064e3b; color: #34d399; border: 1px solid #34d399; }
        .result-message.error { display: block; background: #4a1a1a; color: #f87171; border: 1px solid #f87171; }
        .result-message.info { display: block; background: #1a2a4a; color: #60a5fa; border: 1px solid #60a5fa; }
        .btn-group {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 10px;
        }
        .btn-group .btn { flex: 1; min-width: 120px; }
        .channel-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #0a0a0a;
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 8px;
            border: 1px solid #2a2a2a;
        }
        .channel-item:hover { border-color: #444; }
        .channel-name { font-size: 14px; color: #aaa; font-family: monospace; }
        .channel-status {
            font-size: 12px;
            padding: 2px 10px;
            border-radius: 12px;
        }
        .channel-status.active { background: #064e3b; color: #34d399; }
        .channel-status.inactive { background: #4a1a1a; color: #f87171; }
        .channel-actions { display: flex; gap: 8px; }
        .channel-actions button {
            padding: 4px 12px;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .channel-actions .btn-remove { background: #4a1a1a; color: #f87171; }
        .channel-actions .btn-remove:hover { background: #7f1d1d; }
        .channel-actions .btn-toggle { background: #1e3a5f; color: #60a5fa; }
        .channel-actions .btn-toggle:hover { background: #1e40af; }
        @media (max-width: 600px) {
            .config-row { flex-direction: column; align-items: stretch; }
            .config-row label { min-width: auto; }
            .config-row input { min-width: auto; }
            .btn-group .btn { flex: 1 1 100%; }
            .header { flex-direction: column; gap: 10px; text-align: center; }
            .channel-item { flex-direction: column; gap: 8px; align-items: stretch; }
            .channel-actions { justify-content: center; }
        }
        .empty-message { color: #444; text-align: center; padding: 20px; font-style: italic; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo">
            <h1>⚙️ Paramètres</h1>
            <span>LongTerm AI - Configuration</span>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
            <button class="btn btn-back" onclick="window.location.href='/'">← Retour au Dashboard</button>
            <button class="logout-btn" onclick="logout()">🔓 Déconnexion</button>
        </div>
    </div>

    <div class="card">
        <div class="card-title">📡 Chaînes Telegram surveillées</div>
        <div id="channelsList">
            <div class="empty-message">Aucune chaîne configurée</div>
        </div>
        <div class="config-row" style="margin-top:15px;border-top:1px solid #2a2a2a;padding-top:15px;">
            <label>Ajouter une chaîne</label>
            <input type="text" id="newChannel" placeholder="@nom_du_canal" style="flex:1;">
            <button onclick="addChannel()" class="btn btn-success">➕ Ajouter</button>
        </div>
        <div style="font-size:12px;color:#444;margin-top:5px;">Format: @nom_du_canal (ex: @crypto_news_fr)</div>
        <div id="channelResult" style="margin-top:8px;font-size:13px;"></div>
    </div>

    <div class="card">
        <div class="card-title">📊 Intervalle de vérification des prix</div>
        <div class="config-row">
            <label>Minutes entre chaque vérification</label>
            <input type="number" id="priceInterval" placeholder="Minutes (ex: 30)" value="30" min="1" max="1440">
            <button onclick="savePriceInterval()" class="btn btn-info" id="btnInterval">Enregistrer</button>
        </div>
        <div style="font-size:12px;color:#444;">Défaut: 30 minutes (entre 1 et 1440 minutes)</div>
        <div id="intervalResult" style="margin-top:8px;font-size:13px;"></div>
    </div>

    <div class="card">
        <div class="card-title">🔔 Seuil d'alerte de prix</div>
        <div class="config-row">
            <label>Pourcentage de variation pour alerter</label>
            <input type="number" id="alertThreshold" placeholder="% (ex: 5)" value="5" min="0.5" max="50" step="0.5">
            <button onclick="saveAlertThreshold()" class="btn btn-info" id="btnThreshold">Enregistrer</button>
        </div>
        <div style="font-size:12px;color:#444;">Défaut: 5% - Une alerte sera envoyée si un actif varie de ce pourcentage</div>
        <div id="thresholdResult" style="margin-top:8px;font-size:13px;"></div>
    </div>

    <div class="card">
        <div class="card-title">📱 Notifications</div>
        <div class="checkbox-group">
            <label><input type="checkbox" id="notifPrice" checked> Alertes de prix</label>
            <label><input type="checkbox" id="notifNews" checked> Alertes news</label>
            <label><input type="checkbox" id="notifWeekly" checked> Rapport hebdomadaire</label>
        </div>
        <button onclick="saveNotifications()" class="btn btn-success" style="margin-top:15px;" id="btnNotif">Enregistrer les préférences</button>
        <div id="notifResult" style="margin-top:8px;font-size:13px;"></div>
    </div>

    <div class="card">
        <div class="card-title">🛠️ Maintenance</div>
        <div class="btn-group">
            <button onclick="exportData()" class="btn btn-warning" id="btnExport">📥 Exporter les données</button>
            <button onclick="resetBot()" class="btn btn-danger" id="btnReset">🔄 Réinitialiser le bot</button>
        </div>
        <div style="font-size:12px;color:#444;margin-top:10px;">
            Export: Sauvegarde toutes les données en fichier JSON<br>
            Reset: Supprime toutes les données et redémarre le bot
        </div>
        <div id="maintenanceResult" style="margin-top:8px;font-size:13px;"></div>
    </div>

    <div id="settingsResult" class="result-message"></div>

    <div class="card">
        <div class="card-title">📋 Actions récentes</div>
        <div id="settingsLogs" style="max-height:150px;overflow-y:auto;font-size:13px;color:#666;background:#0a0a0a;padding:12px;border-radius:8px;border:1px solid #1a1a1a;">
            <div style="color:#444;">Prêt à configurer</div>
        </div>
    </div>
</div>

<script>
function logout() {
    if (confirm('Voulez-vous vraiment vous déconnecter ?')) {
        localStorage.removeItem('auth');
        window.location.href = '/login';
    }
}

function addLog(msg, type) {
    var log = document.getElementById('settingsLogs');
    var entry = document.createElement('div');
    var time = new Date().toLocaleTimeString();
    var colors = { success: '#34d399', error: '#f87171', info: '#60a5fa', warning: '#fbbf24' };
    entry.innerHTML = '<span style="color:#333;">[' + time + ']</span> <span style="color:' + (colors[type] || '#888') + ';">' + msg + '</span>';
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
    if (log.children.length > 50) log.removeChild(log.firstChild);
}

async function callAPI(endpoint, method, data) {
    method = method || 'GET';
    try {
        var auth = localStorage.getItem('auth') || btoa('admin:admin123');
        var options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + auth
            }
        };
        if (data) options.body = JSON.stringify(data);
        var response = await fetch(endpoint, options);
        if (!response.ok) {
            if (response.status === 401) {
                addLog('⚠️ Session expirée', 'warning');
                localStorage.removeItem('auth');
                window.location.href = '/login';
                return null;
            }
            return { success: false, error: 'HTTP ' + response.status + ' - ' + response.statusText };
        }
        return await response.json();
    } catch (error) {
        return { success: false, error: error.message || 'Erreur réseau' };
    }
}

function showResult(elementId, message, type) {
    var el = document.getElementById(elementId);
    if (!el) return;
    var colors = { success: '#34d399', error: '#f87171', info: '#60a5fa', warning: '#fbbf24' };
    el.style.color = colors[type] || '#888';
    el.textContent = message;
    addLog(message, type);
}

async function loadChannels() {
    var data = await callAPI('/api/settings/channels');
    var list = document.getElementById('channelsList');
    if (!data || !data.success) {
        list.innerHTML = '<div class="empty-message">❌ Erreur de chargement</div>';
        return;
    }
    var channels = data.channels || [];
    if (channels.length === 0) {
        list.innerHTML = '<div class="empty-message">Aucune chaîne configurée</div>';
        return;
    }
    var html = '';
    for (var i = 0; i < channels.length; i++) {
        var ch = channels[i];
        var statusClass = ch.active ? 'active' : 'inactive';
        var statusText = ch.active ? '✅ Actif' : '⛔ Inactif';
        html += '<div class="channel-item">';
        html += '<span class="channel-name">' + ch.channel + '</span>';
        html += '<span class="channel-status ' + statusClass + '">' + statusText + '</span>';
        html += '<div class="channel-actions">';
        html += '<button class="btn-toggle" onclick="toggleChannel(' + i + ')">' + (ch.active ? 'Désactiver' : 'Activer') + '</button>';
        html += '<button class="btn-remove" onclick="removeChannel(' + i + ')">Supprimer</button>';
        html += '</div>';
        html += '</div>';
    }
    list.innerHTML = html;
}

async function addChannel() {
    var input = document.getElementById('newChannel');
    var channel = input.value.trim();
    if (!channel) {
        showResult('channelResult', '❌ Veuillez entrer un nom de chaîne (ex: @crypto_news)', 'error');
        return;
    }
    if (!channel.startsWith('@')) channel = '@' + channel;
    var btn = document.querySelector('.config-row .btn-success');
    btn.disabled = true;
    btn.textContent = '⏳ Ajout...';
    var data = await callAPI('/api/settings/channels/add', 'POST', { channel: channel });
    btn.disabled = false;
    btn.textContent = '➕ Ajouter';
    if (data && data.success) {
        showResult('channelResult', '✅ Chaîne ajoutée: ' + channel, 'success');
        input.value = '';
        loadChannels();
    } else {
        showResult('channelResult', '❌ Erreur: ' + (data.error || 'Inconnue'), 'error');
    }
}

async function removeChannel(index) {
    if (!confirm('⚠️ Voulez-vous vraiment supprimer cette chaîne ?')) return;
    var data = await callAPI('/api/settings/channels/remove', 'POST', { index: index });
    if (data && data.success) {
        showResult('channelResult', '✅ Chaîne supprimée', 'success');
        loadChannels();
    } else {
        showResult('channelResult', '❌ Erreur: ' + (data.error || 'Inconnue'), 'error');
    }
}

async function toggleChannel(index) {
    var data = await callAPI('/api/settings/channels/toggle', 'POST', { index: index });
    if (data && data.success) {
        showResult('channelResult', '✅ Statut de la chaîne modifié', 'success');
        loadChannels();
    } else {
        showResult('channelResult', '❌ Erreur: ' + (data.error || 'Inconnue'), 'error');
    }
}

async function savePriceInterval() {
    var btn = document.getElementById('btnInterval');
    var minutes = parseInt(document.getElementById('priceInterval').value);
    if (!minutes || minutes < 1) {
        showResult('intervalResult', '❌ Entrez un nombre valide (≥ 1 minute)', 'error');
        return;
    }
    btn.disabled = true;
    btn.textContent = '⏳ En cours...';
    var data = await callAPI('/api/settings/interval', 'POST', { interval_minutes: minutes });
    btn.disabled = false;
    btn.textContent = 'Enregistrer';
    if (data && data.success) {
        showResult('intervalResult', '✅ Intervalle mis à jour: ' + minutes + ' minutes', 'success');
    } else {
        showResult('intervalResult', '❌ Erreur: ' + (data.error || 'Inconnue'), 'error');
    }
}

async function saveAlertThreshold() {
    var btn = document.getElementById('btnThreshold');
    var threshold = parseFloat(document.getElementById('alertThreshold').value);
    if (!threshold || threshold < 0) {
        showResult('thresholdResult', '❌ Entrez un pourcentage valide', 'error');
        return;
    }
    btn.disabled = true;
    btn.textContent = '⏳ En cours...';
    var data = await callAPI('/api/settings/threshold', 'POST', { threshold_percent: threshold });
    btn.disabled = false;
    btn.textContent = 'Enregistrer';
    if (data && data.success) {
        showResult('thresholdResult', '✅ Seuil mis à jour: ' + threshold + '%', 'success');
    } else {
        showResult('thresholdResult', '❌ Erreur: ' + (data.error || 'Inconnue'), 'error');
    }
}

async function saveNotifications() {
    var btn = document.getElementById('btnNotif');
    var settings = {
        price: document.getElementById('notifPrice').checked,
        news: document.getElementById('notifNews').checked,
        weekly: document.getElementById('notifWeekly').checked
    };
    btn.disabled = true;
    btn.textContent = '⏳ En cours...';
    var data = await callAPI('/api/settings/notifications', 'POST', settings);
    btn.disabled = false;
    btn.textContent = 'Enregistrer les préférences';
    if (data && data.success) {
        showResult('notifResult', '✅ Préférences de notification enregistrées', 'success');
    } else {
        showResult('notifResult', '❌ Erreur: ' + (data.error || 'Inconnue'), 'error');
    }
}

async function exportData() {
    var btn = document.getElementById('btnExport');
    btn.disabled = true;
    btn.textContent = '⏳ Export...';
    showResult('maintenanceResult', '⏳ Export en cours...', 'info');
    var data = await callAPI('/api/export-data');
    btn.disabled = false;
    btn.textContent = '📥 Exporter les données';
    if (data && data.success) {
        try {
            var json = JSON.stringify(data.data, null, 2);
            var blob = new Blob([json], {type: 'application/json'});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'longterm-ai-data-' + new Date().toISOString().slice(0,10) + '.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(function() { URL.revokeObjectURL(url); }, 10000);
            showResult('maintenanceResult', '✅ Export terminé! Fichier téléchargé', 'success');
        } catch (e) {
            showResult('maintenanceResult', '❌ Erreur lors du téléchargement: ' + e.message, 'error');
        }
    } else {
        showResult('maintenanceResult', '❌ Erreur: ' + (data.error || 'Aucune donnée à exporter'), 'error');
    }
}

async function resetBot() {
    if (!confirm('⚠️ Voulez-vous vraiment réinitialiser le bot ? Toutes les données seront effacées.')) return;
    var btn = document.getElementById('btnReset');
    btn.disabled = true;
    btn.textContent = '⏳ Reset...';
    showResult('maintenanceResult', '⏳ Réinitialisation en cours...', 'info');
    var data = await callAPI('/api/reset', 'POST');
    btn.disabled = false;
    btn.textContent = '🔄 Réinitialiser le bot';
    if (data && data.success) {
        showResult('maintenanceResult', '✅ Bot réinitialisé avec succès. Redirection...', 'success');
        setTimeout(function() { window.location.href = '/'; }, 2000);
    } else {
        showResult('maintenanceResult', '❌ Erreur: ' + (data.error || 'Inconnue'), 'error');
    }
}

async function loadSettings() {
    try {
        var data = await callAPI('/api/status');
        if (data && data.config) {
            var config = data.config;
            if (config.price_interval) document.getElementById('priceInterval').value = config.price_interval;
            if (config.alert_threshold) document.getElementById('alertThreshold').value = config.alert_threshold;
            if (config.notifications) {
                if (config.notifications.price !== undefined) document.getElementById('notifPrice').checked = config.notifications.price;
                if (config.notifications.news !== undefined) document.getElementById('notifNews').checked = config.notifications.news;
                if (config.notifications.weekly !== undefined) document.getElementById('notifWeekly').checked = config.notifications.weekly;
            }
            addLog('✅ Paramètres chargés depuis le serveur', 'success');
        }
    } catch (e) {
        addLog('⚠️ Impossible de charger les paramètres', 'warning');
    }
}

addLog('📋 Page paramètres chargée', 'info');
loadSettings();
loadChannels();

async function testServer() {
    try {
        var response = await fetch('/api/status');
        if (response.ok) {
            addLog('✅ Serveur connecté', 'success');
        } else {
            addLog('⚠️ Serveur accessible mais erreur ' + response.status, 'warning');
        }
    } catch (e) {
        addLog('❌ Serveur inaccessible - Vérifiez que le bot tourne', 'error');
    }
}
setTimeout(testServer, 1000);
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
    auth_cookie = request.cookies.get("auth")
    if auth_cookie:
        try:
            decoded = base64.b64decode(auth_cookie).decode("utf-8")
            username, password = decoded.split(":")
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                return HTMLResponse(MAIN_PAGE)
        except:
            pass
    
    if check_auth_header(request):
        return HTMLResponse(MAIN_PAGE)
    
    return HTMLResponse(MAIN_PAGE)

@app.get("/settings")
async def settings_page(request: Request):
    auth_cookie = request.cookies.get("auth")
    if auth_cookie:
        try:
            decoded = base64.b64decode(auth_cookie).decode("utf-8")
            username, password = decoded.split(":")
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                return HTMLResponse(SETTINGS_PAGE)
        except:
            pass
    
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
    print("🔐 Identifiants par défaut:")
    print("   Utilisateur: admin")
    print("   Mot de passe: admin123")
    print("=" * 50)
    print("🤖 Bot 24h/7j actif en permanence")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000)
