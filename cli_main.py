# cli_main.py
import sys
import os

# Add the project root to the Python path to allow for absolute imports
# This is crucial for running the script from the root directory.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from presentation.main import run

if __name__ == "__main__":
    # The 'if __name__ == "__main__"' block is a standard Python construct
    # that allows the script to be run directly.
    run()
