@echo off
setlocal EnableDelayedExpansion

echo ====================================
echo Blender Addon Updater
echo ====================================

:: Check for required files
if not exist "config.yml" (
    echo ERROR: config.yml not found!
    pause
    exit /b 1
)

if not exist "addon_update.py" (
    echo ERROR: addon_update.py not found!
    pause
    exit /b 1
)

:: Load configuration from config.yml
for /f "tokens=1* delims=: " %%a in ('findstr /r "^[a-zA-Z_][a-zA-Z0-9_]*:" config.yml') do (
    set "key=%%a"
    set "value=%%b"
    :: Remove quotes
    set "value=!value:"=!"

    if "!key!"=="blender_executable" set "BLENDER_EXE=!value!"
    if "!key!"=="blend_file" set "BLEND_FILE=!value!"
    if "!key!"=="addon_folder" set "ADDON_FOLDER=!value!"
    if "!key!"=="output_zip" set "OUTPUT_ZIP=!value!"
    if "!key!"=="addon_name" set "ADDON_NAME=!value!"
    if "!key!"=="verbose" set "VERBOSE=!value!"
)

:: Validate
if not defined BLENDER_EXE (
    echo ERROR: blender_executable not found in config.yml
    pause
    exit /b 1
)
if not defined BLEND_FILE (
    echo ERROR: blend_file not found in config.yml
    pause
    exit /b 1
)
if not defined ADDON_FOLDER (
    echo ERROR: addon_folder not found in config.yml
    pause
    exit /b 1
)
if not defined ADDON_NAME (
    echo ERROR: addon_name not found in config.yml
    pause
    exit /b 1
)

if not defined OUTPUT_ZIP set "OUTPUT_ZIP=%ADDON_FOLDER%.zip"

:: Show configuration if verbose
if "%VERBOSE%"=="true" (
    echo Configuration loaded:
    echo - Blender: !BLENDER_EXE!
    echo - Blend file: !BLEND_FILE!
    echo - Addon folder: !ADDON_FOLDER!
    echo - Output zip: !OUTPUT_ZIP!
    echo - Addon name: !ADDON_NAME!
    echo.
)

:: Validate paths exist
if not exist "!BLENDER_EXE!" (
    echo ERROR: Blender executable not found: !BLENDER_EXE!
    pause
    exit /b 1
)

if not exist "!ADDON_FOLDER!" (
    echo ERROR: Addon folder not found: !ADDON_FOLDER!
    pause
    exit /b 1
)

if not exist "!BLEND_FILE!" (
    echo ERROR: Blend file not found: !BLEND_FILE!
    pause
    exit /b 1
)

:: Create zip file
echo [1/3] Creating zip file from addon folder...
if exist "!OUTPUT_ZIP!" del "!OUTPUT_ZIP!"

powershell -command "Compress-Archive -Path '!ADDON_FOLDER!' -DestinationPath '!OUTPUT_ZIP!'"

if not exist "!OUTPUT_ZIP!" (
    echo ERROR: Failed to create zip file
    pause
    exit /b 1
)
echo Successfully created: !OUTPUT_ZIP!

:: Run Blender with Python script
echo [2/3] Running Blender addon update script...

if "%VERBOSE%"=="true" (
    echo Running: "!BLENDER_EXE!" "!BLEND_FILE!" --background --python "addon_update.py"
)

"!BLENDER_EXE!" "!BLEND_FILE!" --background --python "addon_update.py"

if !ERRORLEVEL! neq 0 (
    echo ERROR: Blender script execution failed with error code !ERRORLEVEL!
    echo Check the console output above for details
    pause
    exit /b 1
)

echo Addon update script completed successfully!

:: Restart Blender
echo [3/3] Restarting Blender...
start "" "!BLENDER_EXE!" "!BLEND_FILE!"

echo.
echo ====================================
echo Update Successful!
echo ====================================
echo - Addon folder zipped: !OUTPUT_ZIP!
echo - Addon reinstalled: !ADDON_NAME!
echo - Blender restarted with: !BLEND_FILE!
echo.

if "%VERBOSE%"=="true" (
    echo Press any key to exit...
    pause >nul
) else (
    pause
)