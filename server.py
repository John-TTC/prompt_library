from flask import Flask, render_template, request, jsonify
import json
import os

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

@app.route("/webhook/agentmail", methods=["POST"])
def agentmail_webhook():
    payload = request.get_json(silent=True) or {}
    print("AgentMail webhook received:", payload)
    return jsonify({"ok": True})
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)