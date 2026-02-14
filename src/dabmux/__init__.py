"""
Python DAB Multiplexer

A pure Python implementation of a DAB/DAB+ multiplexer, recreating the
functionality of ODR-DabMux.
"""
import logging
import structlog

# Configure structlog for clean, structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

__version__ = "0.1.0"
