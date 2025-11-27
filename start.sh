#!/bin/bash
set -e

echo "Starting deployment process..."

# Disable test environment variables for production
unset TEST_DATABASE_ENGINE
unset TEST_DATABASE_NAME

# Create directories for static and media files
if [ -n "$VOLUME_PATH" ]; then
    echo "Using Railway volume at $VOLUME_PATH"
    mkdir -p "$VOLUME_PATH/static" "$VOLUME_PATH/media"
    export STATIC_ROOT="$VOLUME_PATH/static"
    export MEDIA_ROOT="$VOLUME_PATH/media"
else
    echo "Using local directories"
    mkdir -p /app/staticfiles /app/media
    export STATIC_ROOT="/app/staticfiles"
    export MEDIA_ROOT="/app/media"
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Configure SITE_ID and domain
echo "Configuring Django site domain..."
python manage.py shell << EOF
from django.contrib.sites.models import Site
import os

domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")
name = "Barbershop API"

site, created = Site.objects.get_or_create(id=1)
site.domain = domain
site.name = name
site.save()
EOF

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn server
echo "Starting Gunicorn..."
exec gunicorn project.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
