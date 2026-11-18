@echo off
REM Build ApexSteelSearch.exe on your own laptop (GitHub Actions does the same automatically)
cd /d "%~dp0"
if not exist .venv (
  py -3.11 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
pytest -q || goto :error
pyinstaller --noconfirm packaging\ApexSteelSearch.spec || goto :error
echo.
echo Done: dist\ApexSteelSearch\ApexSteelSearch.exe
pause
exit /b 0
:error
echo Build failed.
pause
exit /b 1
