import subprocess
import os
import platform
import time
import signal

server1_process = None
server2_process = None


def run_server1():
    if platform.system() != 'Linux':
        raise "This App runs only on Ubuntu>20.4"
    environment_name = 'fairseq'
    activate_command = f"conda activate {environment_name}  && python server1/app.py"

    return subprocess.Popen(activate_command, shell=True, cwd="server1")


def run_server2():
    if platform.system() != 'Linux':
        raise "This App runs only on Ubuntu>20.4"
    environment_name = 'pynnote'
    activate_command = f"conda activate {environment_name} && python server2/app.py"
    return subprocess.Popen(activate_command, shell=True, cwd="server2")


def print_server_info():
    print("Server 1 is running on http://127.0.0.1:5000/")
    print("Server 2 is running on http://127.0.0.1:8000/")


def stop_servers(signum, frame):
    global server1_process, server2_process
    print("\nStopping servers...")
    if server1_process:
        server1_process.terminate()
    if server2_process:
        server2_process.terminate()


if __name__ == "__main__":
    try:

        signal.signal(signal.SIGINT, stop_servers)
        # Run Server 1
        print("Starting Server 1...")
        server1_process = run_server1()

        # Allow some time for Server 1 to start before starting Server 2
        time.sleep(5)

        # Run Server 2
        print("Starting Server 2...")
        server2_process = run_server2()

        # Print server info to the console
        print_server_info()

        # Keep the script running
        input("Press Enter to exit...")

    except KeyboardInterrupt:
        stop_servers(None, None)
