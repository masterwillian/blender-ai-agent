import argparse
import json
import socket
import sys
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8765


def send_to_blender(code):
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
                "result": None,
                "error": "Blender Bridge returned no data.",
            }

        return json.loads(data.decode("utf-8"))

    except Exception as exc:
        return {
            "success": False,
            "result": None,
            "error": str(exc),
        }


def execute_file(file_path):
    path = Path(file_path)

    if not path.exists():
        return {
            "success": False,
            "result": None,
            "error": f"File not found: {path}",
        }

    try:
        code = path.read_text(encoding="utf-8")
    except Exception as exc:
        return {
            "success": False,
            "result": None,
            "error": f"Could not read file: {exc}",
        }

    return send_to_blender(code)


def inspect_scene():
    code = """
objects = []

for obj in bpy.context.scene.objects:
    objects.append({
        "name": obj.name,
        "type": obj.type,
        "location": [round(float(v), 6) for v in obj.location],
        "rotation": [round(float(v), 6) for v in obj.rotation_euler],
        "scale": [round(float(v), 6) for v in obj.scale],
        "dimensions": [round(float(v), 6) for v in obj.dimensions],
        "collections": [collection.name for collection in obj.users_collection],
        "visible": bool(obj.visible_get())
    })

result = {
    "object_count": len(objects),
    "objects": objects
}
"""

    return send_to_blender(code)


def inspect_objects(names):
    names_json = json.dumps(names)

    code = f"""
import json

requested_names = json.loads({json.dumps(names_json)})

objects = {{}}

for name in requested_names:
    obj = bpy.data.objects.get(name)

    if obj is None:
        objects[name] = {{
            "exists": False
        }}
        continue

    objects[name] = {{
        "exists": True,
        "name": obj.name,
        "type": obj.type,
        "location": [round(float(v), 6) for v in obj.location],
        "rotation": [round(float(v), 6) for v in obj.rotation_euler],
        "scale": [round(float(v), 6) for v in obj.scale],
        "dimensions": [round(float(v), 6) for v in obj.dimensions],
        "collections": [collection.name for collection in obj.users_collection],
        "visible": bool(obj.visible_get())
    }}

result = {{
    "requested": requested_names,
    "objects": objects
}}
"""

    return send_to_blender(code)


def print_response(response):
    print(
        json.dumps(
            response,
            indent=2,
            ensure_ascii=False,
        )
    )

    if not response.get("success"):
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Control the persistent Blender Bridge."
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--code",
        help="Execute short Python code inside Blender.",
    )

    group.add_argument(
        "--file",
        help="Execute a Python file inside Blender.",
    )

    group.add_argument(
        "--inspect",
        action="store_true",
        help="Inspect the complete Blender scene.",
    )

    group.add_argument(
        "--inspect-objects",
        nargs="+",
        metavar="NAME",
        help="Inspect only the specified Blender objects.",
    )

    args = parser.parse_args()

    if args.code is not None:
        response = send_to_blender(args.code)

    elif args.file is not None:
        response = execute_file(args.file)

    elif args.inspect:
        response = inspect_scene()

    elif args.inspect_objects is not None:
        response = inspect_objects(args.inspect_objects)

    else:
        parser.error("No operation selected.")

    print_response(response)


if __name__ == "__main__":
    main()