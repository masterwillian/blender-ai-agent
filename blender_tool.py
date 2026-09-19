import argparse
import json
import socket
import sys

HOST = "127.0.0.1"
PORT = 8765


def execute_blender_python(code):
    command = {
        "id": 1,
        "code": code,
    }

    try:
        with socket.create_connection((HOST, PORT), timeout=10) as sock:
            sock.sendall(
                (json.dumps(command) + "\n").encode("utf-8")
            )

            data = b""

            while b"\n" not in data:
                chunk = sock.recv(65536)

                if not chunk:
                    break

                data += chunk

        if not data:
            return {
                "success": False,
                "error": "Blender Bridge returned no data.",
            }

        return json.loads(data.decode("utf-8"))

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--code",
        required=True,
        help="Python code to execute inside Blender",
    )

    args = parser.parse_args()

    response = execute_blender_python(args.code)

    print(
        json.dumps(
            response,
            indent=2,
            ensure_ascii=False,
        )
    )

    if not response.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()