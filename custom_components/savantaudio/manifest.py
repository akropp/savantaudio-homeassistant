"""Manifest version information."""
import json
import os

# Get the path to the manifest.json file
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "manifest.json")

# Read the manifest.json file
with open(MANIFEST_PATH) as manifest_file:
    manifest_data = json.load(manifest_file)

# Extract the version
__version__ = manifest_data.get("version", "unknown")
