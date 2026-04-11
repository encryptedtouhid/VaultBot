"""Structured logging setup with file output, rotation, and separate audit log.

Log files:
    ~/.vaultbot/logs/zenbot.log       — application log (all events)
    ~/.vaultbot/logs/zenbot.error.log  — errors only
    ~/.vaultbot/logs/audit.log         — security audit events

All logs use structured JSON format for machine parsing.
Console output uses human-readable colored format.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

import structlog

_LOG_DIR = Path.home() / ".vaultbot" / "logs"

# Max 10MB per log file, keep 5 rotated backups
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5


def setup_logging(
    *,
    json_output: bool = False,
    level: str = "INFO",
    log_dir: Path | None = None,
    enable_file_logging: bool = True,
) -> None:
    """Configure structlog with console + file output.

    Args:
        json_output: Use JSON format for console output.
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files. Defaults to ~/.vaultbot/logs/.
        enable_file_logging: Write logs to files (disable for testing).
    """
    log_path = log_dir or _LOG_DIR

    if enable_file_logging:
        log_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        _setup_stdlib_logging(log_path, level)

    # structlog processors shared by all outputs
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        # Add caller info (file, function, line number) for detailed tracing
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    if enable_file_logging:
        # Route structlog through stdlib logging for file output
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, level.upper(), logging.INFO)
            ),
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Console-only mode (for tests)
        console_processors = [*shared_processors]
        if json_output:
            console_processors.append(structlog.processors.JSONRenderer())
        else:
            console_processors.append(structlog.dev.ConsoleRenderer())

        structlog.configure(
            processors=console_processors,
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, level.upper(), logging.INFO)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


def _setup_stdlib_logging(log_dir: Path, level: str) -> None:
    """Configure stdlib logging with file handlers for structlog to route through."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicates on re-init
    root_logger.handlers.clear()

    # --- JSON formatter for file output ---
    json_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    # --- Colored formatter for console ---
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(),
        ],
    )

    # 1. Console handler (human-readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 2. Main application log (all levels, JSON, rotating)
    app_log = log_dir / "vaultbot.log"
    app_handler = logging.handlers.RotatingFileHandler(
        app_log, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    app_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    app_handler.setFormatter(json_formatter)
    app_log.chmod(0o600)
    root_logger.addHandler(app_handler)

    # 3. Error-only log (WARNING+, JSON, rotating)
    error_log = log_dir / "vaultbot.error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(json_formatter)
    error_log.chmod(0o600)
    root_logger.addHandler(error_handler)

    # 4. Audit log (separate file for security events only)
    audit_logger = logging.getLogger("vaultbot.audit")
    audit_log = log_dir / "audit.log"
    audit_handler = logging.handlers.RotatingFileHandler(
        audit_log, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(json_formatter)
    audit_log.chmod(0o600)
    audit_logger.addHandler(audit_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named logger instance."""
    return structlog.get_logger(name)  # type: ignore[return-value]
