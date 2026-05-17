import uuid

from datetime import datetime, timezone

def current_run_info():
  run_id = str(uuid.uuid4())
  run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

  return run_id, run_ts

