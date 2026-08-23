# connect_telegram.py
import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError

# ============================================
# CONFIGURATION - MODIFIEZ CES VALEURS !
# ============================================
API_ID = 38955597  # METTEZ VOTRE API_ID ICI (ex: 1234567)
API_HASH = "275fbac1b68e0984459d044b9b1a20cf"  # METTEZ VOTRE API_HASH ICI
PHONE = "+21699038382"  # VOTRE NUMERO DE TELEPHONE

# ============================================
# SCRIPT DE CONNEXION
# ============================================

async def main():
    print("=" * 60)
    print("🔐 CONNEXION TELEGRAM")
    print("=" * 60)
    
    # Vérifier la version de Telethon
    try:
        import telethon
        print(f"📱 Telethon version: {telethon.__version__}")
    except:
        print("❌ Telethon non installé")
        print("   Installez-le avec: pip install telethon==1.28.5")
        return
    
    print(f"📞 Numéro: {PHONE}")
    print("=" * 60)
    
    # Créer le dossier session
    os.makedirs("session", exist_ok=True)
    
    # Supprimer l'ancienne session si elle existe
    session_file = "session/telegram_render.session"
    if os.path.exists(session_file):
        os.remove(session_file)
        print("🗑️ Ancienne session supprimée")
    
    # Créer le client
    client = TelegramClient("session/telegram_render", API_ID, API_HASH)
    
    try:
        print("🔄 Connexion à Telegram...")
        
        # Se connecter
        await client.connect()
        
        # Vérifier si déjà autorisé
        if not await client.is_user_authorized():
            print("📲 Envoi du code de vérification...")
            
            try:
                # Envoyer la demande de code
                await client.send_code_request(PHONE)
                print("✅ Code envoyé !")
                print()
                
                # Demander le code
                code = input("🔑 Entrez le code reçu par SMS/Telegram: ")
                
                # Tenter la connexion avec le code
                try:
                    await client.sign_in(PHONE, code)
                except PhoneCodeInvalidError:
                    print("❌ Code invalide. Réessayez.")
                    return
                except PhoneCodeExpiredError:
                    print("❌ Code expiré. Réessayez.")
                    return
                except SessionPasswordNeededError:
                    # Si 2FA est activé
                    password = input("🔐 Entrez votre mot de passe 2FA: ")
                    await client.sign_in(password=password)
                    
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi du code: {e}")
                return
        
        # Récupérer les informations
        me = await client.get_me()
        
        print()
        print("=" * 60)
        print("✅ CONNEXION RÉUSSIE !")
        print("=" * 60)
        print(f"👤 Nom: {me.first_name} {me.last_name or ''}")
        print(f"📱 Username: @{me.username}" if me.username else "📱 Username: Non défini")
        print(f"🆔 ID: {me.id}")
        print(f"📁 Session: {session_file}")
        print("=" * 60)
        print()
        print("📌 PROCHAINES ÉTAPES:")
        print("   1. Ajoutez le fichier de session à Git:")
        print("      git add session/telegram_render.session")
        print("   2. Committez et poussez:")
        print("      git commit -m 'Ajout session Telegram'")
        print("      git push origin main")
        print()
        print("✅ Le bot utilisera cette session pour se connecter automatiquement !")
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERREUR DE CONNEXION")
        print("=" * 60)
        print(f"Erreur: {e}")
        print()
        print("💡 SOLUTIONS:")
        print("   1. Vérifiez API_ID et API_HASH sur https://my.telegram.org/apps")
        print("   2. Vérifiez que votre numéro est correct: " + PHONE)
        print("   3. Installez la bonne version: pip install telethon==1.28.5")
        print("   4. Attendez 5 minutes avant de réessayer")
        print("=" * 60)
        
    finally:
        await client.disconnect()
        print()
        print("🔌 Déconnecté")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
