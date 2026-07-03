# InitiativeKeep — one image that builds the frontend and serves it from the backend.
#
# Two "stages": first a Node box builds the React app into static files,
# then a Python box runs FastAPI and serves those files. Only the final
# Python box ends up in the shipped image (the Node box is thrown away).

# ---- Stage 1: build the React frontend into static files ----
FROM node:22-alpine AS frontend
WORKDIR /fe
# copy only package files first so Docker can cache "npm ci" when code changes
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build            # produces /fe/dist (index.html + JS/CSS)

# ---- Stage 2: Python backend that also serves the built frontend ----
FROM python:3.14-slim AS backend
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# gcc is needed in case a dependency (e.g. asyncpg) has no prebuilt wheel
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
# drop the built SPA where FastAPI looks for it (backend/frontend_dist)
COPY --from=frontend /fe/dist ./frontend_dist

COPY entrypoint.sh /entrypoint.sh
# strip possible Windows CRLF line endings, then make it executable
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
