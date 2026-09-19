import json
import socket

HOST = "127.0.0.1"
PORT = 8765

command = {
    "id": 1,
    "code": """
bpy.ops.mesh.primitive_cube_add(location=(3, 0, 1))
obj = bpy.context.active_object
obj.name = "BridgeCube"

result = {
    "name": obj.name,
    "location": list(obj.location)
}
"""
}

with socket.create_connection((HOST, PORT), timeout=10) as sock:
    payload = json.dumps(command) + "\n"

    sock.sendall(payload.encode("utf-8"))

    data = b""

    while b"\n" not in data:
        chunk = sock.recv(65536)

        if not chunk:
            break

        data += chunk

response = json.loads(data.decode("utf-8"))

print(json.dumps(response, indent=2))