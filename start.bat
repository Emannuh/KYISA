@echo off
echo ============================================
echo   KYISA Development Server
echo ============================================
echo.

:: Activate Python venv
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate
)

:: Start Django dev server
echo Starting Django on http://127.0.0.1:8000 ...
python manage.py runserver 8000
