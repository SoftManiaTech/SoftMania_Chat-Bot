import logging
import sys
import os

# On Vercel/Lambda the working directory is read-only. Use /tmp for log files
# when the standard 'logs' directory cannot be created (read-only filesystem).
def _get_log_dir() -> str | None:
    """Returns a writable log directory, or None if no file logging is possible."""
    candidates = [
        os.path.join(os.getcwd(), "logs"),  # preferred: project logs/ dir (local/Docker)
        "/tmp/logs",                         # fallback: Vercel/Lambda ephemeral storage
    ]
    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except OSError:
            continue
    return None  # console-only logging (no writable path found)

def setup_logger(name: str) -> logging.Logger:
    """Sets up a standardized logger for the application."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Always add console handler (visible in Vercel/Docker logs)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # Add file handler only when a writable directory is available
        log_dir = _get_log_dir()
        if log_dir:
            try:
                fh = logging.FileHandler(os.path.join(log_dir, "server.log"), encoding="utf-8")
                fh.setLevel(logging.INFO)
                fh.setFormatter(formatter)
                logger.addHandler(fh)
            except OSError:
                pass  # file logging silently skipped if still not writable

    return logger
