FROM valkey/valkey:trixie@sha256:3b55fbaa0cd93cf0d9d961f405e4dfcc70efe325e2d84da207a0a8e6d8fde4f9 AS base

WORKDIR /app
COPY . .

COPY --from=ghcr.io/astral-sh/uv:0.11.3@sha256:90bbb3c16635e9627f49eec6539f956d70746c409209041800a0280b93152823 /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y ca-certificates

RUN uv sync

RUN useradd -U -u 1000 appuser && chown -R 1000:1000 /app
USER 1000

CMD ["uv", "run", "supervisord", "-c", "files/supervisord.conf"]
