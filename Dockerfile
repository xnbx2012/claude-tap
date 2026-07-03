FROM python:3.13-slim AS runtime

ARG PACKAGE_VERSION=0.0.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SETUPTOOLS_SCM_PRETEND_VERSION_FOR_CLAUDE_TAP=${PACKAGE_VERSION} \
    CLAUDE_TAP_DATA_DIR=/data

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /data/ca /data/traces

# Persist this single directory to keep the CA certificate, private key,
# trace database, and exported trace files across container restarts.
VOLUME ["/data"]
WORKDIR /data

EXPOSE 8080 19527

COPY pyproject.toml README.md ./
COPY claude_tap ./claude_tap

RUN pip install .

ENTRYPOINT ["claude-tap"]
CMD ["--tap-proxy-mode", "web_proxy", "--tap-host", "0.0.0.0", "--tap-live", "--tap-live-port", "19527", "--tap-no-open"]
