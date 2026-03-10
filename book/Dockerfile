FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir django djangorestframework requests

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --run-syncdb ; python manage.py runserver 0.0.0.0:8000"]
