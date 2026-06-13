# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM docker.abrha.net/node:20-alpine AS builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./

# Inject backend URL at build time if provided; otherwise Nginx proxies it.
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ── Stage 2: serve ─────────────────────────────────────────────────────────────
FROM docker.abrha.net/nginx:latest AS runtime

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built SPA
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config:
#   - serves the SPA (all paths → index.html)
#   - proxies /health /ingest /query to the backend container
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]