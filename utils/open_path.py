import subprocess
import os

def open_path_in_explorer(path):
    if os.path.exists(path):
        subprocess.Popen(f'explorer "{path}"')
    else:
        print(f"Path does not exist: {path}")
