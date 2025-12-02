#!/bin/bash
set -e

echo "Plan2Scene Backend Starting..."
echo "PYTHONPATH: $PYTHONPATH"

# Note: Room type normalization is now handled by r2v_converter.py normalize_scene_json()
# We no longer modify the Plan2Scene repository's room_types.json (it's read-only)
# The 12 standard room types in /app/static/plan2scene_labels/room_types.json are used

# Execute the main command (uvicorn)
exec "$@"
