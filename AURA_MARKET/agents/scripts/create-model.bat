@echo off
echo ════════════════════════════════════════
echo   AuraMarket — Creating custom model
echo ════════════════════════════════════════
echo.
cd /d "%~dp0\..\src\main\resources"
echo Working directory: %cd%
echo.
echo Creating auramarket-agent from Modelfile...
ollama create auramarket-agent -f Modelfile
echo.
echo ════════════════════════════════════════
echo   Verifying installation...
echo ════════════════════════════════════════
ollama list
echo.
echo Done!
pause
