@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

set "LOG_DIR=%REPO_ROOT%\results\connector-logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%I"
set "LOG_FILE=%LOG_DIR%\provider_%TS%.log"

cd /d "%REPO_ROOT%"
echo [INFO] Provider log: "%LOG_FILE%"
start "" cmd /c "java -Dedc.fs.config=transfer/transfer-00-prerequisites/resources/configuration/provider-configuration.properties -jar transfer/transfer-00-prerequisites/connector/build/libs/connector.jar >> ""%LOG_FILE%"" 2>&1"

endlocal
