import os
import time

if os.name != 'nt':
    time.tzset()

# Gunicorn configuration
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"

# Logging configuration
# Use the same format for Gunicorn as we want for the app
accesslog = "-"
errorlog = "-"

# Custom log format to match your desired output
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "generic": {
            "format": "[%(asctime)s] [%(process)d] [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S %z",
            "class": "logging.Formatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stdout",
        },
        "error_console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "gunicorn.error": {
            "level": "WARNING",
            "handlers": ["error_console"],
            "propagate": False,
            "qualname": "gunicorn.error",
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
            "qualname": "gunicorn.access",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    }
}
