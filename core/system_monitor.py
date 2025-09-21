import psutil
from utils.error_handler import handle_error

def get_cpu_usage():
    """Returns the current CPU usage."""
    try:
        return f"CPU Usage: {psutil.cpu_percent(interval=1)}%"
    except Exception as e:
        handle_error(str(e))
        return ""

def get_memory_usage():
    """Returns the current memory usage."""
    try:
        memory = psutil.virtual_memory()
        return f"Memory Usage: {memory.percent}%"
    except Exception as e:
        handle_error(str(e))
        return ""

def get_running_processes():
    """Returns a list of running processes."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            processes.append(f"PID: {proc.info['pid']}, Name: {proc.info['name']}")
        return "\n".join(processes)
    except Exception as e:
        handle_error(str(e))
        return ""