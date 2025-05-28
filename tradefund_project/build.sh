#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Current directory: $(pwd)"
echo "Listing files: $(ls -la)"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Apply migrations
echo "Running migrations..."
python manage.py migrate

# Create default site - FIXED INDENTATION
echo "Setting up site configuration..."
python manage.py shell -c "from django.contrib.sites.models import Site; import os; domain = os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'fundmanage.onrender.com'); try: site = Site.objects.get(id=1); site.domain = domain; site.name = 'TradeFund'; site.save(); print('Site updated successfully: ' + domain); except Site.DoesNotExist: Site.objects.create(id=1, domain=domain, name='TradeFund'); print('Site created successfully: ' + domain); except Exception as e: print(f'Error handling site: {e}');"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Create cache table
echo "Creating cache table..."
python manage.py createcachetable
