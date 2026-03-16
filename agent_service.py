import json
import re
import shutil
from pathlib import Path


DEFAULT_SECTION_ORDER = ["role", "rules", "process", "output"]


def _slugify(value):
    base = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return base


def _normalize_segment(value, label):
    normalized = _slugify(value)
    if not normalized:
        raise ValueError(f"Invalid {label}")
    return normalized


def _ensure_within_root(root, candidate):
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve()
    if root_resolved == candidate_resolved:
        return
    if root_resolved not in candidate_resolved.parents:
        raise ValueError("Resolved path is outside agents root")


def _agent_dir(root, user, group, agent_slug):
    user_norm = _normalize_segment(user, "user")
    group_norm = _normalize_segment(group, "group")
    agent_norm = _normalize_segment(agent_slug, "agent")
    path = root / user_norm / group_norm / agent_norm
    _ensure_within_root(root, path)
    return path, user_norm, group_norm, agent_norm


def _agent_json_path(agent_dir):
    return agent_dir / "agent.json"


def _section_file_name(section_name):
    section_norm = _normalize_section_key(section_name)
    return f"{section_norm}.md", section_norm


def _legacy_section_file_name(section_name):
    section_legacy = _normalize_segment(section_name, "section")
    return f"{section_legacy}.md", section_legacy


def _normalize_section_key(value):
    raw = str(value).strip().lower()
    if not raw:
        raise ValueError("Invalid section")
    if raw.endswith(".md"):
        raw = raw[:-3]
    if raw.endswith("-md"):
        raw = raw[:-3]
    if raw.endswith("_md"):
        raw = raw[:-3]
    return _normalize_segment(raw, "section")


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_text(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def list_agents(agents_root, user):
    root = Path(agents_root)
    user_norm = _normalize_segment(user, "user")
    user_root = root / user_norm
    if not user_root.exists():
        return []

    items = []
    for group_dir in user_root.iterdir():
        if not group_dir.is_dir():
            continue
        group_norm = _normalize_segment(group_dir.name, "group")
        for agent_dir in group_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            agent_json = _agent_json_path(agent_dir)
            if not agent_json.exists():
                continue
            payload = _read_json(agent_json)
            section_order_raw = payload.get("section_order", list(DEFAULT_SECTION_ORDER))
            section_order = []
            seen = set()
            if isinstance(section_order_raw, list):
                for name in section_order_raw:
                    try:
                        normalized = _normalize_section_key(name)
                    except ValueError:
                        continue
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    section_order.append(normalized)
            if not section_order:
                section_order = list(DEFAULT_SECTION_ORDER)
            items.append(
                {
                    "id": payload.get("id", _normalize_segment(agent_dir.name, "agent")),
                    "title": payload.get("title", agent_dir.name),
                    "description": payload.get("description", ""),
                    "user": payload.get("user", user_norm),
                    "group": payload.get("group", group_norm),
                    "agent_slug": _normalize_segment(agent_dir.name, "agent"),
                    "section_order": section_order,
                }
            )

    items.sort(key=lambda item: (item.get("group", ""), item.get("title", "")))
    return items


def load_agent(agents_root, user, group, agent_slug):
    root = Path(agents_root)
    agent_dir, user_norm, group_norm, agent_norm = _agent_dir(
        root, user, group, agent_slug
    )
    agent_json = _agent_json_path(agent_dir)
    if not agent_json.exists():
        raise FileNotFoundError("Agent not found")

    payload = _read_json(agent_json)
    section_order_raw = payload.get("section_order", list(DEFAULT_SECTION_ORDER))
    section_order = []
    seen = set()
    if isinstance(section_order_raw, list):
        for name in section_order_raw:
            try:
                normalized = _normalize_section_key(name)
            except ValueError:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            section_order.append(normalized)
    if not section_order:
        section_order = list(DEFAULT_SECTION_ORDER)

    sections = {}
    for section_name in section_order:
        file_name, section_norm = _section_file_name(section_name)
        section_path = agent_dir / file_name
        if section_path.exists():
            sections[section_norm] = _read_text(section_path)
            continue

        # Legacy fallback for older malformed section names (e.g. role.md -> role-md.md)
        legacy_file_name, _ = _legacy_section_file_name(section_name)
        legacy_path = agent_dir / legacy_file_name
        sections[section_norm] = _read_text(legacy_path) if legacy_path.exists() else ""

    return {
        "id": payload.get("id", agent_norm),
        "title": payload.get("title", agent_norm),
        "description": payload.get("description", ""),
        "user": payload.get("user", user_norm),
        "group": payload.get("group", group_norm),
        "agent_slug": agent_norm,
        "section_order": section_order,
        "sections": sections,
        "construct_defaults": payload.get("construct_defaults"),
    }


def save_section(agents_root, user, group, agent_slug, section_name, content):
    root = Path(agents_root)
    agent_dir, _, _, _ = _agent_dir(root, user, group, agent_slug)
    agent_json = _agent_json_path(agent_dir)
    if not agent_json.exists():
        raise FileNotFoundError("Agent not found")

    file_name, section_norm = _section_file_name(section_name)
    section_path = agent_dir / file_name
    _ensure_within_root(root, section_path)
    _write_text(section_path, str(content))
    return {"ok": True, "section": section_norm}


def create_agent(
    agents_root,
    user,
    group,
    agent_slug,
    title,
    description="",
    section_order=None,
    construct_defaults=None,
):
    root = Path(agents_root)
    agent_dir, user_norm, group_norm, agent_norm = _agent_dir(
        root, user, group, agent_slug
    )
    if agent_dir.exists():
        raise FileExistsError("Agent already exists")

    sections = section_order if isinstance(section_order, list) and section_order else list(DEFAULT_SECTION_ORDER)
    section_order_norm = []
    seen = set()
    for name in sections:
        normalized = _normalize_section_key(name)
        if normalized in seen:
            continue
        seen.add(normalized)
        section_order_norm.append(normalized)

    agent_dir.mkdir(parents=True, exist_ok=False)
    payload = {
        "id": agent_norm,
        "title": str(title).strip() or agent_norm,
        "description": str(description),
        "user": user_norm,
        "group": group_norm,
        "section_order": section_order_norm,
    }
    if construct_defaults is not None:
        payload["construct_defaults"] = construct_defaults
    _write_json(_agent_json_path(agent_dir), payload)

    for section in section_order_norm:
        file_name, _ = _section_file_name(section)
        _write_text(agent_dir / file_name, "")

    return {
        "id": payload["id"],
        "title": payload["title"],
        "description": payload["description"],
        "user": payload["user"],
        "group": payload["group"],
        "agent_slug": agent_norm,
        "section_order": section_order_norm,
    }


def delete_agent(agents_root, user, group, agent_slug):
    root = Path(agents_root)
    agent_dir, _, _, _ = _agent_dir(root, user, group, agent_slug)
    if not agent_dir.exists():
        raise FileNotFoundError("Agent not found")
    if not _agent_json_path(agent_dir).exists():
        raise ValueError("Refusing to delete directory without agent.json")
    _ensure_within_root(root, agent_dir)
    shutil.rmtree(agent_dir)
    return {"ok": True}
