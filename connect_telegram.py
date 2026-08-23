# connect_telegram.py
import asyncio
import os
from telethon import TelegramClient

# ===== CONFIGURATION =====
API_ID = 38955597  # METTEZ VOTRE API_ID ICI
API_HASH = "275fbac1b68e0984459d044b9b1a20cf"  # METTEZ VOTRE API_HASH ICI
PHONE = "+21699038382"  # VOTRE NUMERO

async def main():
    print("=" * 60)
    print("🔐 CONNEXION TELEGRAM")
    print("=" * 60)
    print(f"📞 Numéro: {PHONE}")
    print("=" * 60)
    
    # Vérifier la version de Telethon
    import telethon
    print(f"📱 Telethon version: {telethon.__version__}")
    print("=" * 60)
    
    os.makedirs("session", exist_ok=True)
    
    # Supprimer l'ancienne session
    if os.path.exists("session/telegram_render.session"):
        os.remove("session/telegram_render.session")
        print("🗑️ Ancienne session supprimée")
    
    client = TelegramClient("session/telegram_render", API_ID, API_HASH)
    
    try:
        print("🔄 Connexion...")
        
        # Connexion sans start() pour éviter l'erreur
        await client.connect()
        
        if not await client.is_user_authorized():
            print("📲 Demande de code...")
            await client.send_code_request(PHONE)
            code = input("🔑 Entrez le code reçu: ")
            
            try:
                await client.sign_in(PHONE, code)
            except Exception as e:
                print(f"❌ Erreur: {e}")
                return
        
        me = await client.get_me()
        print()
        print("=" * 60)
        print("✅ CONNEXION RÉUSSIE !")
        print(f"👤 Nom: {me.first_name} (@{me.username})")
        print(f"📁 Session: session/telegram_render.session")
        print("=" * 60)
        print()
        print("📌 Ajoutez à Git et poussez sur Render")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
        print("💡 Solutions:")
        print("   1. Vérifiez API_ID et API_HASH")
        print("   2. Téléthon version: pip install telethon==1.28.5")
        
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
