web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn kyisa_cms.wsgi --bind 0.0.0.0:$PORT --workers 2
