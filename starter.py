# starts the server and opens the browser, handy for a desktop shortcut
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

here = Path(__file__).resolve().parent
process = subprocess.Popen([sys.executable, str(here / "app.py")], cwd=here)

time.sleep(2)
webbrowser.open("http://127.0.0.1:3000")

try:
    process.wait()
except KeyboardInterrupt:
    process.terminate()
    process.wait()
