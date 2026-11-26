@echo off
setlocal EnableDelayedExpansion
rem Prism project guide: open the key files, then the explainer in the browser.
rem
rem Usage (from the repository root, in cmd):
rem   guide\open_all.bat
rem   guide\open_all.bat /nobrowser
rem   guide\open_all.bat /nocode
rem
rem If VS Code ("code") is on PATH, the repo folder and all files open together
rem as tabs, so the links in guide\rishith.md work. Otherwise each file opens in
rem its default application. guide\index.html opens in the default browser unless
rem /nobrowser is given. Missing files are skipped and reported.

set "NOBROWSER=0"
set "NOCODE=0"
for %%A in (%*) do (
    if /i "%%~A"=="/nobrowser" set "NOBROWSER=1"
    if /i "%%~A"=="/nocode" set "NOCODE=1"
)

rem Repository root = parent of this script's folder.
pushd "%~dp0.."
set "ROOT=%CD%"

set "FILES="
set "COUNT=0"
set "MISSING="
set "MISSCOUNT=0"

for %%F in (
    guide\rishith.md
    guide\flowchart.md
    guide\README.md
    README.md
    DESIGN.md
    docs\SDLC.md
    backend\finreq\pipeline.py
    backend\finreq\llm.py
    backend\finreq\models.py
    backend\finreq\config.py
    backend\finreq\masking.py
    backend\finreq\retrieval.py
    backend\finreq\storage.py
    backend\finreq\sdlc.py
    backend\finreq\artifacts.py
) do call :add "%%F"

rem Every agent module except the package marker.
if exist "backend\finreq\agents\" (
    for %%F in (backend\finreq\agents\*.py) do (
        if /i not "%%~nxF"=="__init__.py" call :add "backend\finreq\agents\%%~nxF"
    )
)

for %%F in (
    backend\server.py
    backend\cli.py
    backend\scripts\gates.py
    backend\eval\evaluate.py
    frontend\src\App.tsx
    frontend\src\lib\api.ts
    frontend\src\index.css
    frontend\src\components\RunView.tsx
    frontend\src\components\InputPanel.tsx
    frontend\src\components\review\ReviewStep.tsx
    frontend\src\components\DeliveryStep.tsx
    frontend\src\components\ExportStep.tsx
) do call :add "%%F"

set "OPENED=0"
set "MODE=default applications"
where code >nul 2>nul
if "%NOCODE%"=="0" if not errorlevel 1 (
    set "MODE=VS Code"
    call code "%ROOT%" !FILES!
    set "OPENED=!COUNT!"
) else (
    call :open_default
)
if "%NOCODE%"=="1" call :open_default

if "%NOBROWSER%"=="0" (
    if exist "guide\index.html" (
        start "" "%ROOT%\guide\index.html"
        set /a OPENED+=1
    ) else (
        set /a MISSCOUNT+=1
        set "MISSING=!MISSING! guide\index.html"
    )
)

echo.
echo Prism project guide
echo   Opened !OPENED! item(s) via !MODE!
if !MISSCOUNT! gtr 0 (
    echo   Skipped !MISSCOUNT! missing file^(s^):
    for %%M in (!MISSING!) do echo     %%M
)
echo.
popd
endlocal
exit /b 0

:add
if exist "%~1" (
    set "FILES=!FILES! "%ROOT%\%~1""
    set /a COUNT+=1
) else (
    set /a MISSCOUNT+=1
    set "MISSING=!MISSING! %~1"
)
exit /b

:open_default
for %%F in (!FILES!) do (
    start "" %%F
    set /a OPENED+=1
)
exit /b
