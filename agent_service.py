import json
import re
import shutil
from pathlib import Path


DEFAULT_SECTION_ORDER = ["role", "rules", "process", "output"]
DEFAULT_AGENT_GROUP = "agent-group-unsorted"
AGENT_GROUPS_FILE = "agent-groups.json"


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


def _user_root(root, user):
    user_norm = _normalize_segment(user, "user")
    path = root / user_norm
    _ensure_within_root(root, path)
    return path, user_norm


def _agent_groups_path(user_root):
    return user_root / AGENT_GROUPS_FILE


def _normalize_group_name(group):
    return _normalize_segment(group, "group")


def _collect_group_dirs(user_root):
    if not user_root.exists():
        return []
    groups = []
    for item in user_root.iterdir():
        if not item.is_dir():
            continue
        try:
            groups.append(_normalize_group_name(item.name))
        except ValueError:
            continue
    return groups


def _load_group_registry(user_root):
    groups_path = _agent_groups_path(user_root)
    if not groups_path.exists():
        return []
    payload = _read_json(groups_path)
    raw_groups = payload.get("groups", [])
    if not isinstance(raw_groups, list):
        return []
    cleaned = []
    seen = set()
    for value in raw_groups:
        try:
            normalized = _normalize_group_name(value)
        except ValueError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def _save_group_registry(user_root, groups):
    seen = set()
    cleaned = []
    for value in groups:
        try:
            normalized = _normalize_group_name(value)
        except ValueError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    cleaned.sort()
    payload = {"groups": cleaned}
    if not user_root.exists():
        user_root.mkdir(parents=True, exist_ok=True)
    _write_json(_agent_groups_path(user_root), payload)
    return cleaned


def _ensure_group_in_registry(root, user, group):
    user_root, _ = _user_root(root, user)
    normalized_group = _normalize_group_name(group)
    groups = _load_group_registry(user_root)
    if normalized_group in groups:
        return groups
    groups.append(normalized_group)
    return _save_group_registry(user_root, groups)


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


def list_agent_groups(agents_root, user):
    root = Path(agents_root)
    user_root, _ = _user_root(root, user)
    persisted = _load_group_registry(user_root)
    discovered = _collect_group_dirs(user_root)

    seen = set()
    groups = []
    for name in [DEFAULT_AGENT_GROUP, *persisted, *discovered]:
        try:
            normalized = _normalize_group_name(name)
        except ValueError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        groups.append(normalized)
    return groups


def create_agent_group(agents_root, user, group):
    root = Path(agents_root)
    user_root, _ = _user_root(root, user)
    group_norm = _normalize_group_name(group)
    groups = _load_group_registry(user_root)
    if group_norm in groups:
        raise ValueError("Group already exists")
    groups.append(group_norm)
    _save_group_registry(user_root, groups)
    return {"group": group_norm}


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


def add_section(agents_root, user, group, agent_slug, section_name):
    root = Path(agents_root)
    agent_dir, _, _, _ = _agent_dir(root, user, group, agent_slug)
    agent_json = _agent_json_path(agent_dir)
    if not agent_json.exists():
        raise FileNotFoundError("Agent not found")

    payload = _read_json(agent_json)
    section_order_raw = payload.get("section_order", list(DEFAULT_SECTION_ORDER))
    section_order_norm = []
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
            section_order_norm.append(normalized)
    if not section_order_norm:
        section_order_norm = list(DEFAULT_SECTION_ORDER)
        seen = set(section_order_norm)

    requested_section = _normalize_section_key(section_name)
    if requested_section in seen:
        raise ValueError("Section already exists")

    section_order_norm.append(requested_section)
    payload["section_order"] = section_order_norm
    _write_json(agent_json, payload)

    section_file_name, section_norm = _section_file_name(requested_section)
    section_path = agent_dir / section_file_name
    _ensure_within_root(root, section_path)
    if not section_path.exists():
        _write_text(section_path, "")

    return {"ok": True, "section": section_norm, "section_order": section_order_norm}


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
    _ensure_group_in_registry(root, user, group)

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


def move_agent_to_group(agents_root, user, from_group, agent_slug, to_group):
    root = Path(agents_root)
    from_dir, user_norm, _, agent_norm = _agent_dir(root, user, from_group, agent_slug)
    to_group_norm = _normalize_group_name(to_group)
    to_dir = root / user_norm / to_group_norm / agent_norm
    _ensure_within_root(root, to_dir)

    if not from_dir.exists() or not _agent_json_path(from_dir).exists():
        raise FileNotFoundError("Agent not found")
    if to_dir.exists():
        raise FileExistsError("Agent already exists in target group")

    to_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(from_dir), str(to_dir))

    agent_json = _agent_json_path(to_dir)
    payload = _read_json(agent_json)
    payload["group"] = to_group_norm
    payload["user"] = user_norm
    _write_json(agent_json, payload)

    _ensure_group_in_registry(root, user, to_group_norm)
    return {"ok": True, "group": to_group_norm, "agent_slug": agent_norm}


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
