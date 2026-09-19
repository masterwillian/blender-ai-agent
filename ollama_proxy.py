from flask import Flask, request, Response
import requests
import json
import datetime
from pathlib import Path

app = Flask(__name__)

OLLAMA = "http://localhost:11434"
LOG_FILE = Path(__file__).parent / "opencode_ollama_log_v2.txt"

request_number = 0

# Regras extras para modelos locais pequenos.
AGENT_RULES = """
<local-model-compatibility>
IMPORTANT EXECUTION RULES:

1. Execute dependent tool operations sequentially.
2. NEVER call Read for a file in the same response that creates that file.
3. Wait for Write to return successfully before calling Read.
4. Wait for Read to return successfully before calling Edit.
5. Wait for Edit to return successfully before calling Read for verification.
6. Do not use Task/subagents for simple file creation, reading, editing, or verification.
7. Preserve file paths EXACTLY as supplied by the user or tool results.
8. Never translate, rewrite, normalize, or invent any part of a filesystem path.
9. For a dependent multi-step task, call ONE tool, wait for its result, then decide the next tool.
10. Do not respond to the user until every explicitly requested step is complete.

For a task such as:
Write -> Read -> Edit -> Read
you MUST execute exactly in that sequential order, waiting for each tool result.
</local-model-compatibility>
"""


def log(title, data):
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write("\n\n")
        f.write("=" * 100 + "\n")
        f.write(title + "\n")
        f.write("=" * 100 + "\n")

        if isinstance(data, (dict, list)):
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            f.write(str(data))

        f.write("\n")


def patch_request(body):
    if not isinstance(body, dict):
        return body

    # Não mexer em chamadas auxiliares do OpenCode,
    # como geração automática do título da conversa.
    messages = body.get("messages")

    if not isinstance(messages, list):
        return body

    is_main_agent = False

    for message in messages:
        if message.get("role") == "system":
            content = message.get("content", "")

            if (
                isinstance(content, str)
                and content.startswith("You are opencode")
            ):
                is_main_agent = True
                break

    if not is_main_agent:
        return body

    # Modelo rápido sem reasoning.
    body["reasoning_effort"] = "none"

    # Uma operação dependente por rodada.
    body["parallel_tool_calls"] = False

    SIMPLE_SYSTEM = r"""
You are an autonomous coding agent running on Windows.

Your job is to COMPLETE the user's entire requested task using the available tools.

CORE RULE:
A successful tool result completes only ONE step.
It does NOT mean the entire user task is complete.

DEPENDENT OPERATIONS:
Execute exactly ONE dependent tool per response.

Example:
Write -> wait
Read -> wait
Run -> wait
Edit -> wait
Run -> wait
Verify -> finish

FILES:
- Use Write to create files.
- Use Read to inspect files.
- Use Edit to modify existing files.
- Read a file before editing it.

EXECUTION:
- Use Bash to execute programs and commands.
- For Python files, use Bash with:
  python "absolute-path-to-file.py"
- Observe the actual Bash output before deciding whether execution succeeded.
- Never claim execution succeeded unless Bash actually returned success.

ERROR RECOVERY:
When a command fails:
1. inspect the actual error
2. identify its cause
3. edit the relevant file
4. execute the command again
5. verify the new result

ANTI-LOOP RULES:
- Never repeat the exact same tool call if its result has not changed.
- Never Read the same unchanged file repeatedly.
- A second identical Read is allowed only after an Edit or Write changed that file.
- If you need information that Read cannot provide, choose another appropriate tool.
- If execution is required, use Bash instead of repeatedly reading the file.
- If a tool fails, change your approach before calling another tool.
- Never perform the same unsuccessful action more than twice.

PATHS:
Copy filesystem paths EXACTLY.
Never translate, shorten, rewrite, or modify any portion of a path.

COMPLETION:
Track the original user request throughout the entire task.
Before responding, mentally check every requested step.

Only give a final response when:
- every requested action has been performed
- requested execution has actually occurred
- errors have been corrected
- requested verification has succeeded

If work remains, continue using tools.
Do not ask the user whether you should continue work they already requested.

BLENDER CONTROL:

A persistent Blender 5.2 instance is available.

To execute Python inside Blender, use Bash with exactly this interface:

python "D:\blender-ai\blender_tool.py" --code "<python code>"

The supplied Python code executes inside Blender and has access to bpy.

When the user asks you to create, modify, delete, inspect, or otherwise operate on a Blender scene:
- Use blender_tool.py through Bash.
- Do not merely write Blender Python code to a file unless the user specifically asks for a file.
- Actually execute the requested operation inside Blender.
- Always inspect the JSON response.
- "success": true means Blender executed the code successfully.
- "success": false means the operation failed.
- If it fails, inspect the returned error, correct the Python code, and execute it again.
- Never claim a Blender operation succeeded without receiving "success": true.
- Use the returned "result" field to verify important results.
- Keep Blender operations sequential.
"""

    for message in messages:
        if message.get("role") == "system":
            message["content"] = SIMPLE_SYSTEM
            break

    # For this experiment expose only the three tools
    # necessary for the task.
    allowed_tools = {"write", "read", "edit", "bash"}

    tools = body.get("tools")

    if isinstance(tools, list):
        body["tools"] = [
            tool
            for tool in tools
            if tool.get("function", {}).get("name") in allowed_tools
        ]

    return body


@app.route(
    "/",
    defaults={"path": ""},
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
@app.route(
    "/<path:path>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
def proxy(path):
    global request_number

    request_number += 1
    current_request = request_number

    url = f"{OLLAMA}/{path}"
    timestamp = datetime.datetime.now().isoformat()

    raw_data = request.get_data()

    try:
        body = request.get_json(silent=True)
    except Exception:
        body = None

    log(
        f"ORIGINAL REQUEST #{current_request} | {timestamp} | {request.method} /{path}",
        body if body is not None else raw_data.decode("utf-8", errors="replace"),
    )

    if body is not None:
        body = patch_request(body)

        log(
            f"PATCHED REQUEST #{current_request}",
            body,
        )

        outgoing_data = json.dumps(
            body,
            ensure_ascii=False,
        ).encode("utf-8")
    else:
        outgoing_data = raw_data

    headers = {
        key: value
        for key, value in request.headers
        if key.lower()
        not in {
            "host",
            "content-length",
            "connection",
            "accept-encoding",
        }
    }

    try:
        upstream = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=outgoing_data,
            params=request.args,
            stream=True,
            timeout=600,
        )

        response_headers = {
            key: value
            for key, value in upstream.headers.items()
            if key.lower()
            not in {
                "content-length",
                "transfer-encoding",
                "connection",
                "content-encoding",
            }
        }

        def generate():
            chunks = []

            for chunk in upstream.iter_content(chunk_size=None):
                if chunk:
                    chunks.append(chunk)
                    yield chunk

            raw = b"".join(chunks)

            log(
                f"RESPONSE #{current_request} | HTTP {upstream.status_code}",
                raw.decode("utf-8", errors="replace"),
            )

        return Response(
            generate(),
            status=upstream.status_code,
            headers=response_headers,
        )

    except Exception as e:
        log(
            f"PROXY ERROR #{current_request}",
            repr(e),
        )

        return {"error": str(e)}, 500


if __name__ == "__main__":
    print()
    print("OpenCode Compatibility Adapter v2")
    print("---------------------------------")
    print("OpenCode -> http://localhost:11435")
    print("Adapter  -> patches requests")
    print("Ollama   -> http://localhost:11434")
    print()
    print("Rules:")
    print("  parallel_tool_calls = false")
    print("  Task tool removed")
    print("  sequential tool rules injected")
    print("  filesystem paths must be preserved")
    print()
    print(f"Log -> {LOG_FILE}")
    print()
    print("CTRL+C para encerrar.")
    print()

    app.run(
        host="127.0.0.1",
        port=11435,
        threaded=True,
    )