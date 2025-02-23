#!/bin/bash
# ===================================================
# Script Name: automate_run.sh
# Description: Automates stopping and restarting servers at specific times.
#              - Starts daily at 08:00 AM
#              - Stops every 1 hour 55 minutes, restarts after 3 minutes
#              - Special shutdown at 11:15 PM, restarts at 11:18 PM
#              - Final shutdown at 11:30 PM
#              - Restarts at 8:00 AM the next day
#              - Adjusts to the schedule even if started at a different time
#              - Checks every minute
# Usage: Run using './automate_run.sh' for foreground execution.
# ===================================================

start_servers() {
    echo "Starting servers..."
    kill_process_on_port 10003
    kill_process_on_port 8002

    cd server1 || exit
    source activate fairseq
    python app.py &
    echo $! > ../server1.pid
    cd ..
    conda deactivate

    cd server2 || exit
    conda activate pyannote
    python app.py &
    echo $! > ../server2.pid
    cd ..
    conda deactivate

    echo "Servers started."
}

stop_servers() {
    echo "Stopping servers..."
    for pid_file in server1.pid server2.pid; do
        if [[ -f $pid_file ]]; then
            kill $(cat $pid_file) 2>/dev/null
            rm -f $pid_file
        fi
    done
    echo "Servers stopped."
}

kill_process_on_port() {
    local port=$1
    fuser -k -n tcp "$port" 2>/dev/null
}

echo "Server auto-restart script running..."

current_time=$(date +%s)
base_time=$(date -d "08:00" +%s)
if [[ $current_time -lt $base_time ]]; then
    base_time=$((base_time - 86400))  # Adjust for the previous day if needed
fi

# Calculate the next stop time based on 8:00 AM schedule
elapsed=$(( (current_time - base_time) % 6900 ))
next_stop_time=$((current_time - elapsed + 6900))

# Ensure servers do not run between 11:30 PM and 7:55 AM
current_hm=$(date +"%H:%M")
if [[ "$current_hm" > "23:30" || "$current_hm" < "07:55" ]]; then
    echo "[$current_hm] Current time is within shutdown period. Servers will remain stopped."
else
    start_servers
fi

while true; do
    current_time=$(date +%s)
    current_hm=$(date +"%H:%M")

    # Check if it's time for the periodic stop/restart
    if [[ $current_time -ge $next_stop_time ]]; then
        echo "[$current_hm] Stopping servers for scheduled maintenance."
        stop_servers
        sleep 180  # 3 minutes
        echo "[$current_hm] Restarting servers after maintenance."
        start_servers
        next_stop_time=$((next_stop_time + 6900))  # Schedule next stop/restart
    fi

    # Special shutdown at 11:15 PM, restart at 11:18 PM
    if [[ "$current_hm" == "23:15" ]]; then
        echo "[$current_hm] Special shutdown before final stop."
        stop_servers
    elif [[ "$current_hm" == "23:18" ]]; then
        echo "[$current_hm] Restarting servers after special shutdown."
        start_servers
    fi

    # Final shutdown at 11:30 PM
    if [[ "$current_hm" == "23:30" ]]; then
        echo "[$current_hm] Final shutdown. Stopping servers until 8:00 AM."
        stop_servers
        sleep $(( $(date -d "08:00 tomorrow" +%s) - $(date +%s) ))  # Sleep until 8:00 AM
        next_stop_time=$(( $(date -d "08:00" +%s) + 6900 ))  # Reset stop cycle for the next day
    else
        sleep 60  # Check every minute
    fi

done

