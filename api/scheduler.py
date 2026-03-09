# api/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from .services import IoTService  # Adjust the import based on your folder structure

def start_watchdog():
    scheduler = BackgroundScheduler()
    
    # Run the check_node_connectivity function every 1 minute
    scheduler.add_job(IoTService.check_node_connectivity, 'interval', minutes=1)
    
    scheduler.start()