# connect_telegram.py
import asyncio
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# ===== MODIFIEZ CES 3 LIGNES =====
API_ID = 38955597  # METTEZ VOTRE API_ID ICI
API_HASH = "275fbac1b68e0984459d044b9b1a20cf"  # METTEZ VOTRE API_HASH ICI
PHONE = "+21699038382"  # VOTRE NUMERO

async def main():
    print("=" * 60)
    print("🔐 CRÉATION SESSION TELEGRAM")
    print("=" * 60)
    
    # Vérifier la version
    import telethon
    print(f"📱 Telethon version: {telethon.__version__}")
    print(f"📞 Numéro: {PHONE}")
    print("=" * 60)
    
    # Créer le dossier session
    os.makedirs("session", exist_ok=True)
    
    # Supprimer l'ancienne session si elle existe
    if os.path.exists("session/telegram_render.session"):
        os.remove("session/telegram_render.session")
        print("🗑️ Ancienne session supprimée")
    
    client = TelegramClient("session/telegram_render", API_ID, API_HASH)
    
    try:
        print("🔄 Connexion à Telegram...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print("📲 Envoi du code de vérification...")
            await client.send_code_request(PHONE)
            print("✅ Code envoyé !")
            code = input("🔑 Entrez le code reçu: ")
            
            try:
                await client.sign_in(PHONE, code)
            except SessionPasswordNeededError:
                password = input("🔐 Mot de passe 2FA: ")
                await client.sign_in(password=password)
        
        me = await client.get_me()
        print()
        print("=" * 60)
        print("✅ CONNEXION RÉUSSIE !")
        print(f"👤 Nom: {me.first_name} (@{me.username})")
        print(f"📁 Session: session/telegram_render.session")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        
    finally:
        await client.disconnect()
        print("🔌 Déconnecté")

if __name__ == "__main__":
    asyncio.run(main())