#!/bin/sh
set -e
mkdir -p /app/uploaded_images
# Volume mount hides image-bundled OCR seed files; restore them if missing
if [ -d /app/ocr_seed ]; then
  for f in /app/ocr_seed/*; do
    [ -f "$f" ] || continue
    base=$(basename "$f")
    if [ ! -f "/app/uploaded_images/$base" ]; then
      cp "$f" "/app/uploaded_images/"
    fi
  done
fi
exec gunicorn app:app --bind "0.0.0.0:${PORT:-10000}" --timeout 300 --workers 1 --threads 4
