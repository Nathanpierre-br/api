FROM valkey/valkey:latest AS base

WORKDIR /app
COPY . .

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN uv sync

CMD ["uv", "run", "supervisord", "-c", "files/supervisord.conf"]
