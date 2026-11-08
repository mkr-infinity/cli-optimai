# ============================================================
# optimai-telegram-node — Docker image
# python:3.12-slim + the STATIC DOCKER CLIENT only.
# NO docker daemon inside the image: on the VPS the daemon comes
# from the host socket mounted at runtime; on Railway it does not
# exist and the bot degrades to the honest warning path.
# ============================================================

FROM python:3.12-slim

# Best-effort static Docker CLI CLIENT (pinned; NOT the daemon).
ARG DOCKER_CLI_VERSION=27.3.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl screen procps docker.io \
    && rm -rf /var/lib/apt/lists/*

# Download official OptimAI CLI binary into /usr/local/bin/optimai-cli.
RUN set -ux; \
    (curl -fsSL "https://cli-node.optimai.network/optimai_cli_ubuntu" -o /usr/local/bin/optimai-cli \
     && chmod +x /usr/local/bin/optimai-cli) \
    || echo "WARNING: optimai-cli binary download failed."

# Best-effort static Docker CLI CLIENT (pinned; NOT the daemon).
RUN set -ux; \
    (curl -fsSL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_CLI_VERSION}.tgz" -o /tmp/docker.tgz \
     && tar -xzf /tmp/docker.tgz -C /tmp \
     && mv /tmp/docker-${DOCKER_CLI_VERSION}/docker /usr/local/bin/docker \
     && chmod +x /usr/local/bin/docker \
     && rm -rf /tmp/docker.tgz /tmp/docker-${DOCKER_CLI_VERSION}) \
    || echo "WARNING: docker CLI client download failed - degraded Docker-unreachable mode."; \
    /usr/local/bin/docker --version > /dev/null 2>&1 \
    || echo "docker client binary absent - the bot will report Docker as unreachable."

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/

# The optimai CLI stores its downloaded core binary and credentials under
# $HOME/.optimai — HOME MUST live on the persistent /data volume, otherwise
# every restart would force a fresh /login.
ENV HOME=/data/home
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /data/home /data/data

VOLUME /data

ENTRYPOINT ["python", "-m", "bot.main"]
