FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04
ARG ASAR_VERSION=v1.91
ARG BSNES_PLUS_COMMIT=a9789fab9a26859153c2963defe186fcaaa80ca2
ARG MESEN_AGENT_COMMIT=dbc2c744ad52e1c89a8570d22d7fa92507ad4816
ARG NOVNC_VERSION=v1.7.0
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
 build-essential clang cmake pkg-config git ca-certificates curl wget unzip python3 python3-pip python3-venv python3-pil python3-yaml \
 qtbase5-dev qtbase5-dev-tools libxv-dev libsdl1.2-dev libao-dev libopenal-dev libdbus-1-dev \
 xxd jq ripgrep file bc less vim-tiny xvfb x11vnc openbox xterm dbus-x11 x11-utils websockify supervisor \
 # Noto CJK supplies Japanese glyphs. Without them the original text renders as
 # tofu in the GUI, the editor, and rendered font/graphics analysis, so Japanese
 # source text cannot be read or reviewed at all.
 fonts-noto-cjk fonts-noto-cjk-extra \
 && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch "${ASAR_VERSION}" https://github.com/RPGHacker/asar.git /tmp/asar \
 && cmake -S /tmp/asar/src -B /tmp/asar/build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build /tmp/asar/build -j"$(nproc)" \
 && install -m 0755 /tmp/asar/build/asar/bin/asar /usr/local/bin/asar \
 && rm -rf /tmp/asar
RUN git clone --filter=blob:none https://github.com/devinacker/bsnes-plus.git /tmp/bsnes-plus \
 && git -C /tmp/bsnes-plus checkout --detach "${BSNES_PLUS_COMMIT}" \
 && git -C /tmp/bsnes-plus submodule update --init --recursive \
 && make -C /tmp/bsnes-plus/bsnes -j"$(nproc)" \
 && install -m 0755 /tmp/bsnes-plus/bsnes/out/bsnes /usr/local/bin/bsnes-plus \
 && rm -rf /tmp/bsnes-plus
RUN git clone --filter=blob:none https://github.com/atonamy/mesen-agent.git /tmp/mesen-agent \
 && git -C /tmp/mesen-agent checkout --detach "${MESEN_AGENT_COMMIT}" \
 && make -C /tmp/mesen-agent agent -j"$(nproc)" \
 && agent_dir="$(find /tmp/mesen-agent/bin -mindepth 2 -maxdepth 2 -type d -name Release -print -quit)" \
 && test -n "${agent_dir}" \
 && install -m 0755 "${agent_dir}/mesen-agent" /usr/local/bin/mesen-agent \
 && install -m 0644 "${agent_dir}/MesenCore.so" /usr/local/bin/MesenCore.so \
 && printf '%s\n' "${MESEN_AGENT_COMMIT}" > /usr/local/bin/mesen-agent.revision \
 && rm -rf /tmp/mesen-agent
RUN git clone --depth 1 --branch "${NOVNC_VERSION}" https://github.com/novnc/noVNC.git /opt/novnc \
 && ln -s /opt/novnc/vnc.html /opt/novnc/index.html
WORKDIR /workspaces
