# API

![Static Badge](https://img.shields.io/badge/branch-dev-red?style=for-the-badge)

Main branch where magic happens.

Expect bugs, problems and etc.

## Quick Start (WS not configured)
1. Copy `.env.example` as `.env` and fill required variables

2. Set up your DNS/proxy for the dev server

3. Run the container:
```bash
docker compose -f docker-compose.dev.yml up -d --build
```

4. Explore emails on http://localhost:8025

5. Explore s3 buckets on http://localhost:9001
