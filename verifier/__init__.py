"""The deterministic verifier: each tool's checks, and the task's, on contract instances."""

from contract import Task, Tool

from . import audit

# tool -> (verify_input(value), verify_output(input_value, output_value, workspace))
TOOLS = {
    Tool.GET_CATALOG: (audit.verify_audit_input, lambda given, made, workspace: audit.verify_catalog_output(given, made)),
    Tool.GET_TRANSCRIPT: (audit.verify_audit_input, lambda given, made, workspace: audit.verify_transcript_output(given, made)),
    Tool.PIN_AUDIT: (audit.verify_audit_input, lambda given, made, workspace: audit.verify_pin_output(given, made)),
}
# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.AUDIT_DEGREE: audit.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)][0](value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)][1](input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
