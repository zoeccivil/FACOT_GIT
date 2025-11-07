@echo off
setlocal

set APP_NAME=FACOT

REM Compila usando el .spec y saca dist/build fuera de Dropbox
py -m PyInstaller facot.spec --clean --noconfirm ^
  --distpath C:\_facot\dist ^
  --workpath C:\_facot\build

echo.
echo EXE en: C:\_facot\dist\%APP_NAME%\%APP_NAME%.exe
endlocal