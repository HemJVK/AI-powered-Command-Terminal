import sys

def handle_error(error_message):
    """Prints an error message to stderr."""
    print(f"Error: {error_message}", file=sys.stderr)