# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/logger.py
import logging
import logging.handlers
import sys
import os  # Import the os module

# --- Configuration ---
# Default to writing the log into the current working directory.
# This ensures the log file is created relative to where the server is run from.
LOG_FILENAME = os.environ.get("LOG_FILENAME", "mcp_server.log")
MAX_LOG_SIZE_MB = 5
MAX_BYTES = MAX_LOG_SIZE_MB * 1024 * 1024
BACKUP_COUNT = 0  # Set to 0 to overwrite (delete the old log on rotation)

# --- Determine Log Level from Environment Variable ---
# Default to INFO for production use. The LOG_LEVEL env var can override this at runtime.
DEFAULT_LOG_LEVEL = "INFO"
LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

# Map string level names to logging constants
log_level_map = {
  "DEBUG": logging.DEBUG,
  "INFO": logging.INFO,
  "WARNING": logging.WARNING,
  "ERROR": logging.ERROR,
  "CRITICAL": logging.CRITICAL,
}

# Get the logging level constant, default to INFO if invalid
LOG_LEVEL = log_level_map.get(LOG_LEVEL_STR, logging.INFO)

# --- Create Formatter ---
# Added %(lineno)d for line number
log_formatter = logging.Formatter(
  "%(levelname)s %(asctime)s - %(name)s:%(lineno)d - %(message)s"
)

# --- Logging Setup Function ---


def setup_logging() -> bool:
  """Configure logging for the application based on environment variables.

  Reads the LOG_LEVEL environment variable (defaulting to INFO).

  Returns:
      bool: True if file logging was successfully configured, False otherwise
  """
  # Configure Root Logger
  root_logger = logging.getLogger()
  root_logger.setLevel(LOG_LEVEL)  # Set the desired global level
  root_logger.handlers.clear()  # Clear any existing handlers

  # Rotating File Handler
  log_file_path = LOG_FILENAME  # Use relative path for simplicity here
  file_logging_enabled = False

  try:
    rotating_handler = logging.handlers.RotatingFileHandler(
      filename=log_file_path,
      maxBytes=MAX_BYTES,
      backupCount=BACKUP_COUNT,
      encoding="utf-8",
    )
    # Ensure the handler uses the configured logging level
    rotating_handler.setLevel(LOG_LEVEL)
    rotating_handler.setFormatter(log_formatter)
    root_logger.addHandler(rotating_handler)
    file_logging_enabled = True
  except Exception as file_log_error:
    # Log error to stderr if file handler setup fails
    # Use basicConfig only if file handler fails, ensuring some logging output
    logging.basicConfig(level=LOG_LEVEL, format=log_formatter._fmt, stream=sys.stderr)
    logging.error(
      f"Failed to configure file logging to {log_file_path}: {file_log_error}"
    )

  # Disable console logging to avoid interfering with MCP protocol
  console_logging_enabled = False

  # Initialize logger for this module AFTER handlers are added
  logger = logging.getLogger(__name__)

  # Install a global excepthook so uncaught exceptions are captured in the
  # log file. This is important when the process exits with code 1 due to an
  # unhandled error.
  def _handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    # Don't log KeyboardInterrupt as an error to avoid noisy logs on Ctrl-C
    if issubclass(exc_type, KeyboardInterrupt):
      sys.__excepthook__(exc_type, exc_value, exc_traceback)
      return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

  sys.excepthook = _handle_uncaught_exception

  # Log a warning if the provided LOG_LEVEL env var was invalid
  if LOG_LEVEL_STR not in log_level_map:
    logger.warning(
      f"Invalid LOG_LEVEL '{os.environ.get('LOG_LEVEL')}' provided in environment. "
      f"Defaulting to '{DEFAULT_LOG_LEVEL}' ({logging.getLevelName(LOG_LEVEL)})."
    )

  log_destinations = []
  if file_logging_enabled:
    log_destinations.append(
      f"File ({log_file_path}, MaxSize: {MAX_LOG_SIZE_MB}MB, Backups: {BACKUP_COUNT})"
    )
  if console_logging_enabled:
    log_destinations.append("Console (stderr)")

  if log_destinations:
    logger.info(
      f"Logging configured (Level: {logging.getLevelName(LOG_LEVEL)}) -> {' & '.join(log_destinations)}"
    )
  else:
    # If even basicConfig failed (e.g., stderr issue), print might be the only option
    print("CRITICAL: Logging could not be configured.", file=sys.stderr)

  return file_logging_enabled
