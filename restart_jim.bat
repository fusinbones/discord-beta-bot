@echo off
echo Restarting Jim with new superpowers...
echo.

REM Kill any existing Python processes running the bot
taskkill /f /im python.exe 2>nul
timeout /t 2 /nobreak >nul

echo Starting Jim (Beta Testing Assistant)...
echo.
echo Jim will:
echo - Greet the beta channel and announce his capabilities
echo - Automatically scan recent chat history
echo - Announce scanning progress to the channel
echo - Be ready to assist with beta testing coordination
echo.

python bot.py

pause
