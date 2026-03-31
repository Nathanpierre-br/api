FROM valkey/valkey:latest AS base

WORKDIR /app
COPY . .

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt update
RUN apt install supervisor -y

RUN uv sync

CMD ["supervisord", "-c", "files/supervisord.conf"]
