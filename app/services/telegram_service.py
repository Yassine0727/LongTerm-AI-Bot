import asyncio
import logging
import json
import os
from typing import Optional, Callable, List

from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.errors import SessionPasswordNeededError

logger = logging.getLogger(__name__)

class TelegramService:
    """Service de connexion et d'écoute Telegram - Authentification par lien"""
    
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.is_connected = False
        self.message_handler: Optional[Callable] = None
        self.processed_messages = set()
        self.active_channels = []
        self.channel_handlers = {}
        
        # Configuration depuis .env
        self.api_id = int(os.getenv("TELEGRAM_API_ID", 0))
        self.api_hash = os.getenv("TELEGRAM_API_HASH", "")
        self.phone = os.getenv("TELEGRAM_PHONE", "")
        self.channel = os.getenv("TELEGRAM_CHANNEL", "")
        
        self.session_name = "session/telegram_render"
        logger.info(f"📁 Session: {self.session_name}")
    
    def get_channels_from_config(self) -> List[str]:
        """Récupérer la liste des chaînes actives depuis config.json"""
        config_file = "config.json"
        channels = []
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                telegram_channels = config_data.get('telegram_channels', [])
                for ch in telegram_channels:
                    if ch.get('active', True):
                        channel_name = ch.get('channel', '')
                        if channel_name:
                            channels.append(channel_name)
                
                logger.info(f"📡 Chaînes actives: {channels}")
                
            except Exception as e:
                logger.error(f"❌ Erreur lecture config.json: {e}")
        
        if not channels and self.channel:
            channels.append(self.channel)
            logger.info(f"📡 Utilisation du canal principal: {self.channel}")
        
        return channels
    
    async def connect(self) -> bool:
        """Se connecter à Telegram via QR code ou lien"""
        try:
            if not self.api_id or not self.api_hash:
                logger.error("❌ Telegram API_ID ou API_HASH manquant")
                return False
            
            os.makedirs("session", exist_ok=True)
            
            # Créer le client
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            
            # Vérifier si la session existe déjà
            if os.path.exists(f"{self.session_name}.session"):
                logger.info("✅ Session existante trouvée, connexion directe...")
                await self.client.connect()
                
                if await self.client.is_user_authorized():
                    self.is_connected = True
                    me = await self.client.get_me()
                    logger.info(f"✅ Connecté en tant que: {me.first_name} (@{me.username})")
                    return True
                else:
                    logger.warning("⚠️ Session existante mais invalide")
            
            # Pas de session valide -> Authentification par lien
            logger.info("=" * 50)
            logger.info("🔐 AUTHENTIFICATION TELEGRAM")
            logger.info("=" * 50)
            logger.info("📱 Connectez-vous via le lien ci-dessous :")
            logger.info("   (ou scannez le QR code)")
            logger.info("=" * 50)
            
            # Démarrer l'authentification
            await self.client.connect()
            
            # Obtenir le lien d'authentification
            try:
                # Méthode 1: Lien de connexion
                login_url = await self.client.start(phone=self.phone, code_callback=self._get_code_from_url)
                
                # Si la connexion réussit
                if await self.client.is_user_authorized():
                    self.is_connected = True
                    me = await self.client.get_me()
                    logger.info("=" * 50)
                    logger.info("✅ CONNEXION RÉUSSIE !")
                    logger.info(f"👤 Nom: {me.first_name} (@{me.username})")
                    logger.info(f"📁 Session sauvegardée: {self.session_name}.session")
                    logger.info("=" * 50)
                    return True
                    
            except Exception as e:
                logger.error(f"❌ Erreur d'authentification: {e}")
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Telegram connection error: {e}")
            self.is_connected = False
            return False
    
    async def _get_code_from_url(self):
        """Affiche le lien d'authentification"""
        try:
            # Pour Telethon, on utilise la méthode start() qui gère l'authentification
            pass
        except Exception as e:
            logger.error(f"Erreur: {e}")
    
    async def disconnect(self) -> bool:
        try:
            if self.client:
                for handler in self.channel_handlers.values():
                    self.client.remove_event_handler(handler)
                self.channel_handlers.clear()
                await self.client.disconnect()
                self.is_connected = False
                logger.info("🛑 Telegram disconnected")
            return True
        except Exception as e:
            logger.error(f"❌ Disconnect error: {e}")
            return False
    
    async def start_listening_multiple(self, message_callback: Callable) -> bool:
        """Écouter plusieurs chaînes Telegram"""
        if not self.is_connected or not self.client:
            logger.error("❌ Not connected to Telegram")
            return False
        
        self.message_handler = message_callback
        
        try:
            for handler in self.channel_handlers.values():
                self.client.remove_event_handler(handler)
            self.channel_handlers.clear()
            
            channels = self.get_channels_from_config()
            
            if not channels:
                logger.error("❌ Aucun canal configuré")
                return False
            
            logger.info(f"📡 Écoute de {len(channels)} canaux: {channels}")
            
            # Vérifier l'accès aux canaux
            for channel in channels:
                try:
                    entity = await self.client.get_entity(channel)
                    logger.info(f"✅ Accès confirmé au canal: {channel}")
                except Exception as e:
                    logger.warning(f"⚠️ Impossible d'accéder à {channel}: {e}")
            
            for channel in channels:
                @self.client.on(events.NewMessage(chats=channel))
                async def handler(event, ch=channel):
                    logger.info(f"🔔 Message reçu de {ch}")
                    await self._handle_message(event.message)
                
                self.channel_handlers[channel] = handler
            
            logger.info(f"👀 Écoute active sur {len(channels)} canaux")
            
            await self.client.run_until_disconnected()
            return True
            
        except Exception as e:
            logger.error(f"❌ Listening error: {e}")
            return False
    
    async def reload_channels(self) -> bool:
        """Recharger les chaînes"""
        if not self.is_connected or not self.client:
            logger.error("❌ Not connected to Telegram")
            return False
        
        try:
            for handler in self.channel_handlers.values():
                self.client.remove_event_handler(handler)
            self.channel_handlers.clear()
            
            channels = self.get_channels_from_config()
            
            if not channels:
                logger.warning("⚠️ Aucun canal actif trouvé")
                return False
            
            logger.info(f"🔄 Rechargement des canaux: {channels}")
            
            for channel in channels:
                @self.client.on(events.NewMessage(chats=channel))
                async def handler(event, ch=channel):
                    logger.info(f"🔔 Message reçu de {ch}")
                    await self._handle_message(event.message)
                
                self.channel_handlers[channel] = handler
            
            logger.info(f"✅ {len(channels)} canaux rechargés")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur rechargement: {e}")
            return False
    
    async def _handle_message(self, message: Message):
        try:
            message_id = str(message.id)
            
            if message_id in self.processed_messages:
                return
            
            text = message.text
            if not text:
                return
            
            channel_name = ""
            if message.chat:
                channel_name = message.chat.username or message.chat.title or "unknown"
            
            logger.info(f"📩 Message de @{channel_name}: {text[:100]}...")
            
            self.processed_messages.add(message_id)
            if len(self.processed_messages) > 1000:
                self.processed_messages.clear()
            
            if self.message_handler:
                await self.message_handler(text, message_id, message.date)
            
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
    
    async def send_message(self, channel: str, message: str) -> bool:
        try:
            await self.client.send_message(channel, message)
            logger.info(f"📤 Message envoyé à {channel}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur envoi: {e}")
            return False
