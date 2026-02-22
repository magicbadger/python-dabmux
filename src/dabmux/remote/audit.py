"""
Audit logging for remote control commands.

Logs all command executions for security and compliance.
"""
import json
import time
import structlog
from typing import Dict, Any, Optional
from pathlib import Path

logger = structlog.get_logger(__name__)


class AuditLogger:
    """
    Audit logger for remote control commands.

    Logs command executions to both structlog and a JSON file.
    """

    def __init__(self, log_file: Optional[str] = None) -> None:
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file (optional)
        """
        self.log_file = Path(log_file) if log_file else None
        self.enabled = log_file is not None

        if self.log_file:
            # Ensure parent directory exists
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Audit logging enabled", log_file=str(self.log_file))
        else:
            logger.info("Audit logging disabled (no log file configured)")

    def log_command(
        self,
        source: str,
        client: str,
        command: str,
        args: Dict[str, Any],
        success: bool,
        duration_ms: float,
        error: Optional[str] = None
    ) -> None:
        """
        Log a command execution.

        Args:
            source: Command source ("zmq" or "telnet")
            client: Client address (e.g., "127.0.0.1:12345")
            command: Command name
            args: Command arguments (will be sanitized)
            success: Whether command succeeded
            duration_ms: Execution duration in milliseconds
            error: Error message if command failed
        """
        if not self.enabled:
            return

        # Sanitize sensitive data from args
        safe_args = self._sanitize_args(args)

        entry = {
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "source": source,
            "client": client,
            "command": command,
            "args": safe_args,
            "success": success,
            "duration_ms": round(duration_ms, 2)
        }

        if error:
            entry["error"] = error

        # Log to structlog
        if success:
            logger.info("command_executed", **entry)
        else:
            logger.warning("command_failed", **entry)

        # Append to file
        if self.log_file:
            try:
                with self.log_file.open('a') as f:
                    f.write(json.dumps(entry) + '\n')
            except Exception as e:
                logger.error("Failed to write audit log", error=str(e))

    def _sanitize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize sensitive data from arguments.

        Args:
            args: Original arguments

        Returns:
            Sanitized arguments with sensitive fields redacted
        """
        # List of sensitive field names to redact
        sensitive_fields = ['password', 'auth', 'token', 'secret', 'key']

        sanitized = {}
        for key, value in args.items():
            # Check if field name contains sensitive keywords
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value

        return sanitized

    def get_recent_entries(self, count: int = 100) -> list:
        """
        Get recent audit log entries.

        Args:
            count: Number of recent entries to return

        Returns:
            List of audit log entries (newest first)
        """
        if not self.log_file or not self.log_file.exists():
            return []

        entries = []
        try:
            with self.log_file.open('r') as f:
                # Read last N lines efficiently
                lines = f.readlines()
                for line in lines[-count:]:
                    try:
                        entry = json.loads(line.strip())
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue

            # Return newest first
            return list(reversed(entries))

        except Exception as e:
            logger.error("Failed to read audit log", error=str(e))
            return []
