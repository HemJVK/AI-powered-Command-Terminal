import subprocess
from core.file_operations import (
    list_directory,
    change_directory,
    print_working_directory,
    make_directory,
    remove
)
from core.system_monitor import (
    get_cpu_usage,
    get_memory_usage,
    get_running_processes
)
from utils.error_handler import handle_error

def execute_shell_command(command):
    """Executes a shell command and returns the output."""
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        handle_error(e.stderr)
        return ""

def parse_and_execute(command):
    """Parses the command and executes the corresponding function."""
    parts = command.strip().split()
    cmd = parts[0]
    args = parts[1:]

    command_map = {
        'ls': lambda: list_directory(args[0] if args else '.'),
        'cd': lambda: change_directory(args[0]) if args else handle_error("Path required for cd command."),
        'pwd': print_working_directory,
        'mkdir': lambda: make_directory(args[0]) if args else handle_error("Directory name required for mkdir command."),
        'rm': lambda: remove(args[0]) if args else handle_error("File or directory name required for rm command."),
        'cpu': get_cpu_usage,
        'mem': get_memory_usage,
        'ps': get_running_processes,
        'exit': lambda: 'exit'
    }

    if cmd in command_map:
        return command_map[cmd]()
    else:
        return execute_shell_command(command)