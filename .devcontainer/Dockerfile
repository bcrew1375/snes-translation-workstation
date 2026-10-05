FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04
ARG ASAR_VERSION=v1.91
ARG BSNES_PLUS_COMMIT=master
ARG NOVNC_VERSION=v1.7.0
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
 build-essential clang cmake pkg-config git ca-certificates curl wget unzip python3 python3-pip python3-venv python3-pil python3-yaml \
 qtbase5-dev qtbase5-dev-tools libxv-dev libsdl1.2-dev libao-dev libopenal-dev libdbus-1-dev \
 xxd jq ripgrep file bc less vim-tiny xvfb x11vnc openbox xterm dbus-x11 x11-utils websockify supervisor \
 && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch "${ASAR_VERSION}" https://github.com/RPGHacker/asar.git /tmp/asar \
 && cmake -S /tmp/asar/src -B /tmp/asar/build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build /tmp/asar/build -j"$(nproc)" \
 && install -m 0755 /tmp/asar/build/asar/bin/asar /usr/local/bin/asar \
 && rm -rf /tmp/asar
RUN git clone --depth 1 https://github.com/devinacker/bsnes-plus.git /tmp/bsnes-plus \
 && git -C /tmp/bsnes-plus submodule update --init --recursive \
 && make -C /tmp/bsnes-plus/bsnes -j"$(nproc)" \
 && install -m 0755 /tmp/bsnes-plus/bsnes/out/bsnes /usr/local/bin/bsnes-plus \
 && rm -rf /tmp/bsnes-plus
RUN git clone --depth 1 --branch "${NOVNC_VERSION}" https://github.com/novnc/noVNC.git /opt/novnc \
 && ln -s /opt/novnc/vnc.html /opt/novnc/index.html
WORKDIR /workspaces
