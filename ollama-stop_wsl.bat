@echo off
title Ollama Stopper

echo Stopping Ollama...

taskkill /f /im ollama.exe >nul 2>&1

echo Done.
pause