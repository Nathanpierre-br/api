FROM valkey/valkey:latest AS base

WORKDIR /app
COPY . .

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
    
RUN uv sync

CMD ["uv", "run", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8081"]
