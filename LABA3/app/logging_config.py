# app/logging_config.py
"""
Structured logging configuration with correlation IDs.
"""
import logging
import structlog
from contextvars import ContextVar
from typing import Optional

# Context variables for correlation
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
task_id_var: ContextVar[Optional[str]] = ContextVar("task_id", default=None)


def add_correlation_ids(logger, method_name, event_dict):
    """Add trace_id and task_id to all log entries."""
    trace_id = trace_id_var.get()
    task_id = task_id_var.get()

    if trace_id:
        event_dict["trace_id"] = trace_id
    if task_id:
        event_dict["task_id"] = task_id

    return event_dict


def setup_logging():
    """Configure structlog with JSON output and correlation IDs."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_correlation_ids,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )


def get_logger(name: str = __name__):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def set_trace_id(trace_id: str):
    """Set trace ID for current context."""
    trace_id_var.set(trace_id)


def set_task_id(task_id: str):
    """Set task ID for current context."""
    task_id_var.set(task_id)


def clear_context():
    """Clear correlation IDs from context."""
    trace_id_var.set(None)
    task_id_var.set(None)
