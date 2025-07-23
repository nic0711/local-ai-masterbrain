#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Start Gunicorn with the environment variables
exec gunicorn -w "${WORKERS}" --threads "${THREADS}" --timeout "${TIMEOUT}" -b 0.0.0.0:5000 app:app
