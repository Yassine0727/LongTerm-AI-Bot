# create_session.py
import asyncio
import os
from telethon import TelegramClient

# ===== CONFIGURATION =====
API_ID = 0  # METTEZ VOTRE API_ID ICI
API_HASH = "votre_api_hash"  # METTEZ VOTRE API_HASH ICI
PHONE = "+21699038382"  # VOTRE NUMERO

async def main():
    print("=" * 50)
    print("🔐 AUTHENTIFICATION TELEGRAM")
    print("=" * 50)
    print("📞 Numéro: " + PHONE)
    print("=" * 50)
    
    # Créer le dossier session
    os.makedirs("session", exist_ok=True)
    
    # Supprimer l'ancienne session si elle existe
    if os.path.exists("session/telegram_render.session"):
        os.remove("session/telegram_render.session")
        print("🗑️ Ancienne session supprimée")
    
    # Créer le client
    client = TelegramClient("session/telegram_render", API_ID, API_HASH)
    
    try:
        print("🔄 Connexion en cours...")
        print("📲 Un code de vérification va vous être envoyé")
        print("   (par SMS ou dans Telegram)")
        print("=" * 50)
        
        # Démarrer l'authentification
        await client.start(phone=PHONE)
        
        # Récupérer les infos
        me = await client.get_me()
        print("=" * 50)
        print("✅ CONNEXION RÉUSSIE !")
        print(f"👤 Nom: {me.first_name}")
        print(f"📱 Username: @{me.username}")
        print(f"🆔 ID: {me.id}")
        print(f"📁 Session: session/telegram_render.session")
        print("=" * 50)
        print("📌 Cette session est prête pour Render")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("\nSolutions:")
        print("   1. Vérifiez API_ID et API_HASH sur https://my.telegram.org/apps")
        print("   2. Vérifiez que votre numéro est correct")
        print("   3. Assurez-vous que votre compte Telegram est actif")
        
    finally:
        await client.disconnect()
        print("🔌 Déconnecté")

if __name__ == "__main__":
    asyncio.run(main())
