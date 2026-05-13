@echo off
title Ollama (WSL Bridge Mode)
set OLLAMA_HOST=0.0.0.0
echo Starting Ollama on 0.0.0.0 (Visible to WSL)...
:: Runs in a separate window so the user can see the logs if it fails
start "Ollama Server" cmd /c "ollama serve"
echo.
echo ✅ Server launch command sent. 
echo If a new window opened and stayed open, you're good to go.
pause