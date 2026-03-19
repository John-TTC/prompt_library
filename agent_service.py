import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SECTION_ORDER = ["role", "rules", "process", "output"]
DEFAULT_AGENT_GROUP = "agent-group-unsorted"
DEFAULT_AGENT_GROUP_LABEL = "ungrouped"
AGENT_GROUPS_FILE = "agent-groups.json"
GROUPS_SCHEMA_VERSION = 1


def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def _normalize_group_label(label, fallback):
    text = str(label).strip()
    return text or fallback


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
    raw_groups = payload.get("groups", []) if isinstance(payload, dict) else []
    if not isinstance(raw_groups, list):
        return []

    cleaned = []
    seen = set()
    for idx, value in enumerate(raw_groups):
        if isinstance(value, dict):
            key_raw = value.get("key", "")
            label_raw = value.get("label", "")
            order_raw = value.get("order")
            created_at = str(value.get("createdAt", "")).strip() or None
        else:
            key_raw = value
            label_raw = value
            order_raw = idx
            created_at = None
        try:
            key = _normalize_group_name(key_raw)
        except ValueError:
            continue
        if key in seen:
            continue
        seen.add(key)
        order = order_raw if isinstance(order_raw, int) and order_raw >= 0 else idx
        cleaned.append(
            {
                "key": key,
                "label": _normalize_group_label(label_raw, key),
                "order": order,
                "createdAt": created_at,
            }
        )

    cleaned.sort(key=lambda item: (item["order"], item["key"]))
    for idx, item in enumerate(cleaned):
        item["order"] = idx
    return cleaned


def _save_group_registry(user_root, groups_meta):
    seen = set()
    cleaned = []
    for idx, value in enumerate(groups_meta):
        if not isinstance(value, dict):
            continue
        try:
            key = _normalize_group_name(value.get("key", ""))
        except ValueError:
            continue
        if key in seen:
            continue
        seen.add(key)
        label = _normalize_group_label(value.get("label", ""), key)
        order_raw = value.get("order")
        order = order_raw if isinstance(order_raw, int) and order_raw >= 0 else idx
        created_at = str(value.get("createdAt", "")).strip() or None
        cleaned.append(
            {
                "key": key,
                "label": label,
                "order": order,
                "createdAt": created_at,
            }
        )

    cleaned.sort(key=lambda item: (item["order"], item["key"]))
    for idx, item in enumerate(cleaned):
        item["order"] = idx

    payload = {
        "schemaVersion": GROUPS_SCHEMA_VERSION,
        "groups": cleaned,
    }
    if not user_root.exists():
        user_root.mkdir(parents=True, exist_ok=True)
    _write_json(_agent_groups_path(user_root), payload)
    return cleaned


def _sync_agent_groups(root, user):
    user_root, _ = _user_root(root, user)
    user_root.mkdir(parents=True, exist_ok=True)
    groups_meta = _load_group_registry(user_root)
    by_key = {item["key"]: dict(item) for item in groups_meta}

    changed = False
    if DEFAULT_AGENT_GROUP not in by_key:
        by_key[DEFAULT_AGENT_GROUP] = {
            "key": DEFAULT_AGENT_GROUP,
            "label": DEFAULT_AGENT_GROUP_LABEL,
            "order": len(by_key),
            "createdAt": _now_iso(),
        }
        changed = True
    elif by_key[DEFAULT_AGENT_GROUP].get("label") != DEFAULT_AGENT_GROUP_LABEL:
        by_key[DEFAULT_AGENT_GROUP]["label"] = DEFAULT_AGENT_GROUP_LABEL
        changed = True

    discovered = sorted(_collect_group_dirs(user_root))
    for key in discovered:
        if key in by_key:
            continue
        by_key[key] = {
            "key": key,
            "label": key,
            "order": len(by_key),
            "createdAt": _now_iso(),
        }
        changed = True

    groups_sorted = sorted(by_key.values(), key=lambda item: (item.get("order", 0), item["key"]))
    for idx, item in enumerate(groups_sorted):
        if item.get("order") != idx:
            changed = True
        item["order"] = idx

    # Keep folders aligned with metadata entries.
    for item in groups_sorted:
        group_dir = user_root / item["key"]
        _ensure_within_root(root, group_dir)
        if not group_dir.exists():
            group_dir.mkdir(parents=True, exist_ok=True)
            changed = True

    if changed:
        groups_sorted = _save_group_registry(user_root, groups_sorted)
    return groups_sorted


def _ensure_group_in_registry(root, user, group, label=""):
    groups = _sync_agent_groups(root, user)
    normalized_group = _normalize_group_name(group)
    if any(item["key"] == normalized_group for item in groups):
        return groups
    groups.append(
        {
            "key": normalized_group,
            "label": _normalize_group_label(label, normalized_group),
            "order": len(groups),
            "createdAt": _now_iso(),
        }
    )
    user_root, _ = _user_root(root, user)
    saved = _save_group_registry(user_root, groups)
    group_dir = user_root / normalized_group
    _ensure_within_root(root, group_dir)
    group_dir.mkdir(parents=True, exist_ok=True)
    return saved


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


def _estimate_tokens(char_count):
    return int(round(max(0, int(char_count)) / 4))


def list_agents(agents_root, user):
    root = Path(agents_root)
    user_root, user_norm = _user_root(root, user)
    _sync_agent_groups(root, user_norm)
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
            total_chars = 0
            for section_name in section_order:
                file_name, _ = _section_file_name(section_name)
                section_path = agent_dir / file_name
                if section_path.exists():
                    total_chars += len(_read_text(section_path))
                    continue
                legacy_file_name, _ = _legacy_section_file_name(section_name)
                legacy_path = agent_dir / legacy_file_name
                if legacy_path.exists():
                    total_chars += len(_read_text(legacy_path))
            items.append(
                {
                    "id": payload.get("id", _normalize_segment(agent_dir.name, "agent")),
                    "title": payload.get("title", agent_dir.name),
                    "description": payload.get("description", ""),
                    "user": payload.get("user", user_norm),
                    "group": group_norm,
                    "agent_slug": _normalize_segment(agent_dir.name, "agent"),
                    "section_order": section_order,
                    "char_count": total_chars,
                    "token_estimate": _estimate_tokens(total_chars),
                }
            )

    items.sort(key=lambda item: (item.get("group", ""), item.get("title", "")))
    return items


def list_agent_groups(agents_root, user):
    root = Path(agents_root)
    groups = _sync_agent_groups(root, user)
    return [dict(item) for item in groups]


def create_agent_group(agents_root, user, group, label=""):
    root = Path(agents_root)
    groups = _sync_agent_groups(root, user)
    group_norm = _normalize_group_name(group)
    if any(item["key"] == group_norm for item in groups):
        raise ValueError("Group already exists")
    groups.append(
        {
            "key": group_norm,
            "label": _normalize_group_label(label, group_norm),
            "order": len(groups),
            "createdAt": _now_iso(),
        }
    )
    user_root, _ = _user_root(root, user)
    saved = _save_group_registry(user_root, groups)
    group_dir = user_root / group_norm
    _ensure_within_root(root, group_dir)
    group_dir.mkdir(parents=True, exist_ok=True)
    created = next((item for item in saved if item["key"] == group_norm), None)
    return {"group": created or {"key": group_norm, "label": group_norm, "order": 0, "createdAt": None}}


def reorder_agent_groups(agents_root, user, ordered_group_keys):
    root = Path(agents_root)
    user_root, _ = _user_root(root, user)
    groups = _sync_agent_groups(root, user)

    requested = []
    seen = set()
    if isinstance(ordered_group_keys, list):
        for value in ordered_group_keys:
            try:
                key = _normalize_group_name(value)
            except ValueError:
                continue
            if key in seen:
                continue
            seen.add(key)
            requested.append(key)

    by_key = {item["key"]: dict(item) for item in groups}
    ordered = []
    for key in requested:
        if key in by_key:
            ordered.append(by_key[key])
            del by_key[key]
    for item in sorted(by_key.values(), key=lambda value: (value.get("order", 0), value["key"])):
        ordered.append(item)

    for idx, item in enumerate(ordered):
        item["order"] = idx

    saved = _save_group_registry(user_root, ordered)
    return {"ok": True, "groups": saved}


def rename_agent_group(agents_root, user, group, label):
    root = Path(agents_root)
    user_root, _ = _user_root(root, user)
    group_norm = _normalize_group_name(group)
    if group_norm == DEFAULT_AGENT_GROUP:
        raise ValueError(f'Cannot rename "{DEFAULT_AGENT_GROUP_LABEL}"')

    next_label = str(label).strip()
    if not next_label:
        raise ValueError("Group name is required")

    groups = _sync_agent_groups(root, user)
    target = next((item for item in groups if item["key"] == group_norm), None)
    if not target:
        raise FileNotFoundError("Group not found")

    for item in groups:
        if item["key"] == group_norm:
            continue
        if str(item.get("label", "")).strip().lower() == next_label.lower():
            raise ValueError("Group name already exists")

    target["label"] = _normalize_group_label(next_label, group_norm)
    saved = _save_group_registry(user_root, groups)
    updated = next((item for item in saved if item["key"] == group_norm), None)
    return {"ok": True, "group": updated or target}


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


def save_agent_meta(agents_root, user, group, agent_slug, title=None, description=None):
    root = Path(agents_root)
    agent_dir, _, _, agent_norm = _agent_dir(root, user, group, agent_slug)
    agent_json = _agent_json_path(agent_dir)
    if not agent_json.exists():
        raise FileNotFoundError("Agent not found")

    payload = _read_json(agent_json)
    if title is not None:
        title_value = str(title).strip()
        if not title_value:
            raise ValueError("Agent title is required")
        payload["title"] = title_value
    if description is not None:
        payload["description"] = str(description)
    _write_json(agent_json, payload)

    return {
        "ok": True,
        "id": payload.get("id", agent_norm),
        "title": payload.get("title", agent_norm),
        "description": payload.get("description", ""),
    }


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
        "char_count": 0,
        "token_estimate": 0,
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


def delete_agent_group(agents_root, user, group):
    root = Path(agents_root)
    user_root, _ = _user_root(root, user)
    group_norm = _normalize_group_name(group)
    if group_norm == DEFAULT_AGENT_GROUP:
        raise ValueError(f'Cannot delete "{DEFAULT_AGENT_GROUP_LABEL}"')

    groups = _sync_agent_groups(root, user)
    group_entry = next((item for item in groups if item["key"] == group_norm), None)
    if not group_entry:
        raise FileNotFoundError("Group not found")

    source_dir = user_root / group_norm
    unsorted_dir = user_root / DEFAULT_AGENT_GROUP
    _ensure_within_root(root, source_dir)
    _ensure_within_root(root, unsorted_dir)
    unsorted_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    if source_dir.exists():
        for child in list(source_dir.iterdir()):
            if not child.is_dir():
                continue
            agent_json = _agent_json_path(child)
            if not agent_json.exists():
                continue
            target = unsorted_dir / child.name
            _ensure_within_root(root, target)
            if target.exists():
                raise FileExistsError(f"Target already has agent: {child.name}")
            shutil.move(str(child), str(target))
            moved += 1

            moved_json = _agent_json_path(target)
            payload = _read_json(moved_json)
            payload["group"] = DEFAULT_AGENT_GROUP
            _write_json(moved_json, payload)

        try:
            source_dir.rmdir()
        except OSError:
            pass

    next_groups = [item for item in groups if item["key"] != group_norm]
    for idx, item in enumerate(next_groups):
        item["order"] = idx
    _save_group_registry(user_root, next_groups)
    _sync_agent_groups(root, user)
    return {"ok": True, "moved_agents": moved, "group": group_norm}


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
