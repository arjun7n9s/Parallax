#!/usr/bin/env bash
# Start the Android emulator container with a KVM preflight.
#
# Docker Desktop's WSL2 VM does not reliably auto-load the kvm/kvm_intel
# modules across restarts (the /etc/modules-load.d config persists but the
# modules don't), so the x86_64 emulator crash-loops with /dev/kvm missing.
# This wrapper loads the modules first, verifies /dev/kvm, then brings the
# container up.
set -euo pipefail

cd "$(dirname "$0")/.."

echo ">>> Preflight: ensuring KVM modules are loaded in the docker-desktop VM"
if command -v wsl.exe >/dev/null 2>&1; then
    wsl.exe -d docker-desktop -e sh -c "modprobe kvm 2>/dev/null; modprobe kvm_intel 2>/dev/null; ls -l /dev/kvm" \
        || echo "    (could not modprobe via wsl; assuming KVM already present)"
else
    echo "    (wsl.exe not found; assuming KVM already present)"
fi

echo ">>> Starting android-emulator container"
docker compose up -d android-emulator

echo ">>> Waiting for emulator boot (sys.boot_completed) ..."
ADB="${ADB_BIN:-/c/Users/arjun/AppData/Local/Android/Sdk/platform-tools/adb.exe}"
"$ADB" connect localhost:5555 >/dev/null 2>&1 || true
for i in $(seq 1 60); do
    booted="$("$ADB" -s localhost:5555 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
    if [ "$booted" = "1" ]; then
        echo ">>> Emulator booted after ~$((i*5))s"
        echo ">>> Verifying frida-server is running"
        if ! "$ADB" -s localhost:5555 shell ps -A 2>/dev/null | tr -d '\r' | grep -q "frida-server"; then
            echo "!!! frida-server is not running after boot — check: docker logs parallax_android_emulator"
            exit 1
        fi
        "$ADB" devices
        exit 0
    fi
    sleep 5
    "$ADB" connect localhost:5555 >/dev/null 2>&1 || true
done
echo "!!! Emulator did not report boot_completed within 5 min — check: docker logs parallax_android_emulator"
exit 1
