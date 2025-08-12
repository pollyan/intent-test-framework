@echo off
chcp 65001 >nul
title Intent Test Framework - Local Proxy Server [FINAL]
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Intent Test Framework Local Proxy
echo   [FINAL VERSION - Complete Setup]
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

REM Step 2: Skip npm version check
echo.
echo [2/5] npm check...
echo + npm: Will be verified during dependency installation

REM Step 3: Install dependencies
echo.
echo [3/5] Installing dependencies...

if exist "node_modules\@playwright\test" (
    if exist "node_modules\axios" (
        echo + Dependencies already exist, skipping installation
    ) else (
        echo ^ Installing npm dependencies...
        echo   This may take several minutes, please wait...
        echo   Note: Warnings are normal and will not stop installation
        echo.
        call npm install --no-audit --no-fund --silent
        set NPM_CODE=!errorlevel!
        if !NPM_CODE! neq 0 (
            echo.
            echo X npm install failed ^(exit code: !NPM_CODE!^)
            echo Try running as administrator or check network connection
            pause
            exit /b 1
        )
        echo + npm dependencies installed successfully!
    )
) else (
    echo ^ Installing npm dependencies...
    echo   This may take several minutes, please wait...
    echo   Note: Warnings are normal and will not stop installation
    echo.
    call npm install --no-audit --no-fund --silent
    set NPM_CODE=!errorlevel!
    if !NPM_CODE! neq 0 (
        echo.
        echo X npm install failed ^(exit code: !NPM_CODE!^)
        echo Try running as administrator or check network connection
        pause
        exit /b 1
    )
    echo + npm dependencies installed successfully!
)

REM Step 4: Install Playwright browsers
echo.
echo [4/5] Installing Playwright browsers...
echo ^ Installing Chromium browser for web automation
echo   This step may take 2-10 minutes depending on your network
echo   Please be patient, download progress will be shown
echo.

REM Try installation with different approaches
set PLAYWRIGHT_SUCCESS=false

REM Method 1: Standard installation
echo + Attempting standard installation...
call npx playwright install chromium --with-deps 2>nul
if !errorlevel! equ 0 (
    set PLAYWRIGHT_SUCCESS=true
    echo + Playwright browsers installed successfully!
) else (
    echo ^ Standard installation failed, trying alternative method...
    
    REM Method 2: Without deps
    call npx playwright install chromium 2>nul  
    if !errorlevel! equ 0 (
        set PLAYWRIGHT_SUCCESS=true
        echo + Playwright browsers installed successfully ^(without system deps^)!
    ) else (
        echo ^ Alternative method failed, trying forced installation...
        
        REM Method 3: Force installation with timeout
        timeout /t 2 /nobreak >nul
        call npx playwright install --force chromium 2>nul
        if !errorlevel! equ 0 (
            set PLAYWRIGHT_SUCCESS=true
            echo + Playwright browsers force-installed successfully!
        ) else (
            REM If all methods fail, continue but warn user
            echo.
            echo ^ Warning: Playwright browser installation encountered issues
            echo   This might be due to network connectivity or firewall settings
            echo   The server will start, but browser will download during first test
            echo   You can manually install later with: npx playwright install chromium
            echo.
            echo + Continuing with server startup...
        )
    )
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
    echo Please edit .env file and replace 'your-api-key-here'
    echo with your actual AI API key, then run this script again.
    echo.
    start notepad .env 2>nul
    echo Press any key after editing the .env file...
    pause
    exit /b 0
)

echo + Configuration file exists

REM Check API key configuration
findstr /c:"your-api-key-here" .env >nul
if !errorlevel! equ 0 (
    echo.
    echo X Please edit .env file and set your actual API key
    echo   Current value is still the placeholder
    echo.
    start notepad .env 2>nul
    echo Press any key after setting your API key...
    pause
    exit /b 0
)

echo + API key appears to be configured

echo.
echo ========================================
echo   ALL SETUP COMPLETED - STARTING SERVER
echo ========================================
echo.
echo + Starting Intent Test Framework Local Proxy Server...
echo.
echo Expected startup sequence:
echo   1. Environment variables loading
echo   2. Express server initialization
echo   3. WebSocket server startup
echo   4. "Server listening on port 3001" message
echo.
echo After successful startup:
echo   - Go to the web interface
echo   - Select "Local Proxy Mode"
echo   - Start creating and running tests
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Start the server
node midscene_server.js

REM Server stopped
set SERVER_EXIT_CODE=!errorlevel!
echo.
echo ========================================
echo Server stopped ^(exit code: !SERVER_EXIT_CODE!^)

if !SERVER_EXIT_CODE! neq 0 (
    echo.
    echo Troubleshooting guide:
    echo 1. API key issues: Check .env file configuration
    echo 2. Port conflict: Port 3001 may be in use by another application  
    echo 3. Network issues: Check internet connection for AI API calls
    echo 4. Dependency issues: Try deleting node_modules and running again
    echo 5. Permission issues: Try running as administrator
    echo.
)

echo.
echo Script execution completed. Press any key to exit.
pause
exit /b !SERVER_EXIT_CODE!
