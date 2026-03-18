from flask import Flask, render_template, request, jsonify
import json
import os
import re

import agent_service

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "launch-config.ini")


def read_simple_config(path):
    config = {}
    if not os.path.exists(path):
        return config

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            config[key.strip().lower()] = value.strip()
    return config


def resolve_data_file():
    config = read_simple_config(CONFIG_FILE)
    configured = config.get("data_file", "")
    if configured:
        if os.path.isabs(configured):
            return configured
        return os.path.join(BASE_DIR, configured)

    preferred = os.path.join(BASE_DIR, "prompt_library.json")
    legacy = os.path.join(BASE_DIR, "contexts.json")
    if os.path.exists(preferred):
        return preferred
    if os.path.exists(legacy):
        return legacy
    return preferred


DATA_FILE = resolve_data_file()


def resolve_agents_root():
    config = read_simple_config(CONFIG_FILE)
    configured = config.get("agents_root", "")
    if configured:
        if os.path.isabs(configured):
            return configured
        return os.path.join(BASE_DIR, configured)
    return os.path.join(BASE_DIR, "agents")


AGENTS_ROOT = resolve_agents_root()


def slugify_user_id(label):
    base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return base or "user"


def resolve_configured_users():
    config = read_simple_config(CONFIG_FILE)
    raw = config.get("users", "")
    tokens = [part.strip() for part in raw.split(",") if part.strip()]

    if not tokens:
        return [{"id": "default", "label": "Default"}]

    seen = {}
    users = []
    for label in tokens:
        base_id = slugify_user_id(label)
        next_num = seen.get(base_id, 0) + 1
        seen[base_id] = next_num
        user_id = base_id if next_num == 1 else f"{base_id}-{next_num}"
        users.append({"id": user_id, "label": label})
    return users

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.route("/")
def index():
    return render_template("prompt_library.html")

@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(load_data())

@app.route("/data", methods=["POST"])
def post_data():
    data = request.get_json(force=True)
    save_data(data)
    return jsonify({"ok": True})


@app.route("/app-config", methods=["GET"])
def get_app_config():
    return jsonify({"users": resolve_configured_users()})


@app.route("/agents", methods=["GET"])
def get_agents():
    user = request.args.get("user", "").strip()
    if not user:
        return jsonify({"error": "Missing user"}), 400
    try:
        items = agent_service.list_agents(AGENTS_ROOT, user)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify({"agents": items})


@app.route("/agents/groups", methods=["GET"])
def get_agent_groups():
    user = request.args.get("user", "").strip()
    if not user:
        return jsonify({"error": "Missing user"}), 400
    try:
        groups = agent_service.list_agent_groups(AGENTS_ROOT, user)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify({"groups": groups})


@app.route("/agents/groups/create", methods=["POST"])
def create_agent_group():
    payload = request.get_json(force=True) or {}
    user = str(payload.get("user", "")).strip()
    group = str(payload.get("group", "")).strip()
    label = str(payload.get("label", "")).strip()
    if not user or not group:
        return jsonify({"error": "Missing user/group"}), 400
    try:
        result = agent_service.create_agent_group(
            AGENTS_ROOT,
            user=user,
            group=group,
            label=label,
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify({"ok": True, "group": result.get("group")})


@app.route("/agents/groups/reorder", methods=["POST"])
def reorder_agent_groups():
    payload = request.get_json(force=True) or {}
    user = str(payload.get("user", "")).strip()
    order = payload.get("order", [])
    if not user:
        return jsonify({"error": "Missing user"}), 400
    if not isinstance(order, list):
        return jsonify({"error": "Invalid order"}), 400
    try:
        result = agent_service.reorder_agent_groups(
            AGENTS_ROOT,
            user=user,
            ordered_group_keys=order,
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify(result)


@app.route("/agents/groups/delete", methods=["POST"])
def delete_agent_group():
    payload = request.get_json(force=True) or {}
    user = str(payload.get("user", "")).strip()
    group = str(payload.get("group", "")).strip()
    if not user or not group:
        return jsonify({"error": "Missing user/group"}), 400
    try:
        result = agent_service.delete_agent_group(AGENTS_ROOT, user=user, group=group)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except FileNotFoundError as err:
        return jsonify({"error": str(err)}), 404
    except FileExistsError as err:
        return jsonify({"error": str(err)}), 409
    return jsonify(result)


@app.route("/agents/load", methods=["GET"])
def load_agent():
    user = request.args.get("user", "").strip()
    group = request.args.get("group", "").strip()
    agent_slug = request.args.get("agent", "").strip()
    if not user or not group or not agent_slug:
        return jsonify({"error": "Missing user/group/agent"}), 400
    try:
        payload = agent_service.load_agent(AGENTS_ROOT, user, group, agent_slug)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except FileNotFoundError as err:
        return jsonify({"error": str(err)}), 404
    return jsonify(payload)


@app.route("/agents/create", methods=["POST"])
def create_agent():
    payload = request.get_json(force=True) or {}
    user = str(payload.get("user", "")).strip()
    group = str(payload.get("group", "")).strip()
    agent_slug = str(payload.get("agent", "")).strip()
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", ""))
    section_order = payload.get("section_order")
    construct_defaults = payload.get("construct_defaults")

    if not user or not group or not agent_slug or not title:
        return jsonify({"error": "Missing user/group/agent/title"}), 400
    try:
        created = agent_service.create_agent(
            AGENTS_ROOT,
            user=user,
            group=group,
            agent_slug=agent_slug,
            title=title,
            description=description,
            section_order=section_order,
            construct_defaults=construct_defaults,
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except FileExistsError as err:
        return jsonify({"error": str(err)}), 409
    return jsonify({"ok": True, "agent": created})


@app.route("/agents/section/save", methods=["POST"])
def save_agent_section():
    payload = request.get_json(force=True) or {}
    user = str(payload.get("user", "")).strip()
    group = str(payload.get("group", "")).strip()
    agent_slug = str(payload.get("agent", "")).strip()
    section = str(payload.get("section", "")).strip()
    content = payload.get("content", "")
    if not user or not group or not agent_slug or not section:
        return jsonify({"error": "Missing user/group/agent/section"}), 400
    try:
        result = agent_service.save_section(
            AGENTS_ROOT,
            user=user,
            group=group,
            agent_slug=agent_slug,
            section_name=section,
            content=content,
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except FileNotFoundError as err:
        return jsonify({"error": str(err)}), 404
    return jsonify(result)


@app.route("/agents/section/add", methods=["POST"])
def add_agent_section():
    payload = request.get_json(force=True) or {}
    user = str(payload.get("user", "")).strip()
    group = str(payload.get("group", "")).strip()
    agent_slug = str(payload.get("agent", "")).strip()
    section = str(payload.get("section", "")).strip()
    if not user or not group or not agent_slug or not section:
        return jsonify({"error": "Missing user/group/agent/section"}), 400
    try:
        result = agent_service.add_section(
            AGENTS_ROOT,
            user=user,
            group=group,
            agent_slug=agent_slug,
            section_name=section,
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except FileNotFoundError as err:
        return jsonify({"error": str(err)}), 404
    return jsonify(result)


@app.route("/agents/delete", methods=["POST"])
def delete_agent():
    payload = request.get_json(force=True) or {}
    user = str(payload.get("user", "")).strip()
    group = str(payload.get("group", "")).strip()
    agent_slug = str(payload.get("agent", "")).strip()
    if not user or not group or not agent_slug:
        return jsonify({"error": "Missing user/group/agent"}), 400
    try:
        result = agent_service.delete_agent(
            AGENTS_ROOT,
            user=user,
            group=group,
            agent_slug=agent_slug,
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except FileNotFoundError as err:
        return jsonify({"error": str(err)}), 404
    return jsonify(result)


@app.route("/agents/move", methods=["POST"])
def move_agent():
    payload = request.get_json(force=True) or {}
    user = str(payload.get("user", "")).strip()
    from_group = str(payload.get("from_group", "")).strip()
    to_group = str(payload.get("to_group", "")).strip()
    agent_slug = str(payload.get("agent", "")).strip()
    if not user or not from_group or not to_group or not agent_slug:
        return jsonify({"error": "Missing user/from_group/to_group/agent"}), 400
    try:
        result = agent_service.move_agent_to_group(
            AGENTS_ROOT,
            user=user,
            from_group=from_group,
            to_group=to_group,
            agent_slug=agent_slug,
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except FileNotFoundError as err:
        return jsonify({"error": str(err)}), 404
    except FileExistsError as err:
        return jsonify({"error": str(err)}), 409
    return jsonify(result)

@app.route("/webhook/agentmail", methods=["POST"])
def agentmail_webhook():
    payload = request.get_json(silent=True) or {}
    print("AgentMail webhook received:", payload)
    return jsonify({"ok": True})
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)