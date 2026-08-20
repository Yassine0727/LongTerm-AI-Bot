# create_session.py
import asyncio
import os
from telethon import TelegramClient

# ===== VOS IDENTIFIANTS TELEGRAM =====
# À remplacer par vos vraies valeurs
API_ID = 38955597              # Votre API ID
API_HASH = "275fbac1b68e0984459d044b9b1a20cf"   # Votre API Hash
PHONE = "+21699038382"        # Votre numéro avec indicatif

async def main():
    # Créer le dossier session s'il n'existe pas
    os.makedirs("session", exist_ok=True)
    
    # Créer le client Telegram
    client = TelegramClient("session/telegram", API_ID, API_HASH)
    
    print("=" * 50)
    print("📱 Connexion à Telegram...")
    print("=" * 50)
    print(f"📞 Numéro: {PHONE}")
    print("📲 Un code de vérification va vous être envoyé")
    print("=" * 50)
    
    # Démarrer la connexion
    await client.start(phone=PHONE)
    
    # Vérifier la connexion
    me = await client.get_me()
    print("=" * 50)
    print(f"✅ Connecté avec succès !")
    print(f"👤 Nom: {me.first_name} {me.last_name or ''}")
    print(f"🆔 Username: @{me.username}" if me.username else "🆔 Pas d'username")
    print("=" * 50)
    
    # Tester l'accès à un canal (optionnel)
    try:
        channel = await client.get_entity("@testbot1252")
        print(f"📢 Canal trouvé: {channel.title}")
    except Exception as e:
        print(f"⚠️ Canal non trouvé: {e}")
    
    await client.disconnect()
    print("=" * 50)
    print("✅ Session sauvegardée dans: session/telegram.session")
    print("📁 Vous pouvez maintenant pousser ce fichier sur GitHub")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())