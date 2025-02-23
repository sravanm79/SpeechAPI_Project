#!/bin/bash
# Function to check if a port is in use
is_port_in_use() {
    lsof -i ":$1" > /dev/null
}

# Function to kill processes running on a port
kill_process_on_port() {
    local port=$1
    local process_ids=$(fuser -k -n tcp "$port" 2>/dev/null)

    if [ -n "$process_ids" ]; then
        echo "Killing processes on port $port (PIDs: $process_ids)..."
        echo "$process_ids" | xargs kill -9

        # Wait for the processes to terminate
        for process_id in $process_ids; do
            while ps -p "$process_id" > /dev/null; do
                sleep 1
            done
        done

        echo "Processes terminated on port $port"
    else
        echo "No processes found on port $port"
    fi
}

kill_process_on_port 10003
kill_process_on_port 8002
#

# Start Server 1
echo "Starting Server 1..."
cd server1
source activate fairseq
python app.py &
pid_server1=$!
echo "Server 1 started with PID: $pid_server1"
cd ..
conda deactivate

# Start Server 2
echo "Starting Server 2..."
cd server2
conda activate pyannote
python app.py &
pid_server2=$!
echo "Server 2 started with PID: $pid_server2"
cd ..
conda deactivate



# Wait for user input to stop the servers
echo "Press Enter to stop the servers..."
read -r

# Stop API


# Stop Server 1
echo "Stopping Server 1..."
kill $pid_server1
echo "Server 1 stopped"

# Stop Server 2
echo "Stopping Server 2..."
kill $pid_server2
echo "Server 2 stopped"


echo "Servers stopped."

