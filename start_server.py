import subprocess
import sys

subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"], 
                 cwd=r"D:\Nikhil\ZoikOne\zoiko-one-backend")
print("Backend server started on port 8000")
