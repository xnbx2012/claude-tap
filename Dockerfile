FROM python:3.13-slim AS runtime

ARG PACKAGE_VERSION=0.0.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SETUPTOOLS_SCM_PRETEND_VERSION_FOR_CLAUDE_TAP=${PACKAGE_VERSION}

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /root/.claude-tap /root/.traces

# Trace output and CA directory are persisted at these host paths:
#   - /root/.claude-tap   — CA certificate and private key
#   - /root/.traces       — SQLite trace database and JSONL files
WORKDIR /root

EXPOSE 8080 19527

COPY pyproject.toml README.md ./
COPY claude_tap ./claude_tap

RUN pip install .

ENTRYPOINT ["claude-tap"]
CMD ["--tap-proxy-mode", "web_proxy", "--tap-host", "0.0.0.0", "--tap-live", "--tap-live-port", "19527", "--tap-no-open"]
