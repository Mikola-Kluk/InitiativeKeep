#!/bin/sh
# Runs every time the container starts.
set -e

# make sure the folder for the SQLite database file exists
mkdir -p /data

# create database tables from the models (dialect-correct on SQLite & Postgres;
# safe to run every start). Replaces `aerich upgrade`, whose committed migrations
# are SQLite-only SQL and break on Postgres.
python init_db.py

# start the web server, listening on all interfaces inside the container.
# Render (and most PaaS) inject the port to bind via $PORT; fall back to 8000
# for local Docker / docker-compose where PORT is unset.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
