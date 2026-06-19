#!/usr/bin/env bash
# Create an isolated venv for running PARALLAX live Band agents.
#
# Why a separate venv: band-sdk requires cryptography>=46.0.5, while the main
# analysis stack (mitmproxy / pyOpenSSL) requires cryptography<44.1. Those
# ranges do not overlap, so live Band agents MUST run in their own venv,
# isolated from the analysis/test venv (which keeps cryptography<44.1).
#
# The Band remote-agent runner is a standalone process, so this isolation is
# clean: nothing in the live-agent import path needs mitmproxy/frida/androguard.
#
# Paths below assume Windows (Scripts/); on Linux/macOS use bin/ instead.
set -euo pipefail
cd "$(dirname "$0")/.."

python -m venv .venv-band
.venv-band/Scripts/python -m pip install --upgrade pip
.venv-band/Scripts/pip install "band-sdk[langgraph]>=1.0.0" "langchain-openai>=1.3.2"
# Install the PARALLAX package WITHOUT its analysis deps (which would clash on
# cryptography); the Band orchestrator only needs the runtime deps below.
.venv-band/Scripts/pip install -e . --no-deps
.venv-band/Scripts/pip install pydantic-settings sqlalchemy asyncpg minio structlog python-dotenv

echo
echo "Band venv ready. Configure BAND_* + AIML_API in .env, then run live agents:"
echo "  .venv-band/Scripts/python -m parallax.agents.band.band_orchestrator"
