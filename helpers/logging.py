import logging
import os
import sys

def configure_logging(level: str | None = None) -> None:
  level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
  level_value = getattr(logging, level_name, logging.INFO)
  log_format = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s %(levelname)s %(name)s: %(message)s",
  )
  date_format = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")

  logging.basicConfig(
    level = level_value,
    format = log_format,
    datefmt = date_format,
    stream = sys.stdout,
  )

def get_logger(name: str) -> logging.Logger:
  return logging.getLogger(name)
