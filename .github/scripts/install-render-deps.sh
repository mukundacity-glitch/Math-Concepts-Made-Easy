#!/usr/bin/env bash
set -euo pipefail
# Ubuntu 24.04's runner mirror has stalled previous video exports. Use the
# signed official HTTPS origins with bounded retries for both production and QA.
sudo tee /etc/apt/sources.list.d/ubuntu.sources >/dev/null <<'SOURCES'
Types: deb
URIs: https://archive.ubuntu.com/ubuntu/
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: https://security.ubuntu.com/ubuntu/
Suites: noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
SOURCES
options=(-o Acquire::Retries=2 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30)
timeout 180s sudo apt-get "${options[@]}" update -qq
timeout 900s sudo apt-get "${options[@]}" install -y --no-install-recommends \
  ffmpeg libcairo2-dev libpango1.0-dev pkg-config \
  texlive-latex-base texlive-latex-extra texlive-fonts-recommended dvisvgm cm-super
ffmpeg -version
ffprobe -version
pkg-config --modversion cairo pangocairo
