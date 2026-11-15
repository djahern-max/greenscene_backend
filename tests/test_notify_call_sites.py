"""
tests/test_notify_call_sites.py

Deterministic, no-DB, no-network tier — a static check over the source.

Every notify_* function in app/services/notifications.py resolves tenant
branding (brand name, sender address, SMS number, admin inbox) from the
`tenant_id` and `db` it is given. A call that omits either one sends one
tenant's notification under another tenant's identity.

Two guards:
  1. Every `notify_*(...)` call anywhere under app/ passes both `tenant_id`
     and `db` as keyword arguments.
  2. Every notify_* function declares `tenant_id` and `db` as required
     keyword-only parameters, so a missing argument is a TypeError.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import app.services.notifications as notifications

APP_DIR = Path(__file__).resolve().parent.parent / "app"
REQUIRED_KWARGS = ("tenant_id", "db")


def _called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _notify_calls():
    """Yield (relative_path, line, function_name, call_node) for every
    notify_*(...) call under app/."""
    for path in sorted(APP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _called_name(node)
                if name and name.startswith("notify_"):
                    yield path.relative_to(APP_DIR.parent), node.lineno, name, node


def test_static_check_finds_the_known_call_sites():
    """Guard the guard: if the walker finds nothing, test 1 passes vacuously."""
    files = {str(path) for path, _, _, _ in _notify_calls()}
    assert "app/api/bookings.py" in files
    assert "app/api/job_orders.py" in files
    assert "app/services/scheduler.py" in files


def test_every_notify_call_passes_tenant_id_and_db():
    problems = []
    for path, line, name, call in _notify_calls():
        # **kwargs would hide what is passed — require the names spelled out.
        passed = {kw.arg for kw in call.keywords if kw.arg is not None}
        missing = [k for k in REQUIRED_KWARGS if k not in passed]
        if missing:
            problems.append(f"{path}:{line} {name}() is missing {', '.join(missing)}")

    assert not problems, (
        "notify_* call sites must pass tenant_id= and db= explicitly:\n  "
        + "\n  ".join(problems)
    )


def test_every_notify_function_requires_tenant_id_and_db():
    functions = {
        name: fn
        for name, fn in inspect.getmembers(notifications, inspect.isfunction)
        if name.startswith("notify_") and fn.__module__ == notifications.__name__
    }
    assert len(functions) >= 11, f"expected the notify_* functions, found {sorted(functions)}"

    problems = []
    for name, fn in sorted(functions.items()):
        params = inspect.signature(fn).parameters
        for required in REQUIRED_KWARGS:
            param = params.get(required)
            if param is None:
                problems.append(f"{name}() has no `{required}` parameter")
            elif param.default is not inspect.Parameter.empty:
                problems.append(f"{name}() gives `{required}` a default ({param.default!r})")
            elif param.kind is not inspect.Parameter.KEYWORD_ONLY:
                problems.append(f"{name}() does not make `{required}` keyword-only")

    assert not problems, "\n  ".join(["notify_* signatures:"] + problems)
