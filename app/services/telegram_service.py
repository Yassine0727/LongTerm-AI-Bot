import asyncio
import logging
import json
import os
from typing import Optional, Callable, List

from telethon import TelegramClient, events
from telethon.tl.types import Message

from app.core.config import config

logger = logging.getLogger(__name__)

class TelegramService:
    """Service de connexion et d'écoute Telegram"""
    
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.is_connected = False
        self.message_handler: Optional[Callable] = None
        self.processed_messages = set()
        self.active_channels = []  # Stocker les canaux actifs
        self.channel_handlers = {}  # Stocker les handlers par canal
        
        self.api_id = config.TELEGRAM_API_ID
        self.api_hash = config.TELEGRAM_API_HASH
        self.phone = config.TELEGRAM_PHONE
        self.channel = config.TELEGRAM_CHANNEL
    
    def get_channels_from_config(self) -> List[str]:
        """Récupérer la liste des chaînes actives depuis config.json"""
        config_file = "config.json"
        channels = []
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Récupérer les chaînes actives
                telegram_channels = config_data.get('telegram_channels', [])
                for ch in telegram_channels:
                    if ch.get('active', True):
                        channel_name = ch.get('channel', '')
                        if channel_name:
                            channels.append(channel_name)
                
                logger.info(f"📡 Chaînes actives depuis config.json: {channels}")
                
            except Exception as e:
                logger.error(f"❌ Erreur lecture config.json: {e}")
        
        # Si aucune chaîne trouvée, utiliser le canal principal
        if not channels and self.channel:
            channels.append(self.channel)
            logger.info(f"📡 Utilisation du canal principal: {self.channel}")
        
        return channels
    
    async def connect(self) -> bool:
        try:
            if not self.api_id or not self.api_hash:
                logger.error("❌ Telegram config incomplete")
                return False
            
            logger.info(f"🔑 Connexion avec API_ID: {self.api_id}")
            
            self.client = TelegramClient(
                'session/telegram',
                self.api_id,
                self.api_hash
            )
            
            await self.client.start(phone=self.phone)
            self.is_connected = True
            
            logger.info("✅ Telegram connected successfully")
            
            # Récupérer les informations du compte
            me = await self.client.get_me()
            logger.info(f"👤 Connecté en tant que: {me.first_name} (@{me.username})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Telegram connection error: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        try:
            if self.client:
                # Supprimer tous les handlers
                if hasattr(self.client, 'remove_event_handler'):
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
    
    async def start_listening(self, message_callback: Callable) -> bool:
        """Écouter un seul canal (méthode originale)"""
        if not self.is_connected or not self.client:
            logger.error("❌ Not connected to Telegram")
            return False
        
        self.message_handler = message_callback
        
        try:
            @self.client.on(events.NewMessage(chats=self.channel))
            async def handler(event):
                logger.info(f"🔔 ÉVÉNEMENT DÉCLENCHÉ pour {self.channel}")
                await self._handle_message(event.message)
            
            logger.info(f"👀 Listening to channel: {self.channel}")
            await self.client.run_until_disconnected()
            return True
            
        except Exception as e:
            logger.error(f"❌ Listening error: {e}")
            return False
    
    async def start_listening_multiple(self, message_callback: Callable) -> bool:
        """Écouter plusieurs chaînes Telegram depuis config.json avec rechargement dynamique"""
        if not self.is_connected or not self.client:
            logger.error("❌ Not connected to Telegram")
            return False
        
        self.message_handler = message_callback
        
        try:
            # Nettoyer les anciens handlers
            for handler in self.channel_handlers.values():
                self.client.remove_event_handler(handler)
            self.channel_handlers.clear()
            
            # Récupérer les chaînes actives
            channels = self.get_channels_from_config()
            
            if not channels:
                logger.error("❌ Aucun canal configuré")
                return False
            
            logger.info(f"📡 Écoute de {len(channels)} canaux: {channels}")
            
            # Vérifier l'accès aux canaux
            for channel in channels:
                try:
                    entity = await self.client.get_entity(channel)
                    logger.info(f"✅ Accès confirmé au canal: {channel} (ID: {entity.id})")
                except Exception as e:
                    logger.warning(f"⚠️ Impossible d'accéder au canal {channel}: {e}")
                    logger.warning(f"   Assurez-vous que le bot est membre du canal")
            
            # Ajouter un handler pour chaque canal
            for channel in channels:
                @self.client.on(events.NewMessage(chats=channel))
                async def handler(event, ch=channel):
                    logger.info(f"🔔 ÉVÉNEMENT DÉCLENCHÉ pour {ch}")
                    
                    # Vérifier si la chaîne est toujours active
                    config_file = "config.json"
                    is_active = True
                    if os.path.exists(config_file):
                        try:
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                            telegram_channels = config_data.get('telegram_channels', [])
                            for c in telegram_channels:
                                if c.get('channel') == ch:
                                    is_active = c.get('active', True)
                                    break
                        except:
                            pass
                    
                    if is_active:
                        logger.info(f"📩 Nouveau message reçu de {ch}")
                        await self._handle_message(event.message)
                    else:
                        logger.info(f"⏭️ Message ignoré de {ch} (chaîne désactivée)")
                
                self.channel_handlers[channel] = handler
            
            logger.info(f"👀 Écoute active sur {len(channels)} canaux")
            
            # Démarrer l'écoute
            await self.client.run_until_disconnected()
            return True
            
        except Exception as e:
            logger.error(f"❌ Listening error: {e}")
            return False
    
    async def reload_channels(self) -> bool:
        """Recharger les chaînes en cours d'exécution"""
        if not self.is_connected or not self.client:
            logger.error("❌ Not connected to Telegram")
            return False
        
        try:
            # Nettoyer les anciens handlers
            for handler in self.channel_handlers.values():
                self.client.remove_event_handler(handler)
            self.channel_handlers.clear()
            
            # Récupérer les chaînes actives
            channels = self.get_channels_from_config()
            
            if not channels:
                logger.warning("⚠️ Aucun canal actif trouvé")
                return False
            
            logger.info(f"🔄 Rechargement des canaux: {channels}")
            
            # Ajouter un handler pour chaque canal
            for channel in channels:
                @self.client.on(events.NewMessage(chats=channel))
                async def handler(event, ch=channel):
                    logger.info(f"🔔 ÉVÉNEMENT DÉCLENCHÉ pour {ch}")
                    
                    # Vérifier si la chaîne est toujours active
                    config_file = "config.json"
                    is_active = True
                    if os.path.exists(config_file):
                        try:
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                            telegram_channels = config_data.get('telegram_channels', [])
                            for c in telegram_channels:
                                if c.get('channel') == ch:
                                    is_active = c.get('active', True)
                                    break
                        except:
                            pass
                    
                    if is_active:
                        logger.info(f"📩 Nouveau message reçu de {ch}")
                        await self._handle_message(event.message)
                    else:
                        logger.info(f"⏭️ Message ignoré de {ch} (chaîne désactivée)")
                
                self.channel_handlers[channel] = handler
            
            logger.info(f"✅ {len(channels)} canaux rechargés")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur rechargement: {e}")
            return False
    
    async def _handle_message(self, message: Message):
        try:
            logger.info(f"🔍 _handle_message appelé - ID: {message.id}")
            
            message_id = str(message.id)
            
            # Vérifier si déjà traité
            if message_id in self.processed_messages:
                logger.info(f"⏭️ Message déjà traité: {message_id}")
                return
            
            text = message.text
            if not text:
                logger.info(f"📭 Message sans texte - ID: {message_id}")
                return
            
            # Récupérer le nom du canal
            channel_name = ""
            if message.chat:
                channel_name = message.chat.username or message.chat.title or "unknown"
            
            logger.info(f"📩 Message reçu de @{channel_name}: {text[:100]}...")
            
            self.processed_messages.add(message_id)
            if len(self.processed_messages) > 1000:
                self.processed_messages.clear()
            
            if self.message_handler:
                logger.info(f"📤 Appel du message_handler pour: {text[:50]}...")
                await self.message_handler(text, message_id, message.date)
                logger.info(f"✅ message_handler exécuté avec succès")
            else:
                logger.warning("⚠️ Aucun message_handler configuré")
            
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
    
    async def send_test_message(self, channel: str = None) -> bool:
        """Envoyer un message de test"""
        try:
            target = channel or self.channel
            if not target:
                logger.error("❌ Aucun canal cible")
                return False
            
            logger.info(f"📤 Envoi d'un message de test à {target}")
            await self.client.send_message(
                target,
                "🤖 Test du bot LongTerm AI - Connexion établie!"
            )
            logger.info(f"✅ Message de test envoyé à {target}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi test: {e}")
            return False
    
    async def get_recent_messages(self, channel: str = None, limit: int = 10) -> List[Message]:
        """Récupérer les derniers messages d'un canal"""
        try:
            target = channel or self.channel
            if not target:
                logger.error("❌ Aucun canal cible")
                return []
            
            logger.info(f"📥 Récupération des {limit} derniers messages de {target}")
            messages = []
            async for message in self.client.iter_messages(target, limit=limit):
                messages.append(message)
            
            logger.info(f"📥 {len(messages)} messages récupérés de {target}")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération messages: {e}")
            return []
    
    async def list_joined_channels(self) -> List[dict]:
        """Liste tous les canaux où le bot est membre"""
        try:
            logger.info("📡 Récupération de la liste des canaux...")
            dialogs = await self.client.get_dialogs()
            channels = []
            for dialog in dialogs:
                if dialog.is_channel:
                    channels.append({
                        "name": dialog.name,
                        "username": dialog.entity.username,
                        "id": dialog.id,
                        "participants_count": getattr(dialog.entity, 'participants_count', None)
                    })
            logger.info(f"📡 Canaux où le bot est membre: {len(channels)}")
            for ch in channels:
                logger.info(f"   - {ch['name']} (@{ch['username']})")
            return channels
        except Exception as e:
            logger.error(f"❌ Erreur liste canaux: {e}")
            return []
