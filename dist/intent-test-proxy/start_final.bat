@echo off
chcp 65001 >nul
title Intent Test Framework - Local Proxy Server [FIXED VERSION]
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Intent Test Framework Local Proxy
echo   [FINAL FIXED VERSION - No Interruption]
echo ========================================
echo.

REM Step 1: Check Node.js
echo [1/5] Checking Node.js environment...
for /f "tokens=*" %%i in ('node --version 2^>nul') do set NODE_VERSION=%%i
if "!NODE_VERSION!"=="" (
    echo X Error: Node.js not detected
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo + Node.js version: !NODE_VERSION!

REM Step 2: Skip npm check (causes issues)
echo.
echo [2/5] npm check...
echo + npm: Will be tested during installation

REM Step 3: Dependencies
echo.
echo [3/5] Installing dependencies...

if exist "node_modules\@playwright\test" (
    if exist "node_modules\axios" (
        echo + Dependencies already exist, skipping installation
        goto step4_playwright
    )
)

echo ^ node_modules missing or incomplete
echo ^ Running npm install...
echo   Please wait, this may take several minutes...
echo.

npm install --no-audit --no-fund

if !errorlevel! neq 0 (
    echo.
    echo X npm install failed
    echo Try: 1^) Run as administrator 2^) npm cache clean --force
    pause
    exit /b 1
)

echo + npm install completed successfully!

:step4_playwright
REM Step 4: Playwright browsers
echo.
echo [4/5] Installing Playwright browsers...
echo ^ Installing Chromium browser...

npx playwright install chromium

if !errorlevel! neq 0 (
    echo ^ Warning: Playwright browser installation failed
    echo   You can install manually: npx playwright install chromium
    echo   Continuing anyway...
) else (
    echo + Playwright browsers ready
)

REM Step 5: Configuration and startup
echo.
echo [5/5] Configuration and server startup...

if not exist ".env" (
    echo ^ Creating configuration file...
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
    ) else (
        echo OPENAI_API_KEY=your-api-key-here > .env
        echo OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 >> .env
        echo MIDSCENE_MODEL_NAME=qwen-vl-max-latest >> .env
        echo PORT=3001 >> .env
    )
    echo + Configuration file created
    echo.
    echo ========================================
    echo   CONFIGURATION REQUIRED
    echo ========================================
    echo.
    echo Please edit .env file and set your API key
    echo Current placeholder: 'your-api-key-here'
    echo.
    start notepad .env 2>nul
    echo After editing, run this script again.
    pause
    exit /b 0
)

echo + Configuration file exists

REM Check API key
findstr /c:"your-api-key-here" .env >nul
if !errorlevel! equ 0 (
    echo X Please set your actual API key in .env file
    start notepad .env 2>nul
    pause
    exit /b 0
)

echo + API key configured

echo.
echo ========================================
echo   ALL STEPS COMPLETED - STARTING SERVER
echo ========================================
echo.
echo ^ Starting Intent Test Framework Local Proxy Server...
echo.
echo What to expect:
echo - Server will show startup messages
echo - Look for "Server listening on port 3001"
echo - Then go to Web interface and select "Local Proxy Mode"
echo.
echo Press Ctrl+C to stop the server
echo.

node midscene_server.js

set EXIT_CODE=!errorlevel!
echo.
echo ========================================
echo Server stopped ^(exit code: !EXIT_CODE!^)

if !EXIT_CODE! neq 0 (
    echo.
    echo Possible issues:
    echo 1. API key invalid or missing
    echo 2. Port 3001 already in use
    echo 3. Network connectivity issues
    echo 4. Missing dependencies
)

echo.
echo Script execution completed.
pause