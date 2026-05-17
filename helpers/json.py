import json

from pathlib import Path

from helpers.constants import JSON_PATH

def load_json(json_file: str):
  json_path = Path(JSON_PATH) / json_file

  with open(json_path, "r") as f:
    json_data = json.load(f)
    return json_data