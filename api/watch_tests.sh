#!/bin/bash
while true; do
  clear
  echo "Running tests..."
  uv run python manage.py test tests/
  echo "Waiting for file changes..."
  sleep 2
done
