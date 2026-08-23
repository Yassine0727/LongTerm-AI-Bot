# connect_telegram.py
import asyncio
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

<<<<<<< HEAD
# ===== MODIFIEZ CES 3 LIGNES =====
API_ID = 38955597  # METTEZ VOTRE API_ID ICI
=======
# ===== CONFIGURATION - MODIFIEZ CES 3 LIGNES =====
API_ID = 38955597 # METTEZ VOTRE API_ID ICI (ex: 1234567)
>>>>>>> 7d773253044c08b9ad62c8be6dfb2059af44b6ea
API_HASH = "275fbac1b68e0984459d044b9b1a20cf"  # METTEZ VOTRE API_HASH ICI
PHONE = "+21699038382"  # VOTRE NUMERO

async def main():
    print("=" * 60)
<<<<<<< HEAD
    print("🔐 CRÉATION SESSION TELEGRAM")
=======
    print("🔐 CONNEXION TELEGRAM - CRÉATION SESSION")
>>>>>>> 7d773253044c08b9ad62c8be6dfb2059af44b6ea
    print("=" * 60)
    
    # Vérifier la version
    import telethon
    print(f"📱 Telethon version: {telethon.__version__}")
    print(f"📞 Numéro: {PHONE}")
    print("=" * 60)
    
    # Créer le dossier session
    os.makedirs("session", exist_ok=True)
    
<<<<<<< HEAD
    # Supprimer l'ancienne session si elle existe
=======
    # Supprimer l'ancienne session
>>>>>>> 7d773253044c08b9ad62c8be6dfb2059af44b6ea
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
<<<<<<< HEAD
        print(f"📁 Session: session/telegram_render.session")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
=======
        print(f"🆔 ID: {me.id}")
        print(f"📁 Session: session/telegram_render.session")
        print("=" * 60)
        print()
        print("📌 PROCHAINES ÉTAPES:")
        print("   1. Ajoutez le fichier de session à Git:")
        print("      git add session/telegram_render.session")
        print("   2. Committez et poussez:")
        print("      git commit -m 'Ajout session Telegram'")
        print("      git push origin main")
        print()
        print("✅ Le bot utilisera cette session sur Render !")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
        print("💡 SOLUTIONS:")
        print("   1. Vérifiez API_ID et API_HASH sur https://my.telegram.org/apps")
        print("   2. Vérifiez que votre numéro est correct")
        print("   3. Installez: pip install telethon==1.28.5")
>>>>>>> 7d773253044c08b9ad62c8be6dfb2059af44b6ea
        
    finally:
        await client.disconnect()
        print("🔌 Déconnecté")

if __name__ == "__main__":
<<<<<<< HEAD
    asyncio.run(main())
=======
    asyncio.run(main())
>>>>>>> 7d773253044c08b9ad62c8be6dfb2059af44b6ea
