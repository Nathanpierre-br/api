FROM valkey/valkey:latest AS base

WORKDIR /app
COPY . .

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN echo "deb http://deb.debian.org/debian/ unstable main contrib non-free non-free-firmware" > /etc/apt/sources.list   
RUN apt update
RUN apt install supervisor --no-install-recommends -y

RUN uv sync

CMD ["supervisord", "-c", "files/supervisord.conf"]
