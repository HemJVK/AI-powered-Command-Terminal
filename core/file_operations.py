import os
import shutil
from utils.error_handler import handle_error

def list_directory(path='.'):
    """Lists the contents of a directory."""
    try:
        return "\n".join(os.listdir(path))
    except FileNotFoundError:
        handle_error(f"Directory not found: {path}")
        return ""
    except Exception as e:
        handle_error(str(e))
        return ""

def change_directory(path):
    """Changes the current working directory."""
    try:
        os.chdir(path)
        return f"Directory changed to: {os.getcwd()}"
    except FileNotFoundError:
        handle_error(f"Directory not found: {path}")
        return ""
    except Exception as e:
        handle_error(str(e))
        return ""

def print_working_directory():
    """Returns the current working directory."""
    try:
        return os.getcwd()
    except Exception as e:
        handle_error(str(e))
        return ""

def make_directory(path):
    """Creates a new directory."""
    try:
        os.makedirs(path, exist_ok=True)
        return f"Directory created: {path}"
    except Exception as e:
        handle_error(str(e))
        return ""

def remove(path):
    """Removes a file or directory."""
    try:
        if os.path.isfile(path):
            os.remove(path)
            return f"File removed: {path}"
        elif os.path.isdir(path):
            shutil.rmtree(path)
            return f"Directory removed: {path}"
        else:
            handle_error(f"Path not found: {path}")
            return ""
    except Exception as e:
        handle_error(str(e))
        return ""