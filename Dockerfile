
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_demo && if [ \"$DJANGO_ADMIN_RECOVERY_ENABLED\" = \"true\" ]; then python manage.py recover_admin || exit 1; fi && python manage.py runserver 0.0.0.0:8000"]
