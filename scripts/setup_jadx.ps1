$JADX_VERSION = "1.4.7"
$JADX_ZIP = "jadx-$JADX_VERSION.zip"
$JADX_URL = "https://github.com/skylot/jadx/releases/download/v$JADX_VERSION/$JADX_ZIP"
$INSTALL_DIR = "C:\jadx"

Write-Host "Downloading jadx v$JADX_VERSION..."
Invoke-WebRequest -Uri $JADX_URL -OutFile $JADX_ZIP

Write-Host "Extracting jadx..."
Expand-Archive -Path $JADX_ZIP -DestinationPath $INSTALL_DIR -Force

Write-Host "Adding jadx to PATH..."
$env:Path += ";$INSTALL_DIR\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::User)

Write-Host "Cleaning up..."
Remove-Item $JADX_ZIP

Write-Host "jadx successfully installed! Please restart your terminal for PATH changes to take effect."
& "$INSTALL_DIR\bin\jadx.bat" --version
