FROM valkey/valkey:trixie AS base

WORKDIR /app
COPY . .

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y ca-certificates

RUN useradd -U -u 1000 appuser
RUN mkdir -p /home/appuser/.cache/uv
RUN chown -R 1000:1000 /app /home/appuser/
USER 1000

RUN uv sync

CMD ["uv", "run", "supervisord", "-c", "files/supervisord.conf"]
