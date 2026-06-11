#!/bin/bash
set -e

echo "=== Starting custom emulator entrypoint ==="

# Start the original run.sh in the background
/home/androidusr/docker-android/mixins/scripts/run.sh &
RUN_PID=$!

echo "=== Waiting for emulator to boot ==="

# Determine where adb is
ADB="adb"
if ! command -v adb &> /dev/null; then
    if [ -f "/android-sdk/platform-tools/adb" ]; then
        ADB="/android-sdk/platform-tools/adb"
    fi
fi
echo "Using adb binary at: $ADB"

# Poll for adb connection
timeout=300
elapsed=0
while ! $ADB devices | grep -q -E "device$"; do
    if [ $elapsed -ge $timeout ]; then
        echo "Error: Timeout waiting for adb device connection"
        kill $RUN_PID
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

echo "=== ADB device connected. Waiting for system boot completion ==="
elapsed=0
while [ "$($ADB shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
    if [ $elapsed -ge $timeout ]; then
        echo "Error: Timeout waiting for sys.boot_completed=1"
        kill $RUN_PID
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

echo "=== Android emulator is fully booted! ==="

# Enable root adb
$ADB root
sleep 2

# Push matching frida-server based on CPU ABI
abi=$($ADB shell getprop ro.product.cpu.abi | tr -d '\r')
echo "Emulator CPU ABI: $abi"

if [ "$abi" = "x86_64" ]; then
    echo "Pushing frida-server-x86_64"
    $ADB push /usr/local/bin/frida-server-x86_64 /data/local/tmp/frida-server
else
    echo "Pushing frida-server-x86"
    $ADB push /usr/local/bin/frida-server-x86 /data/local/tmp/frida-server
fi

$ADB shell chmod 755 /data/local/tmp/frida-server

# Check if frida-server is already running, if so, kill it
if $ADB shell ps -A | grep -q "frida-server"; then
    echo "Killing existing frida-server..."
    $ADB shell pkill -f frida-server || true
fi

# Start frida-server in background
echo "Starting frida-server..."
$ADB shell "/data/local/tmp/frida-server -l 0.0.0.0:27042 >/dev/null 2>&1 &"
sleep 3

# Forward frida-server port from container to emulator
echo "Setting up adb port forward for Frida..."
$ADB forward tcp:27043 tcp:27042

# Expose port 27042 externally via socat
echo "Starting socat forwarder for Frida..."
socat tcp-listen:27042,fork tcp:127.0.0.1:27043 &

# Verify frida-server is running
if $ADB shell ps -A | grep -q "frida-server"; then
    echo "frida-server started successfully!"
else
    echo "Error: frida-server failed to start"
    $ADB shell logcat -d | grep -i frida || true
    kill $RUN_PID
    exit 1
fi

echo "=== Emulator and frida-server are fully ready! ==="

# Keep the container running and wait for the original run.sh process
wait $RUN_PID
