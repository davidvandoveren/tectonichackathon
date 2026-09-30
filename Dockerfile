# syntax=docker/dockerfile:1.7
# One image, one Cloud Run service: FastAPI serves the API *and* the built SPA (same origin,
# so no CORS and strict SameSite cookies just work).

# --- 1. build the frontend ------------------------------------------------------------------
FROM node:24-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- 2. runtime -----------------------------------------------------------------------------
FROM python:3.13-slim AS runtime
# TRUSTED_PROXY_HOPS=1: Cloud Run's front end appends the real client IP to X-Forwarded-For, and
# the login rate limiter reads exactly that entry (see backend/app/security/client_ip.py).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    STATIC_DIR=/app/static \
    PORT=8080 \
    TRUSTED_PROXY_HOPS=1
WORKDIR /app
RUN groupadd --system app && useradd --system --gid app --no-create-home app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/app ./app
COPY --from=web /web/dist ./static
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request as u; u.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/health')"]
# Cloud Run injects $PORT; only Google's front end can reach the container, so trusting its
# X-Forwarded-Proto is safe there. The client IP for rate limiting is NOT taken from uvicorn (which
# would pick the spoofable leftmost X-Forwarded-For entry) but via TRUSTED_PROXY_HOPS above.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
