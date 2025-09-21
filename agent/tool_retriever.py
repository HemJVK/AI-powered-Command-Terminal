import os
import shutil
import platform
import subprocess
import random  # <-- Import the random module
from functools import lru_cache
from typing import List, Set
from langchain_core.tools import Tool, BaseTool
from tqdm import tqdm

# --- Configuration ---
MAX_TOOLS_TO_CREATE = 2000  # <-- Set the desired limit here
DANGEROUS_COMMANDS = {
    "rm",
    "del",
    "erase",
    "format",
    "mkfs",
    "dd",
    "mv",
    "move",
    "rd",
    "rmdir",
    "remove-item",
    "clear-disk",
}
BASE_COMMANDS_TO_EXCLUDE = {
    "sudo",
    "su",
    "doas",
    "exit",
    "logout",
    "login",
    "passwd",
    "shutdown",
    "reboot",
    "kill",
    "pkill",
    "killall",
    "bg",
    "fg",
    "jobs",
    "alias",
    "unalias",
    "source",
    "export",
    "set",
    "unset",
    "history",
    "let",
    "eval",
    "exec",
    "sh",
    "bash",
    "zsh",
    "python",
    "pip",
    "conda",
    "docker",
    "git",
    "make",
}
# --- End Configuration ---

SUBPROCESS_FLAGS = 0
if platform.system() == "Windows":
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW


def human_in_the_loop_confirmation(command_name: str, args: str) -> bool:
    # ... (this function remains unchanged)
    print("\n" + "=" * 50)
    print("⚠️  WARNING: POTENTIALLY DESTRUCTIVE OPERATION DETECTED ⚠️")
    print(f"The agent wants to execute the following command: ")
    print(f"\n    {command_name} {args}\n")
    print("This could result in permanent data loss.")
    print("=" * 50)
    try:
        confirm = input("Do you want to proceed? (yes/no): ").lower().strip()
        return confirm == "yes"
    except EOFError:
        return False


def _execute_command(command_name: str, args: str) -> str:
    # ... (this function remains unchanged)
    command_name = command_name.lower().strip()

    if command_name == "sudo" or (args and args.strip().startswith("sudo")):
        return "Error: sudo access is strictly forbidden."

    if command_name in DANGEROUS_COMMANDS:
        if not human_in_the_loop_confirmation(command_name, args):
            return "Execution cancelled by user."

    try:
        full_command_list = [command_name] + args.split()
        print(f" L Executing: {' '.join(full_command_list)}")

        result = subprocess.run(
            full_command_list,
            capture_output=True,
            text=True,
            timeout=30,
            errors="ignore",
            creationflags=SUBPROCESS_FLAGS,
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output or "Command executed successfully with no output."
    except FileNotFoundError:
        return f"Error: Command '{command_name}' not found."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"An unexpected error occurred: {e}"


def get_command_help(command: str) -> str:
    # ... (this function remains unchanged)
    try:
        result = subprocess.run(
            [command, "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            errors="ignore",
            creationflags=SUBPROCESS_FLAGS,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout

        if platform.system() != "Windows":
            man_result = subprocess.run(
                ["man", command],
                capture_output=True,
                text=True,
                timeout=5,
                errors="ignore",
                creationflags=SUBPROCESS_FLAGS,
            )
            if man_result.returncode == 0 and man_result.stdout:
                return man_result.stdout

        if platform.system() == "Windows":
            help_result = subprocess.run(
                [command, "/?"],
                capture_output=True,
                text=True,
                timeout=5,
                errors="ignore",
                creationflags=SUBPROCESS_FLAGS,
            )
            if help_result.returncode == 0 and help_result.stdout:
                return help_result.stdout

        return "No help page found."
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "No help page found."


def discover_package_managers() -> Set[str]:
    # ... (this function remains unchanged)
    managers = set()
    system = platform.system()
    known_managers = {
        "Linux": ["apt", "yum", "dnf", "pacman", "zypper", "apt-get", "dpkg"],
        "Darwin": ["brew"],
        "Windows": ["choco", "winget", "scoop"],
    }
    if system in known_managers:
        for manager in known_managers[system]:
            if shutil.which(manager):
                managers.add(manager)
    return managers


def discover_executables_from_path() -> Set[str]:
    # ... (this function remains unchanged)
    executables = set()
    system_path = os.environ.get("PATH", "")
    if not system_path:
        print(
            "⚠️ WARNING: PATH environment variable is not set. No commands will be found."
        )
        return executables

    print(f"Scanning directories in PATH: {system_path}")
    for path_dir in system_path.split(os.pathsep):
        if not os.path.isdir(path_dir):
            continue

        try:
            for filename in os.listdir(path_dir):
                filepath = os.path.join(path_dir, filename)
                if os.access(filepath, os.X_OK) and not os.path.isdir(filepath):
                    command_name = os.path.splitext(filename)[0]
                    executables.add(command_name.lower())
        except OSError:
            continue

    return executables


@lru_cache(maxsize=1)
def load_system_command_tools() -> List[BaseTool]:
    """
    Discovers system commands from PATH, limits them to a max number,
    wraps them in a safe Tool, and returns the list.
    """
    print("--- Building Toolset from System PATH ---")
    all_cmds = discover_executables_from_path()
    pkg_managers = discover_package_managers()
    COMMANDS_TO_EXCLUDE = BASE_COMMANDS_TO_EXCLUDE.union(pkg_managers)

    valid_cmds = sorted(list(all_cmds - COMMANDS_TO_EXCLUDE))

    # --- ADDED LOGIC TO LIMIT THE NUMBER OF TOOLS ---
    if len(valid_cmds) > MAX_TOOLS_TO_CREATE:
        print(
            f"⚠️  Found {len(valid_cmds)} valid commands, which is more than the limit of {MAX_TOOLS_TO_CREATE}."
        )
        print(
            f"   Taking a random sample to ensure a diverse toolset and faster startup."
        )
        valid_cmds = random.sample(valid_cmds, MAX_TOOLS_TO_CREATE)
    # --- END OF ADDED LOGIC ---

    print(
        f"Found {len(all_cmds)} executables. After exclusions and sampling, creating tools for {len(valid_cmds)} commands."
    )

    tools = []
    for command in tqdm(valid_cmds, desc="Creating command tools"):
        help_text = get_command_help(command)
        if not help_text or "No help page found" in help_text:
            continue

        def create_lambda(cmd_name):
            return lambda args: _execute_command(command_name=cmd_name, args=args)

        tool = Tool(
            name=command,
            description=f"Executes the '{command}' command. Its help page is:\n---\n{help_text}",
            func=create_lambda(command),
        )
        tools.append(tool)

    print(f"✅ Created {len(tools)} dynamic tools from system commands found in PATH.")
    return tools
