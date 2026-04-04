FROM valkey/valkey:latest AS base

WORKDIR /app
COPY . .

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y ca-certificates

RUN uv sync

RUN useradd -U -u 1000 appuser && chown -R 1000:1000 /app
USER 1000

CMD ["uv", "run", "supervisord", "-c", "files/supervisord.conf"]
