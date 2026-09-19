import bpy
import json
import queue
import socket
import threading
import traceback

HOST = "127.0.0.1"
PORT = 8765

command_queue = queue.Queue()


def execute_command(command):
    request_id = command.get("id")
    code = command.get("code", "")

    result = {
        "id": request_id,
        "success": False,
        "result": None,
        "error": None,
    }

    try:
        # Namespace disponibilizado para o código recebido.
        namespace = {
            "bpy": bpy,
        }

        exec(code, namespace, namespace)

        result["success"] = True
        result["result"] = namespace.get("result")

    except Exception:
        result["error"] = traceback.format_exc()

    return result


def process_queue():
    try:
        while True:
            item = command_queue.get_nowait()

            command = item["command"]
            response_queue = item["response_queue"]

            response = execute_command(command)
            response_queue.put(response)

    except queue.Empty:
        pass

    return 0.05


def handle_client(conn):
    try:
        data = b""

        while b"\n" not in data:
            chunk = conn.recv(65536)

            if not chunk:
                return

            data += chunk

        command = json.loads(data.decode("utf-8"))

        response_queue = queue.Queue()

        command_queue.put({
            "command": command,
            "response_queue": response_queue,
        })

        response = response_queue.get(timeout=60)

        payload = json.dumps(
            response,
            ensure_ascii=False,
            default=str
        ) + "\n"

        conn.sendall(payload.encode("utf-8"))

    except Exception:
        error = {
            "success": False,
            "error": traceback.format_exc(),
        }

        conn.sendall(
            (json.dumps(error) + "\n").encode("utf-8")
        )

    finally:
        conn.close()


def server_loop():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        server.bind((HOST, PORT))
        server.listen(5)

        print(f"[BLENDER BRIDGE] Listening on {HOST}:{PORT}")

        while True:
            conn, address = server.accept()

            print(f"[BLENDER BRIDGE] Connection from {address}")

            threading.Thread(
                target=handle_client,
                args=(conn,),
                daemon=True,
            ).start()


def start_bridge():
    print("[BLENDER BRIDGE] Starting...")

    bpy.app.timers.register(
        process_queue,
        persistent=True,
    )

    threading.Thread(
        target=server_loop,
        daemon=True,
    ).start()

    print("[BLENDER BRIDGE] Ready")


start_bridge()