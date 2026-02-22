#!/usr/bin/env python3
"""
Example ZMQ client for python-dabmux remote control.

Demonstrates how to send commands to the multiplexer via ZeroMQ.
"""
import zmq
import json
import sys


def send_command(socket, command, args=None):
    """
    Send command and get response.

    Args:
        socket: ZMQ socket
        command: Command name
        args: Optional command arguments

    Returns:
        Response dict
    """
    request = {
        "command": command,
        "args": args or {}
    }

    socket.send_string(json.dumps(request))
    response_json = socket.recv_string()
    response = json.loads(response_json)

    return response


def print_response(response):
    """Print response in human-readable format."""
    if response["success"]:
        print("✓ Success")
        if "data" in response:
            print("Data:")
            for key, value in response["data"].items():
                print(f"  {key}: {value}")
    else:
        print(f"✗ Error: {response['error']}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python zmq_client.py <command> [args...]")
        print("\nExamples:")
        print("  python zmq_client.py get_statistics")
        print("  python zmq_client.py set_label audio_component 'Now Playing: Song Title 🎵'")
        print("  python zmq_client.py set_service_pty radio1 1")
        print("  python zmq_client.py set_service_language radio1 15")
        print("  python zmq_client.py set_service_label radio1 'New Radio' 'NewRadio'")
        print("  python zmq_client.py get_all_services")
        print("  python zmq_client.py get_all_components")
        print("  python zmq_client.py list_commands")
        sys.exit(1)

    command = sys.argv[1]

    # Build args based on command
    args = {}

    if command == "set_label":
        if len(sys.argv) < 4:
            print("Usage: zmq_client.py set_label <component_uid> <text>")
            sys.exit(1)
        args = {
            "component_uid": sys.argv[2],
            "text": sys.argv[3]
        }

    elif command == "get_label":
        if len(sys.argv) < 3:
            print("Usage: zmq_client.py get_label <component_uid>")
            sys.exit(1)
        args = {"component_uid": sys.argv[2]}

    elif command == "trigger_announcement":
        if len(sys.argv) < 5:
            print("Usage: zmq_client.py trigger_announcement <service_id> <type> <subchannel_id>")
            sys.exit(1)
        args = {
            "service_id": int(sys.argv[2], 0),  # Supports 0x hex
            "type": sys.argv[3],
            "subchannel_id": int(sys.argv[4])
        }

    elif command == "clear_announcement":
        if len(sys.argv) < 4:
            print("Usage: zmq_client.py clear_announcement <service_id> <type>")
            sys.exit(1)
        args = {
            "service_id": int(sys.argv[2], 0),
            "type": sys.argv[3]
        }

    elif command == "get_service_info":
        if len(sys.argv) < 3:
            print("Usage: zmq_client.py get_service_info <service_uid>")
            sys.exit(1)
        args = {"service_uid": sys.argv[2]}

    elif command == "get_input_status":
        if len(sys.argv) < 3:
            print("Usage: zmq_client.py get_input_status <subchannel_uid>")
            sys.exit(1)
        args = {"subchannel_uid": sys.argv[2]}

    elif command == "reload_carousel":
        if len(sys.argv) < 3:
            print("Usage: zmq_client.py reload_carousel <component_uid>")
            sys.exit(1)
        args = {"component_uid": sys.argv[2]}

    elif command == "get_carousel_stats":
        if len(sys.argv) < 3:
            print("Usage: zmq_client.py get_carousel_stats <component_uid>")
            sys.exit(1)
        args = {"component_uid": sys.argv[2]}

    elif command == "get_command_info":
        if len(sys.argv) < 3:
            print("Usage: zmq_client.py get_command_info <command_name>")
            sys.exit(1)
        args = {"command": sys.argv[2]}

    # Phase 2: Service parameter management
    elif command == "set_service_pty":
        if len(sys.argv) < 4:
            print("Usage: zmq_client.py set_service_pty <service_uid> <pty>")
            sys.exit(1)
        args = {
            "service_uid": sys.argv[2],
            "pty": int(sys.argv[3])
        }

    elif command == "set_service_language":
        if len(sys.argv) < 4:
            print("Usage: zmq_client.py set_service_language <service_uid> <language>")
            sys.exit(1)
        args = {
            "service_uid": sys.argv[2],
            "language": int(sys.argv[3])
        }

    elif command == "set_service_label":
        if len(sys.argv) < 4:
            print("Usage: zmq_client.py set_service_label <service_uid> <text> [short_text]")
            sys.exit(1)
        args = {
            "service_uid": sys.argv[2],
            "text": sys.argv[3]
        }
        if len(sys.argv) >= 5:
            args["short_text"] = sys.argv[4]

    # Connect to server
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:9000")

    print(f"Sending command: {command}")
    if args:
        print(f"Arguments: {args}")

    # Send command
    response = send_command(socket, command, args)

    # Print response
    print_response(response)

    # Cleanup
    socket.close()
    context.term()


if __name__ == "__main__":
    main()
