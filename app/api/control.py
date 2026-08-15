"""
API de contrôle du bot
"""

from fastapi import APIRouter, Header, HTTPException
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Contrôle"])

# Configuration simple (à remplacer par .env plus tard)
ADMIN_PASSWORD = "admin123"

def check_auth(password: str = Header(...)):
    """Vérifier l'authentification"""
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")

# Statut du bot (en mémoire pour l'instant)
bot_status = {
    "running": False,
    "start_time": None,
    "last_update": None
}

@router.get("/status")
async def get_status(password: str = Header(...)):
    """Obtenir le statut du bot"""
    check_auth(password)
    return {
        "running": bot_status["running"],
        "status": "running" if bot_status["running"] else "stopped",
        "start_time": bot_status["start_time"],
        "last_update": bot_status["last_update"]
    }

@router.post("/start")
async def start_bot(password: str = Header(...)):
    """Démarrer le bot"""
    check_auth(password)
    global bot_status
    
    if bot_status["running"]:
        return {"message": "Bot déjà en cours", "status": "already_running"}
    
    bot_status["running"] = True
    bot_status["start_time"] = datetime.now().isoformat()
    bot_status["last_update"] = datetime.now().isoformat()
    
    logger.info("✅ Bot démarré via API")
    return {"message": "Bot démarré avec succès", "status": "started"}

@router.post("/stop")
async def stop_bot(password: str = Header(...)):
    """Arrêter le bot"""
    check_auth(password)
    global bot_status
    
    if not bot_status["running"]:
        return {"message": "Bot déjà arrêté", "status": "already_stopped"}
    
    bot_status["running"] = False
    bot_status["last_update"] = datetime.now().isoformat()
    
    logger.info("🛑 Bot arrêté via API")
    return {"message": "Bot arrêté avec succès", "status": "stopped"}

@router.get("/stats")
async def get_stats(password: str = Header(...)):
    """Obtenir les statistiques"""
    check_auth(password)
    return {
        "uptime": "0h 0m",
        "total_analyzed": 0,
        "total_alerts": 0,
        "last_analysis": None
    }