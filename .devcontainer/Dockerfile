FROM python:3.12-slim

# System deps: git, sqlite, build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    sqlite3 \
    libsqlite3-dev \
    curl \
    ca-certificates \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22 (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Python tools — installed as root before user switch
RUN pip install --no-cache-dir uv

# Create non-root vscode user (UID/GID 1000) with passwordless sudo
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME

WORKDIR /workspace
