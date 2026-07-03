#!/bin/sh
# Runs every time the container starts.
set -e

# make sure the folder for the SQLite database file exists
mkdir -p /data

# create/update database tables to match the code (safe to run every start)
aerich upgrade

# start the web server, listening on all interfaces inside the container
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
