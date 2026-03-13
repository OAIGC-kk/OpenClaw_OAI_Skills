#!/usr/bin/env python3
"""
OAI API Client for OpenClaw.

Supports image, video, audio generation via OAI API.

Modes:
  --check                          Check API key status
  --list [--type T] [--task T]     List available apps
  --info APPID                     Show app details
  --app APPID --prompt "..." ...   Execute a generation task
  --task TASK --prompt "..."       Auto-select best app for task
  --query TASKID                   Query task status
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BASE_URL = "https://oaigc.cn/api"
TASK_SUBMIT_URL = f"{BASE_URL}/v1/task/submit"
TASK_QUERY_URL = f"{BASE_URL}/v1/task/query"
MODEL_LIST_URL = f"{BASE_URL}/v1/model/list"
ACCOUNT_INFO_URL = f"{BASE_URL}/v1/user/account-info"

MAX_POLL_SECONDS = 1500  # 25 minutes
POLL_INTERVAL = 5

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CAPABILITIES_PATH = DATA_DIR / "capabilities.json"


# ---------------------------------------------------------------------------
# Capabilities catalog
# ---------------------------------------------------------------------------

_capabilities_cache = None


def load_capabilities() -> dict:
    global _capabilities_cache
    if _capabilities_cache is not None:
        return _capabilities_cache
    if not CAPABILITIES_PATH.exists():
        print(f"Error: capabilities.json not found at {CAPABILITIES_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CAPABILITIES_PATH, encoding="utf-8") as f:
        _capabilities_cache = json.load(f)
    return _capabilities_cache


def find_app(app_id: str) -> dict | None:
    caps = load_capabilities()
    for ep in caps["endpoints"]:
        if ep["appId"] == app_id:
            return ep
    return None


def find_best_for_task(task: str) -> dict | None:
    caps = load_capabilities()
    matches = [e for e in caps["endpoints"] if e["task"] == task]
    if not matches:
        return None
    return min(matches, key=lambda x: x["popularity"])


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------

def read_key_from_openclaw_config() -> str | None:
    cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    if not cfg_path.exists():
        return None
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    entry = cfg.get("skills", {}).get("entries", {}).get("oaigc", {})
    api_key = entry.get("apiKey")
    if isinstance(api_key, str) and api_key.strip():
        return api_key.strip()
    env_val = entry.get("env", {}).get("OAI_API_KEY")
    if isinstance(env_val, str) and env_val.strip():
        return env_val.strip()
    return None


def resolve_api_key(provided_key: str | None) -> str | None:
    """Resolve API key without exiting. Returns None if not found."""
    if provided_key:
        normalized = provided_key.strip()
        placeholders = {
            "your_api_key_here", "<your_api_key>",
            "YOUR_API_KEY", "OAI_API_KEY",
        }
        if normalized and normalized not in placeholders:
            return normalized

    env_key = os.environ.get("OAI_API_KEY", "").strip()
    if env_key:
        return env_key

    return read_key_from_openclaw_config()


def get_key_source(provided_key: str | None) -> str:
    if provided_key:
        normalized = provided_key.strip()
        placeholders = {"your_api_key_here", "<your_api_key>", "YOUR_API_KEY", "OAI_API_KEY"}
        if normalized and normalized not in placeholders:
            return "cli"
    env_key = os.environ.get("OAI_API_KEY", "").strip()
    if env_key:
        return "env"
    cfg_key = read_key_from_openclaw_config()
    if cfg_key:
        return "config"
    return "none"


def require_api_key(provided_key: str | None) -> str:
    key = resolve_api_key(provided_key)
    if key:
        return key
    result = {
        "error": "NO_API_KEY",
        "message": "No API key configured",
        "steps": [
            "1. 登录平台后，点击头像",
            "2. 选择个人中心",
            "3. 选择API令牌获取密钥",
            "4. 将密钥发送给我，或添加到 ~/.openclaw/openclaw.json: skills.entries.oaigc.apiKey",
        ],
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(1)


# ---------------------------------------------------------------------------
# HTTP helpers (curl-based, stdlib only)
# ---------------------------------------------------------------------------

def curl_get(url: str, headers: dict, timeout: int = 60) -> subprocess.CompletedProcess:
    cmd = ["curl", "-s", "-S", "--fail-with-body", "-X", "GET", url,
           "--max-time", str(timeout)]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')


def curl_post_json(url: str, payload: dict, headers: dict, timeout: int = 60) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)
        tmp_path = f.name
    try:
        cmd = ["curl", "-s", "-S", "--fail-with-body", "-X", "POST", url,
               "--max-time", str(timeout), "-d", f"@{tmp_path}"]
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
        return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    finally:
        os.unlink(tmp_path)


def api_get(api_key: str, url: str, timeout: int = 60) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    result = curl_get(url, headers, timeout)

    if result.returncode != 0:
        error_body = result.stdout or result.stderr
        try:
            err = json.loads(error_body)
            code = err.get("code", "")
            msg = err.get("msg", error_body)
        except (json.JSONDecodeError, TypeError):
            code = ""
            msg = error_body

        code_str = str(code).lower()
        msg_lower = msg.lower() if isinstance(msg, str) else ""

        if any(k in code_str or k in msg_lower for k in ["auth", "401", "403", "token", "key"]):
            error_result = {
                "error": "AUTH_FAILED",
                "message": f"API authentication failed: {msg}",
            }
        else:
            error_result = {
                "error": "API_ERROR",
                "message": f"API request failed: {msg}",
                "http_stderr": result.stderr[:500] if result.stderr else "",
            }
        print(json.dumps(error_result, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(json.dumps({
            "error": "API_ERROR",
            "message": f"Invalid JSON response: {result.stdout[:500]}",
        }, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


def api_post(api_key: str, url: str, payload: dict, timeout: int = 60) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    result = curl_post_json(url, payload, headers, timeout)

    if result.returncode != 0:
        error_body = result.stdout or result.stderr
        try:
            err = json.loads(error_body)
            code = err.get("code", "")
            msg = err.get("msg", error_body)
        except (json.JSONDecodeError, TypeError):
            code = ""
            msg = error_body

        code_str = str(code).lower()
        msg_lower = msg.lower() if isinstance(msg, str) else ""

        if any(k in code_str or k in msg_lower for k in ["auth", "401", "403", "token", "key"]):
            error_result = {
                "error": "AUTH_FAILED",
                "message": f"API authentication failed: {msg}",
            }
        elif any(k in code_str or k in msg_lower for k in ["balance", "insufficient", "余额", "credit"]):
            error_result = {
                "error": "INSUFFICIENT_BALANCE",
                "message": f"Insufficient balance: {msg}",
            }
        else:
            error_result = {
                "error": "API_ERROR",
                "message": f"API request failed: {msg}",
                "http_stderr": result.stderr[:500] if result.stderr else "",
            }
        print(json.dumps(error_result, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(json.dumps({
            "error": "API_ERROR",
            "message": f"Invalid JSON response: {result.stdout[:500]}",
        }, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# --check: account health check
# ---------------------------------------------------------------------------

def cmd_check(api_key_arg: str | None):
    key = resolve_api_key(api_key_arg)
    if not key:
        print(json.dumps({
            "status": "no_key",
            "message": "No API key configured",
            "steps": [
                "1. 登录平台后，点击头像",
                "2. 选择个人中心",
                "3. 选择API令牌获取密钥",
                "4. 将密钥发送给我，或添加到 ~/.openclaw/openclaw.json: skills.entries.oaigc.apiKey",
            ],
        }, ensure_ascii=False))
        return

    key_prefix = key[:4] + "****"
    key_source = get_key_source(api_key_arg)

    # Try to get model list as a way to verify the key
    try:
        resp = api_get(key, MODEL_LIST_URL, timeout=15)
        if resp.get("code") == 200:
            models = resp.get("data", {}).get("models", [])
            print(json.dumps({
                "status": "ready",
                "key_prefix": key_prefix,
                "key_source": key_source,
                "models_count": len(models),
            }, ensure_ascii=False))
        else:
            print(json.dumps({
                "status": "invalid_key",
                "key_prefix": key_prefix,
                "key_source": key_source,
                "message": resp.get("message", "API key verification failed"),
            }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "key_prefix": key_prefix,
            "message": f"Connection error: {str(e)}",
        }, ensure_ascii=False))


def cmd_balance(api_key_arg: str | None):
    """Query account balance and user info."""
    api_key = require_api_key(api_key_arg)
    
    resp = api_get(api_key, ACCOUNT_INFO_URL, timeout=15)
    
    if resp.get("code") != 200:
        print(json.dumps({
            "error": "API_ERROR",
            "message": resp.get("message", "Failed to get account info"),
        }, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    
    data = resp.get("data", {})
    point = data.get("point", 0)
    nickname = data.get("nickname", "未知用户")
    vip_grade = data.get("vipGrade", "Free")
    has_no_watermark = data.get("hasNoWatermarkPerm", False)
    
    # Output in a format that's easy to parse
    print(f"BALANCE:{point}")
    print(f"NICKNAME:{nickname}")
    print(f"VIP:{vip_grade}")
    print(f"NO_WATERMARK:{has_no_watermark}")


# ---------------------------------------------------------------------------
# --list / --info: capability discovery
# ---------------------------------------------------------------------------

def cmd_list(type_filter: str | None, task_filter: str | None):
    caps = load_capabilities()
    endpoints = caps["endpoints"]

    if type_filter:
        endpoints = [e for e in endpoints if e["output_type"] == type_filter]
    if task_filter:
        endpoints = [e for e in endpoints if e["task"] == task_filter]

    rows = []
    for e in endpoints:
        name = e["name_cn"] or e["name_en"] or e["appId"]
        tags = ",".join(e["tags"]) if e["tags"] else ""
        pop = e["popularity"] if e["popularity"] < 99 else "-"
        rows.append(f"  [{e['output_type']:6s}] {e['task']:20s} rank={str(pop):3s} {e['appId']:40s} {name}")

    print(f"Total: {len(rows)} apps")
    if type_filter:
        print(f"Filter: type={type_filter}")
    if task_filter:
        print(f"Filter: task={task_filter}")
    print()
    for r in rows:
        print(r)


def cmd_info(app_id: str):
    app = find_app(app_id)
    if not app:
        print(f"Error: app '{app_id}' not found", file=sys.stderr)
        print("Use --list to see available apps.", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(app, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Task execution: submit -> poll -> download
# ---------------------------------------------------------------------------

def poll_task(api_key: str, task_id: str) -> tuple[dict, int]:
    """Poll task until completion. Returns (response, elapsed_seconds)."""
    url = f"{TASK_QUERY_URL}/{task_id}"
    print(f"Task ID: {task_id}")
    print("Waiting for result", end="", flush=True)

    elapsed = 0
    consecutive_failures = 0
    while elapsed < MAX_POLL_SECONDS:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        try:
            resp = api_get(api_key, url, timeout=30)
            consecutive_failures = 0
            status = resp.get("data", {}).get("status", "UNKNOWN")

            if status == "success":
                print(f" done ({elapsed}s)")
                return resp, elapsed
            if status == "failed":
                error_msg = resp.get("data", {}).get("error", "Unknown error")
                print(json.dumps({
                    "error": "TASK_FAILED",
                    "message": f"Task failed: {error_msg}",
                }, ensure_ascii=False), file=sys.stderr)
                sys.exit(1)

            print(".", end="", flush=True)
        except Exception as e:
            consecutive_failures += 1
            print("x", end="", flush=True)
            if consecutive_failures >= 5:
                print(f"\nToo many consecutive poll failures", file=sys.stderr)
                sys.exit(1)

    print(f"\nTimeout after {MAX_POLL_SECONDS}s", file=sys.stderr)
    sys.exit(1)


def download_file(url: str, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = ["curl", "-s", "-S", "-L", "-o", output_path, "--max-time", "300", url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Download failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return str(Path(output_path).resolve())


def build_payload(app_def: dict, args) -> dict:
    """Build API payload from app definition and CLI args."""
    # Check if this is a special endpoint with direct params (like banana_generate)
    is_direct_params = app_def.get("is_special_endpoint", False)
    
    if is_direct_params:
        # Direct params format (no appId/parameter wrapper)
        payload = {}
    else:
        # Standard format with appId and parameter wrapper
        payload = {"appId": app_def["appId"], "parameter": {}}

    # Collect --param key=value pairs
    extra_params = {}
    if args.param:
        for p in args.param:
            if "=" not in p:
                print(f"Error: invalid --param format '{p}', expected key=value", file=sys.stderr)
                sys.exit(1)
            k, v = p.split("=", 1)
            extra_params[k] = v

    # --prompt maps to prompt parameter
    if args.prompt:
        if is_direct_params:
            payload["prompt"] = args.prompt
        else:
            payload["parameter"]["prompt"] = args.prompt

    # --image maps to image parameter
    if args.image:
        if is_direct_params:
            payload["image"] = args.image
        else:
            payload["parameter"]["image"] = args.image

    # --video maps to video parameter
    if args.video:
        if is_direct_params:
            payload["video"] = args.video
        else:
            payload["parameter"]["video"] = args.video

    # --audio maps to audio parameter
    if args.audio:
        if is_direct_params:
            payload["audio"] = args.audio
        else:
            payload["parameter"]["audio"] = args.audio

    # Apply extra --param key=value
    for k, v in extra_params.items():
        param_def = next((p for p in app_def["params"] if p["key"] == k), None)
        converted_val = v
        if param_def and param_def["type"] == "BOOLEAN":
            converted_val = v.lower() in ("true", "1", "yes")
        elif param_def and param_def["type"] in ("INT", "FLOAT"):
            try:
                converted_val = int(v) if param_def["type"] == "INT" else float(v)
            except ValueError:
                converted_val = v
        
        if is_direct_params:
            payload[k] = converted_val
        else:
            payload["parameter"][k] = converted_val

    # Fill defaults for required params not yet set
    for param in app_def["params"]:
        target = payload if is_direct_params else payload["parameter"]
        if param["key"] not in target and param.get("required") and "default" in param:
            target[param["key"]] = param["default"]

    # Validate required parameters
    missing_required = []
    for param in app_def["params"]:
        if param.get("required"):
            target = payload if is_direct_params else payload["parameter"]
            if param["key"] not in target:
                missing_required.append(param["key"])
    
    if missing_required:
        print(f"Error: missing required parameter(s): {', '.join(missing_required)}", file=sys.stderr)
        print(f"Use --param {missing_required[0]}=value to provide it", file=sys.stderr)
        sys.exit(1)

    return payload


def get_special_endpoint_url(app_id: str) -> str | None:
    """Check if app uses a special endpoint URL."""
    caps = load_capabilities()
    special = caps.get("special_endpoints", {})
    
    # Check banana_generate special endpoint
    banana_config = special.get("banana_generate", {})
    if banana_config and app_id in ["banana", "banana2", "banana-pro"]:
        return f"{BASE_URL}{banana_config['path']}"
    
    return None


def cmd_execute(args):
    """Execute a generation task."""
    api_key = require_api_key(args.api_key)

    # Resolve app
    if args.app:
        app_def = find_app(args.app)
        if not app_def:
            print(f"Error: app '{args.app}' not found", file=sys.stderr)
            print("Use --list to see available apps.", file=sys.stderr)
            sys.exit(1)
    elif args.task:
        app_def = find_best_for_task(args.task)
        if not app_def:
            print(f"Error: no app found for task '{args.task}'", file=sys.stderr)
            print("Use --list to see available tasks.", file=sys.stderr)
            sys.exit(1)
        print(f"Auto-selected: {app_def['appId']} ({app_def.get('name_cn', '')})", file=sys.stderr)
    else:
        print("Error: --app or --task is required", file=sys.stderr)
        sys.exit(1)

    payload = build_payload(app_def, args)

    # Check for special endpoint URL
    submit_url = get_special_endpoint_url(app_def["appId"])
    if not submit_url:
        submit_url = TASK_SUBMIT_URL

    # Debug output
    print(f"Submitting {app_def['task']} to {app_def['appId']}...", file=sys.stderr)
    print(f"URL: {submit_url}", file=sys.stderr)
    print(f"Payload: {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr)
    
    resp = api_post(api_key, submit_url, payload)

    if resp.get("code") != 200:
        print(f"Error: {resp.get('message', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)

    # Check if response contains direct imageUrl (like banana endpoint)
    result_url = resp.get("data", {}).get("imageUrl")
    if result_url:
        # Direct response with imageUrl (no polling needed)
        output_path = args.output
        if not output_path:
            ext = _guess_ext(app_def["output_type"])
            output_path = f"/tmp/openclaw/oai-output/result.{ext}"

        print(f"Downloading result to local file...", file=sys.stderr)
        full_path = download_file(result_url, output_path)
        print(f"OUTPUT_FILE:{full_path}")
        print(f"WAIT_TIME:0s")
        return

    # Standard task-based response (requires polling)
    task_id = resp.get("data", {}).get("taskId")
    if not task_id:
        print(f"Error: no taskId in response: {json.dumps(resp, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)

    final, elapsed = poll_task(api_key, task_id)
    result_url = final.get("data", {}).get("result")

    if not result_url:
        print("Error: no result URL in response", file=sys.stderr)
        sys.exit(1)

    output_path = args.output
    if not output_path:
        ext = _guess_ext(app_def["output_type"])
        output_path = f"/tmp/openclaw/oai-output/result.{ext}"

    print(f"Downloading result to local file...", file=sys.stderr)
    full_path = download_file(result_url, output_path)
    print(f"OUTPUT_FILE:{full_path}")

    # Extract cost and duration from response if available
    usage = final.get("data", {}).get("usage", {}) or {}
    consume_money = usage.get("consumeMoney") or usage.get("cost")
    task_cost_time = usage.get("duration") or usage.get("taskCostTime")

    if consume_money is not None:
        print(f"COST:¥{consume_money}")
    if task_cost_time and str(task_cost_time) != "0":
        print(f"DURATION:{task_cost_time}s")
    
    # Report wait time (polling elapsed time)
    print(f"WAIT_TIME:{elapsed}s")


def _guess_ext(output_type: str) -> str:
    return {"image": "png", "video": "mp4", "audio": "mp3", "3d": "glb", "string": "txt"}.get(output_type, "bin")


# ---------------------------------------------------------------------------
# --query: task status query
# ---------------------------------------------------------------------------

def cmd_query(args):
    """Query task status."""
    api_key = require_api_key(args.api_key)

    url = f"{TASK_QUERY_URL}/{args.task_id}"
    resp = api_get(api_key, url)

    if resp.get("code") != 200:
        print(f"Error: {resp.get('message', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)

    data = resp.get("data", {})
    status = data.get("status", "unknown")
    result = data.get("result", "")

    if status == "success" and result:
        if args.output:
            full_path = download_file(result, args.output)
            print(f"OUTPUT_FILE:{full_path}")
        else:
            print(f"Status: {status}")
            print(f"Result: {result}")
        
        # Report cost if available
        usage = data.get("usage", {}) or {}
        consume_money = usage.get("consumeMoney") or usage.get("cost")
        task_cost_time = usage.get("duration") or usage.get("taskCostTime")
        if consume_money is not None:
            print(f"COST:¥{consume_money}")
        if task_cost_time and str(task_cost_time) != "0":
            print(f"DURATION:{task_cost_time}s")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="OAI API client for OpenClaw",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Modes:
  --check                           Check API key status
  --balance                         Query account balance (O币余额)
  --list [--type T] [--task T]      List available apps
  --info APPID                      Show app parameter details
  --app APPID [options]             Execute with specific app
  --task TASK [options]             Execute with auto-selected best app
  --query TASKID                    Query task status

Examples:
  python3 oaigc.py --check
  python3 oaigc.py --balance
  python3 oaigc.py --list --type image
  python3 oaigc.py --info z-imagewenshengt
  python3 oaigc.py --app z-imagewenshengt --prompt "a cute dog" --output /tmp/dog.png
  python3 oaigc.py --task text-to-image --prompt "a cute dog" --output /tmp/dog.png
  python3 oaigc.py --query <taskId> --output /tmp/result.png
""",
    )

    # Mode flags
    parser.add_argument("--check", action="store_true", help="Check API key status")
    parser.add_argument("--balance", action="store_true", help="Query account balance")
    parser.add_argument("--list", action="store_true", help="List available apps")
    parser.add_argument("--info", metavar="APPID", help="Show details for an app")
    parser.add_argument("--query", metavar="TASKID", dest="query_task", help="Query task status")

    # Execution params
    parser.add_argument("--app", "-a", help="App ID to use")
    parser.add_argument("--task", "-t", help="Task type (auto-selects best app)")
    parser.add_argument("--prompt", "-p", help="Text prompt")
    parser.add_argument("--image", "-i", help="Input image URL")
    parser.add_argument("--video", help="Input video URL")
    parser.add_argument("--audio", help="Input audio URL")
    parser.add_argument("--param", action="append", help="Extra parameter as key=value (repeatable)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--api-key", "-k", help="API key (optional, resolved from config)")

    # Filters for --list
    parser.add_argument("--type", dest="type_filter", help="Filter by output type (image/video/audio/string)")

    args = parser.parse_args()

    if args.check:
        cmd_check(args.api_key)
    elif args.balance:
        cmd_balance(args.api_key)
    elif args.list:
        cmd_list(args.type_filter, args.task)
    elif args.info:
        cmd_info(args.info)
    elif args.query_task:
        args.task_id = args.query_task
        cmd_query(args)
    elif args.app or args.task:
        cmd_execute(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
