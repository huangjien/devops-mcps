import logging
import logging.handlers
import sys

# Define logging parameters
LOG_FILENAME = "mcp_server.log"
MAX_LOG_SIZE_MB = 4
MAX_BYTES = MAX_LOG_SIZE_MB * 1024 * 1024
BACKUP_COUNT = 0  # Set to 0 to overwrite (delete the old log on rotation)
LOG_LEVEL = logging.DEBUG  # Set the log level to DEBUG

# Create formatter - Added %(lineno)d for line number
log_formatter = logging.Formatter(
  "%(asctime)s - %(name)s - %(levelname)s:%(lineno)d - %(message)s"
)


def setup_logging() -> bool:
  """Configure logging for the application.

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
    rotating_handler.setFormatter(log_formatter)
    root_logger.addHandler(rotating_handler)
    file_logging_enabled = True
  except Exception as file_log_error:
    # Log error to stderr if file handler setup fails
    logging.basicConfig(level=LOG_LEVEL, format=log_formatter._fmt, stream=sys.stderr)
    logging.error(
      f"Failed to configure file logging to {log_file_path}: {file_log_error}"
    )

  # Disable console logging to avoid interfering with MCP protocol
  console_logging_enabled = False

  # Initialize logger for this module AFTER handlers are added
  logger = logging.getLogger(__name__)

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
    print("CRITICAL: Logging could not be configured.", file=sys.stderr)

  return file_logging_enabled
