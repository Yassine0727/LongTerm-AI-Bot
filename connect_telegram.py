# connect_telegram.py
import asyncio
import os
from telethon import TelegramClient

# ===== MODIFIEZ CES 3 LIGNES =====
API_ID = 38955597  # METTEZ VOTRE API_ID ICI
API_HASH = "275fbac1b68e0984459d044b9b1a20cf"  # METTEZ VOTRE API_HASH ICI
PHONE = "+21699038382"  # VOTRE NUMERO

async def main():
    print("=" * 60)
    print("🔐 CONNEXION TELEGRAM")
    print("=" * 60)
    print("📞 Numéro: " + PHONE)
    print("=" * 60)
    print()
    print("📲 Un code de vérification va être envoyé")
    print("   (par SMS ou via Telegram)")
    print()
    
    os.makedirs("session", exist_ok=True)
    
    client = TelegramClient("session/telegram_render", API_ID, API_HASH)
    
    try:
        await client.start(phone=PHONE)
        
        me = await client.get_me()
        print()
        print("=" * 60)
        print("✅ CONNEXION RÉUSSIE !")
        print(f"👤 Nom: {me.first_name} (@{me.username})")
        print(f"📁 Session: session/telegram_render.session")
        print("=" * 60)
        print()
        print("📌 Cette session est sauvegardée.")
        print("   Le bot utilisera cette session à chaque démarrage.")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
        print("💡 Solutions:")
        print("   1. Vérifiez API_ID et API_HASH sur https://my.telegram.org/apps")
        print("   2. Vérifiez que votre numéro est correct")
        print("   3. Attendez 5 minutes avant de réessayer")
        
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
