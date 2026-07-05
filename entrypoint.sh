#!/bin/sh
# Runs every time the container starts.
set -e

# make sure the folder for the SQLite database file exists
mkdir -p /data

# create/update database tables to match the code (safe to run every start)
aerich upgrade

# start the web server, listening on all interfaces inside the container.
# Render (and most PaaS) inject the port to bind via $PORT; fall back to 8000
# for local Docker / docker-compose where PORT is unset.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
