#!/usr/bin/env bash
# Exit on error
set -o errexit

# Check if we're starting for the first time or restarting
if [ ! -f "/tmp/app_initialized" ]; then
    echo "First start - running full initialization..."
    
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
    
    # Create flag file to indicate initialization is done
    touch /tmp/app_initialized
    
    echo "Initialization complete."
else
    echo "Restarting - skipping initialization steps..."
    
    # On restarts, we only need to ensure migrations are up to date
    python manage.py migrate --noinput
fi

# After initialization or restart, start the server
exec gunicorn tradefund_project.wsgi:application
