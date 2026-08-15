@echo off
title LongTerm AI Bot
echo ========================================
echo     LongTerm AI Bot - Lancement
echo ========================================
echo.

REM Activer l'environnement virtuel
call venv\Scripts\activate

REM Lancer le bot
echo 🚀 Lancement du bot...
echo 📊 Interface: http://localhost:8000
echo 📡 API: http://localhost:8000/api/status
echo.
echo 🔴 Appuyez sur Ctrl+C pour arrêter
echo.

python -m app.main
pause