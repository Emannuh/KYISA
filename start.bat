@echo off
set PYTHONNOUSERSITE=1
call venv\Scripts\activate
python manage.py runserver
