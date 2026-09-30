import os
import shutil
import sys

port = sys.argv[1]
pid_file_path = sys.argv[2]

os.setsid()

with open(pid_file_path, "w", encoding="utf-8") as pid_file:
    pid_file.write(f"{os.getpid()}\n")

uv_path = shutil.which("uv")
if uv_path is None:
    raise SystemExit("uv is required to run the Packman development server.")

os.execv(
    uv_path,
    [uv_path, "run", "python", "manage.py", "runserver", f"127.0.0.1:{port}"],  # nosec B606
)
