#!/usr/bin/env python3
"""Read-only Master Team protocol checks and non-overwriting v1 migration.

Python 3.10+, standard library only. Never sends messages or acquires runtime locks.
"""
from __future__ import annotations

import argparse
import copy
import json
import ntpath
import os
import re
import sys
from pathlib import Path, PurePosixPath

SKILL_ROOT = Path(__file__).resolve().parents[1]


def load(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def shape_errors(value, schema, at="$"):
    """Validate the subset of Draft 2020-12 used by the bundled schemas."""
    errors = []
    kinds = {
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
        "boolean": lambda x: isinstance(x, bool),
        "null": lambda x: x is None,
    }
    if "anyOf" in schema and not any(not shape_errors(value, option, at) for option in schema["anyOf"]):
        return [f"{at}: no anyOf shape matched"]
    expected = schema.get("type")
    if expected:
        expected = expected if isinstance(expected, list) else [expected]
        if not any(kinds[k](value) for k in expected):
            return [f"{at}: expected {'/'.join(expected)}"]
    if "const" in schema and (value != schema["const"]
                              or isinstance(value, bool) != isinstance(schema["const"], bool)):
        errors.append(f"{at}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{at}: unsupported value {value!r}")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{at}: empty string")
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            errors.append(f"{at}: numeric limit exceeded")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{at}.{key}: required")
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{at}: too few properties")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties")
        for key, child in value.items():
            if key in properties:
                errors.extend(shape_errors(child, properties[key], f"{at}.{key}"))
            elif isinstance(additional, dict):
                errors.extend(shape_errors(child, additional, f"{at}.{key}"))
    if isinstance(value, list) and "items" in schema:
        for index, child in enumerate(value):
            errors.extend(shape_errors(child, schema["items"], f"{at}[{index}]"))
    return errors


def normalize_path(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path must be a nonempty string")
    path = value.replace("\\", "/")
    if path.startswith("/") or ntpath.splitdrive(path)[0] or ":" in path:
        raise ValueError("path must be relative to project root")
    if any(c in path for c in "*?[]\x00") or any(part == ".." for part in path.split("/")):
        raise ValueError("parent traversal/glob/NUL is not allowed")
    if any(part.endswith((" ", ".")) and part != "." for part in path.split("/") if part):
        raise ValueError("ambiguous Windows path ending")
    return PurePosixPath(path).as_posix().casefold()


def overlaps(a, b):
    a, b = normalize_path(a), normalize_path(b)
    return a == "." or b == "." or a == b or a.startswith(b + "/") or b.startswith(a + "/")


def get_attempt(registry, ticket_id, attempt_id):
    return registry.get("tickets", {}).get(ticket_id, {}).get("attempts", {}).get(attempt_id)


def validate_registry(registry):
    errors = shape_errors(registry, load(SKILL_ROOT / "schemas/registry.schema.json"))
    if errors:
        return errors
    owner, generation = registry["active_master_thread_id"], registry["generation"]
    if owner is None and registry["tickets"]:
        errors.append("tickets require a bound Master")
    if registry.get("migration_unresolved"):
        errors.append("v1 migration has unresolved running/task state")
    policy = registry["policy"]
    if policy["hard_message_limit_bytes"] and policy["message_budget_bytes"] > policy["hard_message_limit_bytes"]:
        errors.append("message budget exceeds confirmed hard limit")
    if registry["mode"] == "persistent" and registry["capabilities"]["independent_sessions"] != "available":
        errors.append("persistent mode requires verified independent sessions")
    if registry["mode"] == "parent_scoped" and registry["capabilities"]["parent_scoped_agents"] != "available":
        errors.append("parent_scoped mode requires verified parent-scoped agents")
    handoff = registry["handoff"]
    if registry["handoff_status"] in ("requested", "quiescing", "completed", "blocked"):
        if not isinstance(handoff, dict):
            errors.append("handoff state requires handoff details")
        elif registry["handoff_status"] == "completed":
            if ("source_generation" not in handoff or not all(
                    isinstance(handoff.get(k), str) and handoff[k].strip()
                    for k in ("from_session_id", "to_session_id", "quiescence_evidence", "transferred_by", "completed_at"))):
                errors.append("completed handoff lacks transfer evidence")
            elif not isinstance(handoff["source_generation"], int) or isinstance(handoff["source_generation"], bool):
                errors.append("handoff source_generation must be an integer")
            elif (handoff["to_session_id"] != owner or handoff["source_generation"] + 1 != generation
                  or registry["previous_master_thread_id"] != handoff["from_session_id"]):
                errors.append("completed handoff identity/generation mismatch")

    seen_sessions = set()
    for worker_id, worker in registry["workers"].items():
        session_id = worker["session_id"]
        if session_id:
            key = (worker["host_id"], session_id)
            if key in seen_sessions:
                errors.append(f"worker {worker_id}: duplicate host/session identity")
            seen_sessions.add(key)
        if worker["verified"] and not session_id:
            errors.append(f"worker {worker_id}: verified without session identity")
        if worker["session_kind"] == "child" and not worker["parent_session_id"]:
            errors.append(f"worker {worker_id}: child has no parent identity")
        active = worker["active_ticket"]
        if active:
            attempt = get_attempt(registry, active["ticket_id"], active["attempt_id"])
            if not attempt or attempt["worker_id"] != worker_id:
                errors.append(f"worker {worker_id}: invalid active_ticket")

    attempts = {}
    graph = {}
    for ticket_id, ticket in registry["tickets"].items():
        if ticket["current_attempt"] not in ticket["attempts"]:
            errors.append(f"ticket {ticket_id}: current_attempt does not exist")
        for attempt_id, attempt in ticket["attempts"].items():
            key = (ticket_id, attempt_id)
            attempts[key] = attempt
            graph[key] = [(d["ticket_id"], d["attempt_id"]) for d in attempt["depends_on"]]
            if attempt["worker_id"] not in registry["workers"]:
                errors.append(f"{key}: unknown Worker")
            if attempt["master_generation"] > generation:
                errors.append(f"{key}: future Master generation")
            if attempt["master_generation"] == generation and attempt["master_session_id"] != owner:
                errors.append(f"{key}: current-generation owner mismatch")
            if attempt["acceptance"] in ("accepted", "rejected") and attempt["execution"] != "submitted":
                errors.append(f"{key}: acceptance requires submitted execution")
            if attempt["execution"] == "submitted" and not attempt["report_ref"]:
                errors.append(f"{key}: submitted execution requires report_ref")
            if attempt["execution"] == "stopped" and attempt["runtime"] != "ended":
                errors.append(f"{key}: stopped execution requires ended runtime")
            if attempt["execution"] == "running" and attempt["runtime"] == "ended":
                errors.append(f"{key}: running execution contradicts ended runtime")
            for relative in attempt["reads"] + attempt["writes"]:
                try:
                    normalize_path(relative)
                    # Real paths can only be checked when this host can access project_root.
                    if registry["project_root"] and Path(registry["project_root"]).is_dir():
                        root = Path(registry["project_root"]).resolve()
                        if not (root / relative.replace("\\", "/")).resolve().is_relative_to(root):
                            errors.append(f"{key}: path resolves outside project root: {relative}")
                except (ValueError, OSError) as exc:
                    errors.append(f"{key}: {relative!r}: {exc}")
            if attempt["runtime"] != "ended":
                worker = registry["workers"].get(attempt["worker_id"], {})
                if worker.get("active_ticket") != {"ticket_id": ticket_id, "attempt_id": attempt_id}:
                    errors.append(f"{key}: live/unknown attempt must be Worker's active_ticket")

    for key, dependencies in graph.items():
        for dep in dependencies:
            if dep not in attempts:
                errors.append(f"{key}: missing dependency {dep}")
            elif attempts[key]["execution"] in ("running", "submitted") and attempts[dep]["acceptance"] != "accepted":
                errors.append(f"{key}: started before dependency accepted")
    visiting, visited = set(), set()

    def visit(key):
        if key in visiting:
            errors.append(f"dependency cycle at {key}")
            return
        if key in visited:
            return
        visiting.add(key)
        for dep in graph.get(key, []):
            visit(dep)
        visiting.remove(key)
        visited.add(key)

    for key in graph:
        visit(key)

    valid_claims = []
    for claim in registry["write_claims"]:
        key = (claim["ticket_id"], claim["attempt_id"])
        attempt = attempts.get(key)
        try:
            path = normalize_path(claim["path"])
        except ValueError as exc:
            errors.append(f"claim {key}: {exc}")
            continue
        if not attempt:
            errors.append(f"claim {key}: unknown attempt")
        elif path not in [normalize_path(p) for p in attempt["writes"] if _safe_path(p)]:
            errors.append(f"claim {key}: path not in frozen writes")
        valid_claims.append((key, path))
    for index, (key, path) in enumerate(valid_claims):
        for other_key, other_path in valid_claims[index + 1:]:
            if key != other_key and overlaps(path, other_path):
                errors.append(f"overlapping write claims: {key}:{path} vs {other_key}:{other_path}")
    for key, attempt in attempts.items():
        if attempt["runtime"] != "ended":
            for path in attempt["writes"]:
                if _safe_path(path) and (key, normalize_path(path)) not in valid_claims:
                    errors.append(f"{key}: live/unknown write scope has no claim: {path}")
    return errors


def _safe_path(path):
    try:
        normalize_path(path)
        return True
    except ValueError:
        return False


def validate_dispatch(registry, envelope):
    errors = validate_registry(registry)
    errors += shape_errors(envelope, load(SKILL_ROOT / "schemas/dispatch.schema.json"))
    if errors:
        return errors
    if registry["handoff_status"] not in ("none", "completed"):
        errors.append("dispatch blocked during unbound/incomplete handoff")
    if (envelope["master_session_id"] != registry["active_master_thread_id"]
            or envelope["master_generation"] != registry["generation"]):
        errors.append("stale or incorrect Master identity/generation")
    ticket = registry["tickets"].get(envelope["ticket_id"])
    attempt = get_attempt(registry, envelope["ticket_id"], envelope["attempt_id"])
    if not ticket or not attempt:
        return errors + ["dispatch references unregistered attempt"]
    if ticket["task_id"] != envelope["task_id"] or ticket["current_attempt"] != envelope["attempt_id"]:
        errors.append("task/current attempt mismatch")
    if attempt["execution"] != "planned" or attempt["delivery"] not in ("not_sent", "pending_delivery"):
        errors.append("attempt already active/submitted/unknown; inspect status instead of sending")
    for field in ("master_session_id", "master_generation", "worker_id", "candidate_ref", "goal", "reads", "writes"):
        if attempt[field] != envelope[field]:
            errors.append(f"dispatch differs from frozen attempt: {field}")
    worker = registry["workers"].get(envelope["worker_id"])
    if not worker or not worker["verified"] or worker["session_kind"] in ("unbound", "legacy_unverified"):
        errors.append("Worker not verified")
    else:
        if worker["session_id"] != envelope["worker_session_id"]:
            errors.append("wrong recipient session")
        if worker["session_kind"] == "child" and worker["parent_session_id"] != registry["active_master_thread_id"]:
            errors.append("child belongs to another parent; registry change cannot transfer control")
    if registry["mode"] != "manual" and registry["capabilities"]["message"] != "available":
        errors.append("message capability unverified/unavailable")
    for dep in attempt["depends_on"]:
        previous = get_attempt(registry, dep["ticket_id"], dep["attempt_id"])
        if not previous or previous["acceptance"] != "accepted":
            errors.append("dependency not accepted")
        elif registry["tickets"][dep["ticket_id"]]["current_attempt"] != dep["attempt_id"]:
            errors.append("dependency changed since frozen attempt; review candidate before dispatch")
    return errors


def validate_result(registry, result):
    errors = validate_registry(registry)
    errors += shape_errors(result, load(SKILL_ROOT / "schemas/result.schema.json"))
    if errors:
        return errors
    ticket = registry["tickets"].get(result["ticket_id"])
    attempt = get_attempt(registry, result["ticket_id"], result["attempt_id"])
    if not ticket or not attempt:
        return errors + ["unknown result attempt"]
    if ticket["task_id"] != result["task_id"] or ticket["current_attempt"] != result["attempt_id"]:
        errors.append("historical/wrong task result; keep as history, not current completion")
    for field in ("master_generation", "candidate_ref"):
        if attempt[field] != result[field]:
            errors.append(f"result {field} does not match original dispatch")
    if attempt["execution"] == "planned":
        errors.append("result arrived before recorded start; inspect receipt and runtime first")
    if attempt["execution"] == "stopped":
        errors.append("attempt already stopped; result cannot revive it")
    if result["status"] == "stopped" and attempt["runtime"] != "ended":
        errors.append("stopped result requires host-confirmed ended runtime")
    if result["status"] == "done":
        if not result["report_ref"]:
            errors.append("done result requires real report_ref")
        if result["checks"]["failed"]:
            errors.append("done result contains failed checks; resolve or report error/blocked")
    if attempt["execution"] == "submitted" and attempt["report_ref"] != result["report_ref"]:
        errors.append("repeated result changed report_ref; retain original and inspect")
    return errors


def migrate_v1(old):
    if not isinstance(old, dict) or old.get("schema_version") != 1:
        raise ValueError("migration expects schema_version=1")
    new = load(SKILL_ROOT / "assets/worker_sessions.json")
    for field in ("project_root", "host_id", "active_master_thread_id", "previous_master_thread_id", "generation"):
        if field in old:
            new[field] = copy.deepcopy(old[field])
    new["handoff_status"] = "none" if new["active_master_thread_id"] else "unbound"
    unresolved = []
    if old.get("handoff_status") not in (None, "unbound", "none", "completed", "active"):
        unresolved.append({"old_handoff_status": old["handoff_status"]})
    for worker_id, worker in old.get("workers", {}).items():
        new["workers"][worker_id] = {
            "session_id":worker.get("thread_id"), "host_id":worker.get("host_id"), "role":worker_id,
            "session_kind":"legacy_unverified", "transport":"unverified",
            "parent_session_id":worker.get("source_parent_thread_id"),
            "verified":False, "active_ticket":None, "legacy_worker":copy.deepcopy(worker),
        }
        if worker.get("active_ticket"):
            unresolved.append({"worker_id":worker_id,"active_ticket":worker["active_ticket"]})
    if old.get("tickets"):
        unresolved.append({"legacy_tickets_require_review": True})
    new["legacy_v1"] = copy.deepcopy(old)
    new["legacy_tickets"] = copy.deepcopy(old.get("tickets", {}))
    new["migration_unresolved"] = unresolved
    new["migration_note"] = "Not activated. Confirm real runtime, capabilities and paths before replacing live registry."
    return new


def message_size(path, budget=4096, hard_limit=None):
    if budget < 1 or (hard_limit is not None and hard_limit < 1):
        raise ValueError("byte limits must be positive")
    # Match the final decoded text, including intentional CRLF, without newline conversion.
    payload = Path(path).read_bytes().decode("utf-8-sig").encode("utf-8")
    return {"bytes":len(payload),"budget_bytes":budget,"over_budget":len(payload)>budget,
            "hard_limit_bytes":hard_limit,"over_hard_limit":hard_limit is not None and len(payload)>hard_limit}


ONBOARDING_STEPS = ("purpose", "environment", "roles", "setup", "practice", "first_task")


def validate_onboarding(state):
    errors = shape_errors(state, load(SKILL_ROOT / "schemas/onboarding.schema.json"))
    if errors:
        return errors
    completed, skipped = state["completed_steps"], state["skipped_steps"]
    if len(completed) != len(set(completed)) or len(skipped) != len(set(skipped)):
        errors.append("duplicate onboarding step")
    if set(completed) & set(skipped):
        errors.append("a step cannot be both completed and skipped")
    accounted = set(completed) | set(skipped)
    if state["status"] == "completed":
        if accounted != set(ONBOARDING_STEPS) or state["current_step"] != "finished":
            errors.append("completed onboarding requires all steps accounted and finished cursor")
    elif state["current_step"] == "finished":
        errors.append("finished cursor requires completed onboarding status")
    if state["status"] == "not_started" and (accounted or state["current_step"] != "purpose"):
        errors.append("not_started onboarding cannot contain prior progress")
    return errors


def _project_identity(path):
    if ntpath.splitdrive(path)[0] or "\\" in path:
        return ntpath.normcase(ntpath.normpath(path))
    return os.path.normcase(str(Path(path).resolve()))


def onboarding_decision(state, action="auto", existing_team=False, concrete_task=False,
                        project_root=None, learner_scope=None):
    """Suggest a route, never mutate progress, team state, or send a message.

    The caller maps an explicit human request to action. This is not a natural
    language interpreter and never detects installation events.
    """
    actions = {"auto", "teach", "resume", "restart", "pause", "skip_all", "disable", "maintenance"}
    if action not in actions:
        return {"ok":False,"errors":["unknown onboarding action"],"route":"inspect_progress","step":None}

    def result(route, step=None, **extra):
        return {"ok":True,"errors":[],"route":route,"step":step,
                "read_only":True,"team_actions_authorized":False,**extra}

    # Maintenance must never turn an editing/review task into a lesson.
    if action == "maintenance":
        return result("maintenance")
    errors = validate_onboarding(state)
    if errors:
        if action == "auto" and (concrete_task or existing_team):
            return result("task",warnings=errors,preserve_old_state=True)
        return {"ok":False, "errors":errors, "route":"inspect_progress", "step":None}
    has_progress = state["status"] != "not_started"
    mismatch = (project_root is not None and state["project_root"] is not None
                and _project_identity(project_root) != _project_identity(state["project_root"]))
    mismatch = mismatch or (learner_scope is not None and state["learner_scope"] is not None
                            and learner_scope != state["learner_scope"])
    if mismatch:
        # Do not carry someone else's opt-out, cursor, or goal to the new scope.
        if action in ("pause", "skip_all", "disable"):
            suggestions = {"pause":{"suggested_status":"paused"},
                           "skip_all":{"suggested_status":"dismissed"},
                           "disable":{"suggested_auto_start":False}}[action]
            return result("new_scope_task",preserve_old_state=True,**suggestions)
        return result("new_scope_task" if concrete_task or existing_team else "new_scope_start",
                      None if concrete_task or existing_team else "purpose",preserve_old_state=True)
    if has_progress and ((project_root is not None and state["project_root"] is None)
                         or (learner_scope is not None and state["learner_scope"] is None)):
        if action == "auto" and (concrete_task or existing_team):
            return result("task",preserve_old_state=True,warnings=["onboarding scope is unverified"])
        return result("scope_unverified",preserve_old_state=True)
    # Explicit conversation controls need no runtime/role changes.
    if state["status"] == "completed" and action in ("pause", "skip_all"):
        return result("no_auto_lesson")
    if action == "pause":
        return result("pause",state["current_step"],suggested_status="paused")
    if action == "skip_all":
        return result("task",suggested_status="dismissed")
    if action == "disable":
        return result("task",suggested_auto_start=False)
    if action == "restart":
        return result("start","purpose",preserve_auto_start_preference=True)
    if action in ("teach", "resume"):
        if state["status"] == "completed":
            return result("already_completed",offered_action="restart")
        return result("resume" if has_progress else "start",state["current_step"])

    if concrete_task or existing_team or state["context"]["team_exists"] is True:
        return result("task",retain_pending_step=has_progress)
    if not state["auto_start"] or state["status"] in ("paused", "dismissed", "completed"):
        return result("no_auto_lesson")
    if state["status"] == "in_progress":
        return result("resume",state["current_step"])
    return result("start","purpose")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "dispatch", "result"):
        sub = subs.add_parser(command)
        sub.add_argument("--registry", required=True)
        if command == "dispatch":
            sub.add_argument("--envelope", required=True)
        elif command == "result":
            sub.add_argument("--result", required=True)
    sub = subs.add_parser("message-size")
    sub.add_argument("--file", required=True)
    sub.add_argument("--budget", type=int, default=4096)
    sub.add_argument("--hard-limit", type=int)
    sub = subs.add_parser("migrate")
    sub.add_argument("--input", required=True)
    sub.add_argument("--output", required=True)
    sub = subs.add_parser("onboarding")
    sub.add_argument("--state", required=True)
    sub.add_argument("--action", choices=("auto", "teach", "resume", "restart", "pause", "skip_all", "disable", "maintenance"), default="auto")
    sub.add_argument("--existing-team", action="store_true")
    sub.add_argument("--concrete-task", action="store_true")
    sub.add_argument("--project-root")
    sub.add_argument("--learner-scope")
    args = parser.parse_args()
    try:
        if args.command == "onboarding":
            decision = onboarding_decision(load(args.state), args.action, args.existing_team,
                                           args.concrete_task, args.project_root, args.learner_scope)
            print(json.dumps(decision,ensure_ascii=False,indent=2))
            return 0 if decision["ok"] else 1
        if args.command == "message-size":
            info = message_size(args.file, args.budget, args.hard_limit)
            print(json.dumps(info, ensure_ascii=False, indent=2))
            return 2 if info["over_hard_limit"] else 0
        if args.command == "migrate":
            destination = Path(args.output)
            content = migrate_v1(load(args.input))
            # x mode never overwrites either the old registry or an existing output.
            with destination.open("x", encoding="utf-8") as stream:
                json.dump(content, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            print(json.dumps({"written":str(destination),"activated":False,
                              "unresolved":len(content["migration_unresolved"])},ensure_ascii=False))
            return 0
        registry = load(args.registry)
        if args.command == "dispatch":
            errors = validate_dispatch(registry, load(args.envelope))
        elif args.command == "result":
            errors = validate_result(registry, load(args.result))
        else:
            errors = validate_registry(registry)
        print(json.dumps({"ok":not errors,"errors":errors,"read_only":True,
                          "runtime_verified":False},ensure_ascii=False,indent=2))
        return 1 if errors else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
