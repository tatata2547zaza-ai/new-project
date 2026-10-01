import subprocess
import sys
import threading
import time
import os
import signal

# Paths to python inside the virtual environment
VENV_BIN = os.path.join("rasa_env", "Scripts")
PYTHON_EXE = os.path.join(VENV_BIN, "python.exe")

# Verify python executable exists
if not os.path.exists(PYTHON_EXE):
    print("Error: Could not find virtual environment python at rasa_env\\Scripts\\python.exe")
    print("Please make sure you run this script from the project root directory where 'rasa_env' is located.")
    sys.exit(1)

# Store running processes as { name: (proc_object, is_optional) }
processes = {}

def log_output(process_name, stream, prefix_color):
    """Reads lines from a stream and prints them with a prefix."""
    # Simple ANSI color codes
    RESET = "\033[0m"
    for line in iter(stream.readline, b""):
        decoded = line.decode("utf-8", errors="replace").strip()
        if decoded:
            print(f"{prefix_color}[{process_name}]{RESET} {decoded}", flush=True)

def run_process(name, cmd, color, optional=False):
    print(f"Starting {name}...")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False
        )
        processes[name] = (proc, optional)
        
        # Start thread to log output
        t = threading.Thread(target=log_output, args=(name, proc.stdout, color), daemon=True)
        t.start()
        return proc
    except Exception as e:
        print(f"\033[31mFailed to start {name}: {e}\033[0m")
        if optional:
            print(f"Warning: {name} is optional, continuing without it...")
            if name == "Ngrok Tunnel":
                print("Tip: Make sure 'ngrok' is installed and added to your system PATH.")
            return None
        else:
            cleanup()

def cleanup(sig=None, frame=None):
    print("\nShutting down all services...")
    for name, (proc, optional) in list(processes.items()):
        if proc.poll() is None:
            try:
                # Use taskkill on Windows to terminate the process tree cleanly
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
    print("Cleanup finished.")
    sys.exit(0)

# Register cleanup for signals
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# Define commands to run: { name: (cmd_list, color_code, is_optional) }
commands = {
    "Rasa Action Server": ([PYTHON_EXE, "-u", "-m", "rasa", "run", "actions"], "\033[36m", False),  # Cyan
    "Rasa Core Server": ([PYTHON_EXE, "-u", "-m", "rasa", "run", "--enable-api", "--cors", "*"], "\033[32m", False), # Green
    "Webhook Server": ([PYTHON_EXE, "-u", "webhook.py"], "\033[35m", False),       # Magenta
    "Ngrok Tunnel": (["ngrok", "http", "8000"], "\033[33m", True)           # Yellow
}

if __name__ == "__main__":
    # Enable ANSI escape sequences on Windows command prompt for colors
    if os.name == 'nt':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    print("=== Starting Rasa chatbot application services ===")
    print("Press Ctrl+C to stop all services simultaneously.\n")
    
    # Start each service
    for name, (cmd, color, optional) in commands.items():
        run_process(name, cmd, color, optional)
        # Give a small delay so they don't print over each other too much during startup
        time.sleep(2)
        
    # Keep the main thread alive and monitor processes
    try:
        while True:
            # Check if any process has exited unexpectedly
            for name, (proc, optional) in list(processes.items()):
                if proc.poll() is not None:
                    print(f"\nWarning: {name} exited with code {proc.returncode}.")
                    if optional:
                        print(f"{name} was optional, removing from active processes...")
                        del processes[name]
                    else:
                        cleanup()
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()
