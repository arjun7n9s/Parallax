#!/bin/bash
# Setup script to download and install jadx locally

JADX_VERSION="1.4.7"
JADX_ZIP="jadx-${JADX_VERSION}.zip"
JADX_URL="https://github.com/skylot/jadx/releases/download/v${JADX_VERSION}/${JADX_ZIP}"
INSTALL_DIR="/usr/local/jadx"

echo "Downloading jadx v${JADX_VERSION}..."
curl -L -o /tmp/${JADX_ZIP} ${JADX_URL}

echo "Extracting jadx..."
sudo unzip -q /tmp/${JADX_ZIP} -d ${INSTALL_DIR}

echo "Linking jadx to /usr/local/bin..."
sudo ln -sf ${INSTALL_DIR}/bin/jadx /usr/local/bin/jadx
sudo ln -sf ${INSTALL_DIR}/bin/jadx-gui /usr/local/bin/jadx-gui

echo "Cleaning up..."
rm /tmp/${JADX_ZIP}

echo "jadx successfully installed!"
jadx --version
