param(
    [string]$Distro = "docker-desktop"
)

$ErrorActionPreference = "Stop"

Write-Host ">>> Loading KVM modules in WSL distro '$Distro'"
wsl -d $Distro -- sh -c "modprobe kvm && modprobe kvm_intel"

Write-Host ">>> Verifying /dev/kvm"
$output = wsl -d $Distro -- sh -c "ls -la /dev/kvm"
Write-Host $output

if ($LASTEXITCODE -ne 0 -or $output -notmatch "10,\s*232") {
    throw "Docker Desktop WSL2 KVM preflight failed; expected /dev/kvm major/minor 10,232."
}

Write-Host ">>> Docker Desktop WSL2 KVM is ready"
