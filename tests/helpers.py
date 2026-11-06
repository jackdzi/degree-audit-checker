from __future__ import annotations

from pathlib import Path

from scripted_agent import audit_from
from slimconfig import build_output, plain_output

from contract import AuditInput, AuditOutput, PinOutput
from plugin import get_catalog, get_transcript, pin_audit


def as_sandbox(value, cls):
    """A value as NanoAgent's verifier sandbox hands it over: rebuilt from its JSON."""
    return build_output(plain_output(value) if not isinstance(value, dict) else value, cls)


def task(seed: int = 4, program: str = "cs-bs") -> AuditInput:
    return build_output({"seed": seed, "program": program}, AuditInput)


def gold(given: AuditInput, workspace: Path = Path(".")) -> tuple[dict, PinOutput]:
    """A correct audit (as plain JSON) from the scripted agent, and the pinned answer key."""
    catalog = plain_output(get_catalog(given, workspace))
    transcript = plain_output(get_transcript(given, workspace))
    return audit_from(catalog, transcript), as_sandbox(pin_audit(given, workspace), PinOutput)


def verdict(given: AuditInput, audit: dict, reference: PinOutput) -> dict:
    import verifier

    return verifier.verify_task("audit-degree", given, as_sandbox(audit, AuditOutput), reference, ".")
