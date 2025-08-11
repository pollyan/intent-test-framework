@echo off
chcp 65001 >nul
title Intent Test Framework - Local Proxy Server
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Intent Test Framework Local Proxy
echo ========================================
echo.

REM Check Node.js
echo [1/5] Checking Node.js environment...
node --version >node_check.tmp 2>&1
if !errorlevel! neq 0 (
    echo X Error: Node.js not detected
    echo.
    echo Please install Node.js first:
    echo https://nodejs.org/
    echo.
    echo Recommend LTS version ^(16.x or higher^)
    if exist node_check.tmp del node_check.tmp
    pause
    exit /b 1
)

set NODE_VERSION=Unknown
if exist node_check.tmp (
    for /f "tokens=*" %%i in (node_check.tmp) do set NODE_VERSION=%%i
    del node_check.tmp
)
echo + Node.js version: !NODE_VERSION!

REM Check npm - skip version check if problematic
echo.
echo [2/5] Checking npm...
echo ^ Skipping npm version check to avoid script termination
echo + npm: Will be verified during dependency installation

REM Check and install dependencies
echo.
echo [3/5] Checking dependencies...

REM Check key dependencies
set NEED_INSTALL=false

if not exist "node_modules" (
    set NEED_INSTALL=true
    echo ^ node_modules folder not found
)
if not exist "node_modules\@playwright\test" (
    set NEED_INSTALL=true
    echo ^ @playwright/test missing
)
if not exist "node_modules\axios" (
    set NEED_INSTALL=true
    echo ^ axios missing
)

if "!NEED_INSTALL!"=="false" (
    echo + Dependencies already exist
    goto check_playwright
)

:install_deps
echo.
echo ^ Installing dependencies...
echo This may take several minutes, please wait...
echo.

REM Clean old dependencies if they exist
if exist "node_modules" (
    echo ^ Cleaning old dependencies...
    rmdir /s /q "node_modules" 2>nul
)
if exist "package-lock.json" (
    del "package-lock.json" 2>nul
)

REM Install dependencies - simplified approach
echo ^ Running npm install...
echo   This may take several minutes, please be patient...
echo   You will see package installation messages below:
echo.

npm install --no-audit --no-fund

if !errorlevel! neq 0 (
    echo.
    echo X npm install failed ^(exit code: !errorlevel!^)
    echo.
    echo Common solutions:
    echo 1. Network issues: npm config set registry https://registry.npmmirror.com
    echo 2. Permission issues: Run as administrator
    echo 3. Clear cache: npm cache clean --force
    echo 4. Manual install: npm install @playwright/test axios express socket.io
    echo.
    pause
    exit /b 1
)

echo.
echo + npm install completed successfully!

REM Verify key dependencies
if not exist "node_modules\@playwright\test" (
    echo X @playwright/test dependency missing after installation
    echo.
    if exist npm_install.log (
        echo Installation log:
        type npm_install.log
        del npm_install.log
    )
    pause
    exit /b 1
)

if not exist "node_modules\axios" (
    echo X axios dependency missing after installation
    pause
    exit /b 1
)

if exist npm_install.log del npm_install.log
echo + Dependencies installation completed

:check_playwright
echo.
echo [4/5] Installing Playwright browsers...
echo ^ Installing Chromium browser for web automation...
echo   This step may take 2-5 minutes...
echo.

npx playwright install chromium
if !errorlevel! neq 0 (
    echo.
    echo ^ Warning: Playwright browser installation had issues
    echo   This might cause "Executable doesn't exist" errors during testing
    echo   You can manually install later with: npx playwright install chromium
    echo   Continuing with server startup...
) else (
    echo + Playwright browsers installed successfully
)

:check_config
echo.
echo [5/5] Configuration setup...

if not exist ".env" (
    echo ^ Creating configuration file...
    
    if exist ".env.example" (
        copy ".env.example" ".env" >nul 2>&1
        if !errorlevel! equ 0 (
            echo + Configuration created from template
        ) else (
            goto create_basic_env
        )
    ) else (
        :create_basic_env
        echo # Intent Test Framework - Local Proxy Server > .env
        echo. >> .env
        echo # AI API Configuration ^(REQUIRED^) >> .env
        echo OPENAI_API_KEY=your-api-key-here >> .env
        echo OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 >> .env
        echo MIDSCENE_MODEL_NAME=qwen-vl-max-latest >> .env
        echo. >> .env
        echo # Server Configuration >> .env
        echo PORT=3001 >> .env
        echo + Basic configuration created
    )
    
    echo.
    echo ========================================
    echo   CONFIGURATION REQUIRED
    echo ========================================
    echo.
    echo Please edit the .env file and replace 'your-api-key-here'
    echo with your actual AI API key, then run this script again.
    echo.
    
    start notepad .env 2>nul
    pause
    exit /b 0
)

echo + Configuration file exists

REM Check if API key is configured
findstr /c:"your-api-key-here" .env >nul
if !errorlevel! equ 0 (
    echo.
    echo X Please edit .env file and set your actual API key
    echo   Current placeholder: 'your-api-key-here'
    echo.
    start notepad .env 2>nul
    pause
    exit /b 0
)

echo + API key appears to be configured

REM Start server
echo.
echo ========================================
echo   STARTING SERVER
echo ========================================
echo.
echo + Starting Intent Test Framework Local Proxy Server...
echo.

node midscene_server.js

set SERVER_CODE=!errorlevel!
echo.
echo ========================================
echo Server stopped with exit code: !SERVER_CODE!

if !SERVER_CODE! neq 0 (
    echo.
    echo Common solutions:
    echo 1. Check API key in .env file
    echo 2. Ensure port 3001 is available
    echo 3. Check internet connection
    echo 4. Try running as administrator
)

echo.
pause