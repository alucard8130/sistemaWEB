FROM python:3.13-slim

# Evita prompts interactivos de apt y mejora logs de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Librerías de sistema necesarias para WeasyPrint (Pango, Cairo, GDK-PixBuf, etc.)
# más las necesarias para psycopg2 y compilación general.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

# Railway inyecta la variable $PORT en tiempo de ejecución.
# Las migraciones corren al iniciar el contenedor (no en el build),
# para asegurar que la base de datos ya esté disponible.
CMD python manage.py migrate --noinput && gunicorn core.wsgi --bind 0.0.0.0:$PORT --log-file -
