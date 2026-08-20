# auth_telegram.py
from telethon import TelegramClient
import asyncio
import os

# ===== VOS IDENTIFIANTS =====
API_ID = "38955597"        # Remplacez
API_HASH = "275fbac1b68e0984459d044b9b1a20cf" # Remplacez
PHONE = "+21699038382"      # Remplacez

async def main():
    os.makedirs("session", exist_ok=True)
    client = TelegramClient("session/telegram", API_ID, API_HASH)
    
    print("📱 Connexion à Telegram...")
    print("📲 Un code vous sera envoyé par SMS ou Telegram")
    
    await client.start(phone=PHONE)
    
    me = await client.get_me()
    print(f"✅ Connecté en tant que: {me.first_name} (@{me.username})")
    
    await client.disconnect()
    print("✅ Session sauvegardée dans session/telegram.session")

if __name__ == "__main__":
    asyncio.run(main())
