from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripted_agent import placements_from
from slimconfig import build_output, plain_output

from contract import AuditInput, AuditOutput, PinOutput, PlaceInput
from plugin import get_catalog, get_transcript, pin_audit, place_courses
from plugin.audit import audit_path


def as_sandbox(value, cls):
    """A value as NanoAgent's verifier sandbox hands it over: rebuilt from its JSON."""
    return build_output(plain_output(value) if not isinstance(value, dict) else value, cls)


def task(seed: int = 4, program: str = "cs-bs") -> AuditInput:
    return build_output({"seed": seed, "program": program}, AuditInput)


def place(given: AuditInput, placements: list[dict], workspace: Path):
    return place_courses(build_output({"task": plain_output(given), "placements": placements}, PlaceInput), workspace)


def gold(given: AuditInput) -> tuple[dict, PinOutput]:
    """A correct audit (as plain JSON), made the way the agent makes it, and the pinned answer key."""
    with tempfile.TemporaryDirectory() as folder:
        workspace = Path(folder)
        catalog = plain_output(get_catalog(given, workspace))
        transcript = plain_output(get_transcript(given, workspace))
        placed = place(given, placements_from(catalog, transcript), workspace)
        return plain_output(placed.audit), as_sandbox(pin_audit(given, workspace), PinOutput)


def verdict(given: AuditInput, audit: dict, reference: PinOutput, *, saved: dict | None = None, save: bool = True) -> dict:
    """The verdict on ``audit``, with ``saved`` (by default the audit itself) as the workspace's saved audit."""
    import verifier

    with tempfile.TemporaryDirectory() as folder:
        if save:
            path = Path(folder) / audit_path(given)
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"audit": audit if saved is None else saved}))
        return verifier.verify_task("audit-degree", given, as_sandbox(audit, AuditOutput), reference, folder)
