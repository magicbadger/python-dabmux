"""
ZMQ Remote Control Protocol.

Defines message formats and command specifications.
"""
from typing import Dict, Any, TypedDict


class ZmqRequest(TypedDict):
    """ZMQ request message format."""
    command: str  # Command name
    args: Dict[str, Any]  # Command arguments


class ZmqResponse(TypedDict):
    """ZMQ response message format."""
    success: bool  # Success flag
    data: Dict[str, Any]  # Response data (if success)
    error: str  # Error message (if not success)


# Command specifications
COMMANDS = {
    # Statistics
    "get_statistics": {
        "description": "Get multiplexer statistics",
        "args": {},
        "returns": {
            "frame_count": "int",
            "uptime_seconds": "float",
            "ensemble_id": "str",
            "num_services": "int",
            "num_subchannels": "int",
        }
    },

    # Dynamic labels
    "get_label": {
        "description": "Get dynamic label text",
        "args": {
            "component_uid": "str"
        },
        "returns": {
            "text": "str",
            "charset": "int",
            "toggle": "bool"
        }
    },

    "set_label": {
        "description": "Set dynamic label text",
        "args": {
            "component_uid": "str",
            "text": "str"
        },
        "returns": {
            "success": "bool"
        }
    },

    # Announcements
    "trigger_announcement": {
        "description": "Trigger announcement",
        "args": {
            "service_id": "int",
            "type": "str",  # 'alarm', 'traffic', 'news', etc.
            "subchannel_id": "int"
        },
        "returns": {
            "success": "bool"
        }
    },

    "clear_announcement": {
        "description": "Clear active announcement",
        "args": {
            "service_id": "int",
            "type": "str"
        },
        "returns": {
            "success": "bool"
        }
    },

    # Service parameters
    "get_service_info": {
        "description": "Get service information",
        "args": {
            "service_uid": "str"
        },
        "returns": {
            "id": "int",
            "label": "str",
            "pty": "int",
            "language": "int"
        }
    },

    # Input control
    "get_input_status": {
        "description": "Get input source status",
        "args": {
            "subchannel_uid": "str"
        },
        "returns": {
            "connected": "bool",
            "bitrate": "int",
            "frames_read": "int"
        }
    },

    # Carousel control (MOT)
    "reload_carousel": {
        "description": "Reload MOT carousel from directory",
        "args": {
            "component_uid": "str"
        },
        "returns": {
            "objects_loaded": "int"
        }
    },

    "get_carousel_stats": {
        "description": "Get carousel statistics",
        "args": {
            "component_uid": "str"
        },
        "returns": {
            "num_objects": "int",
            "packets_transmitted": "int",
            "total_bytes": "int"
        }
    },

    # Service parameter updates (Phase 2)
    "set_service_pty": {
        "description": "Set service Programme Type",
        "args": {
            "service_uid": "str",
            "pty": "int"  # 0-31
        },
        "returns": {
            "success": "bool"
        }
    },

    "set_service_language": {
        "description": "Set service language",
        "args": {
            "service_uid": "str",
            "language": "int"  # 0-127
        },
        "returns": {
            "success": "bool"
        }
    },

    "set_service_label": {
        "description": "Set service static label",
        "args": {
            "service_uid": "str",
            "text": "str",  # Max 16 chars
            "short_text": "str"  # Max 8 chars (optional)
        },
        "returns": {
            "success": "bool"
        }
    },

    "get_all_services": {
        "description": "Get list of all services",
        "args": {},
        "returns": {
            "services": "list[dict]"
        }
    },

    "get_all_components": {
        "description": "Get list of all components",
        "args": {},
        "returns": {
            "components": "list[dict]"
        }
    },

    "get_all_subchannels": {
        "description": "Get list of all subchannels",
        "args": {},
        "returns": {
            "subchannels": "list[dict]"
        }
    },

    # Utility
    "list_commands": {
        "description": "List all available commands",
        "args": {},
        "returns": {
            "commands": "list[str]"
        }
    },

    "get_command_info": {
        "description": "Get information about a specific command",
        "args": {
            "command": "str"
        },
        "returns": {
            "description": "str",
            "args": "dict",
            "returns": "dict"
        }
    },

    # Runtime control (Phase 4)
    "set_log_level": {
        "description": "Set logging level at runtime",
        "args": {
            "level": "str",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
            "module": "str"  # Optional module name
        },
        "returns": {
            "success": "bool",
            "level": "str",
            "module": "str",
            "message": "str"
        }
    },

    "get_log_level": {
        "description": "Get current logging level",
        "args": {
            "module": "str"  # Optional module name
        },
        "returns": {
            "level": "str",
            "numeric_level": "int",
            "module": "str"
        }
    },
}
