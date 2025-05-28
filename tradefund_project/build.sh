#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

# Install Poetry dependencies
pip install poetry
poetry config virtualenvs.create false
poetry install --no-interaction --no-ansi

# Apply migrations
python manage.py migrate

# Create default site
python manage.py shell -c "
from django.contrib.sites.models import Site
try:
    site = Site.objects.get(id=1)
    site.domain = '${RENDER_EXTERNAL_HOSTNAME:-fundmanage.onrender.com}'
    site.name = 'TradeFund'
    site.save()
    print('Site updated successfully')
except Site.DoesNotExist:
    Site.objects.create(id=1, domain='${RENDER_EXTERNAL_HOSTNAME:-fundmanage.onrender.com}', name='TradeFund')
    print('Site created successfully')
except Exception as e:
    print(f'Error handling site: {e}')
"

# Collect static files
python manage.py collectstatic --no-input

# Create cache table
python manage.py createcachetable

# Set up Tailwind CSS if using it
if command -v npm &>/dev/null; then
    npm install
    npm run build:css
fi
