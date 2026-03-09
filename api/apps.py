from django.apps import AppConfig
import os

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api' # Make sure this matches your app name

    def ready(self):
        # This prevents the scheduler from running twice when Django's auto-reloader is active
        if os.environ.get('RUN_MAIN') == 'true':
            from .scheduler import start_watchdog
            start_watchdog()
            print("🟢 IoT Star Topology Watchdog Started!")
