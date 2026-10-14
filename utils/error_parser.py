"""
CI/CD error parsing utilities.

This module provides functions for extracting structured error
information from external command output.

The parser supports:

1. General command errors returned by Salesforce CLI.
2. Salesforce deployment and validation component failures.
3. Salesforce deployment result information.
4. Salesforce test failures.
5. Salesforce code coverage warnings.

Deployment failures can be returned by Salesforce CLI in different
JSON structures. The parser therefore supports both:

- result.details.components
- result.details.componentFailures

When the initial deployment output does not contain a clear reason
for failure, the deployment report can be parsed for additional
information such as:

- runTestResult.failures
- runTestResult.codeCoverageWarnings
"""

import json


def parse_command_error(output):
    """
    Extract structured error information from command output.

    This function is used for Salesforce CLI commands where the
    returned output may contain a JSON error object or plain text.

    Args:
        output (str):
            Complete command output.

    Returns:
        dict:
            Structured error information containing:
            - code
            - message
            - exit_code
    """

    output = (output or "").strip()

    if not output:
        return {
            "code": None,
            "message": "The command failed without returning an error message.",
            "exit_code": None
        }

    try:
        error_data = json.loads(output)

    except json.JSONDecodeError:
        return {
            "code": None,
            "message": output,
            "exit_code": None
        }

    if not isinstance(error_data, dict):
        return {
            "code": None,
            "message": output,
            "exit_code": None
        }

    error_code = error_data.get("name")
    error_message = error_data.get("message")
    exit_code = error_data.get("exitCode")

    if not error_message:
        result = error_data.get("result")

        if isinstance(result, dict):
            error_code = (
                error_code
                or result.get("name")
                or result.get("status")
            )

            error_message = result.get("message")

    return {
        "code": error_code,
        "message": error_message or output,
        "exit_code": exit_code
    }


def parse_deployment_result(output):
    """
    Extract the main Salesforce deployment result from CLI JSON output.

    Args:
        output (str):
            Complete JSON output returned by Salesforce CLI.

    Returns:
        dict:
            Structured deployment result.
    """

    output = (output or "").strip()

    empty_result = {
        "deployment_id": None,
        "status": None,
        "success": None,
        "done": None,
        "check_only": None,
        "total_components": None,
        "deployed_components": None,
        "component_errors": None,
        "test_errors": None
    }

    if not output:
        return empty_result

    try:
        data = json.loads(output)

    except json.JSONDecodeError:
        return empty_result

    if not isinstance(data, dict):
        return empty_result

    result = data.get("result")

    if not isinstance(result, dict):
        return empty_result

    return {
        "deployment_id": result.get("id"),
        "status": result.get("status"),
        "success": result.get("success"),
        "done": result.get("done"),
        "check_only": result.get("checkOnly"),
        "total_components": result.get(
            "numberComponentsTotal"
        ),
        "deployed_components": result.get(
            "numberComponentsDeployed"
        ),
        "component_errors": result.get(
            "numberComponentErrors"
        ),
        "test_errors": result.get(
            "numberTestErrors"
        )
    }


def parse_deployment_errors(output):
    """
    Extract Salesforce component deployment errors from JSON output.

    Supports:

        result.details.components

    and:

        result.details.componentFailures

    Args:
        output (str):
            Complete Salesforce CLI JSON output.

    Returns:
        list:
            A list of dictionaries containing:
            - component_type
            - full_name
            - message
    """

    output = (output or "").strip()

    if not output:
        return []

    try:
        data = json.loads(output)

    except json.JSONDecodeError:
        return []

    if not isinstance(data, dict):
        return []

    result = data.get("result")

    if not isinstance(result, dict):
        return []

    details = result.get("details")

    if not isinstance(details, dict):
        return []

    components = details.get("components")

    if isinstance(components, list):
        errors = _parse_failed_components(
            components
        )

        if errors:
            return errors

    component_failures = details.get(
        "componentFailures",
        []
    )

    if isinstance(component_failures, dict):
        component_failures = [component_failures]

    if not isinstance(component_failures, list):
        return []

    errors = []

    for failure in component_failures:

        if not isinstance(failure, dict):
            continue

        errors.append({
            "component_type": failure.get(
                "componentType",
                failure.get(
                    "type",
                    "Unknown"
                )
            ),
            "full_name": failure.get(
                "fullName",
                "Unknown"
            ),
            "message": failure.get(
                "problem",
                failure.get(
                    "error",
                    "Unknown Salesforce deployment error."
                )
            )
        })

    return errors


def parse_test_failures(output):
    """
    Extract Salesforce test failures from runTestResult.

    Salesforce deployment reports may contain test failures under:

        result.details.runTestResult.failures

    Args:
        output (str):
            Complete Salesforce CLI JSON output.

    Returns:
        list:
            A list of dictionaries containing:
            - name
            - method
            - message
    """

    data = _load_json(output)

    if not data:
        return []

    result = data.get("result")

    if not isinstance(result, dict):
        return []

    details = result.get("details")

    if not isinstance(details, dict):
        return []

    run_test_result = details.get(
        "runTestResult"
    )

    if not isinstance(run_test_result, dict):
        return []

    failures = run_test_result.get(
        "failures",
        []
    )

    if isinstance(failures, dict):
        failures = [failures]

    if not isinstance(failures, list):
        return []

    parsed_failures = []

    for failure in failures:

        if not isinstance(failure, dict):
            continue

        parsed_failures.append({
            "name": failure.get(
                "name",
                "Unknown"
            ),
            "method": failure.get(
                "methodName",
                failure.get(
                    "method",
                    "Unknown"
                )
            ),
            "message": failure.get(
                "message",
                failure.get(
                    "problem",
                    "Unknown Salesforce test failure."
                )
            )
        })

    return parsed_failures


def parse_code_coverage_warnings(output):
    """
    Extract Salesforce code coverage warnings.

    Salesforce deployment reports may contain coverage warnings under:

        result.details.runTestResult.codeCoverageWarnings

    Args:
        output (str):
            Complete Salesforce CLI JSON output.

    Returns:
        list[str]:
            Code coverage warning messages.
    """

    data = _load_json(output)

    if not data:
        return []

    result = data.get("result")

    if not isinstance(result, dict):
        return []

    details = result.get("details")

    if not isinstance(details, dict):
        return []

    run_test_result = details.get(
        "runTestResult"
    )

    if not isinstance(run_test_result, dict):
        return []

    warnings = run_test_result.get(
        "codeCoverageWarnings",
        []
    )

    if isinstance(warnings, str):
        return [warnings]

    if not isinstance(warnings, list):
        return []

    parsed_warnings = []

    for warning in warnings:

        if isinstance(warning, str):
            parsed_warnings.append(warning)

        elif isinstance(warning, dict):
            message = (
                warning.get("message")
                or warning.get("problem")
                or warning.get("warning")
            )

            if message:
                parsed_warnings.append(
                    message
                )

    return parsed_warnings


def has_clear_deployment_error(output):
    """
    Determine whether the deployment output already contains a
    meaningful error that can be shown to the user.

    The deployment report should only be requested when the original
    output does not provide a clear explanation.

    Args:
        output (str):
            Complete Salesforce CLI deployment output.

    Returns:
        bool:
            True when a clear deployment error was found.
            Otherwise False.
    """

    if parse_deployment_errors(output):
        return True

    if parse_test_failures(output):
        return True

    if parse_code_coverage_warnings(output):
        return True

    command_error = parse_command_error(
        output
    )

    message = command_error.get(
        "message"
    )

    if not message:
        return False

    # A raw JSON response containing only "status": "Failed"
    # is not considered a useful error message.
    if message.strip() == output.strip():
        try:
            data = json.loads(output)

        except json.JSONDecodeError:
            return bool(message.strip())

        result = (
            data.get("result")
            if isinstance(data, dict)
            else None
        )

        if isinstance(result, dict):
            result_message = result.get(
                "message"
            )

            if result_message:
                return True

            return False

    return True


def _parse_failed_components(components):
    """
    Extract failed components from the Salesforce CLI components list.

    Args:
        components (list):
            Salesforce deployment component objects.

    Returns:
        list:
            A list of normalized deployment errors.
    """

    errors = []

    for component in components:

        if not isinstance(component, dict):
            continue

        state = str(
            component.get(
                "state",
                ""
            )
        ).lower()

        if state != "failed":
            continue

        component_type = (
            component.get("type")
            or component.get("componentType")
            or "Unknown"
        )

        full_name = (
            component.get("fullName")
            or "Unknown"
        )

        message = (
            component.get("error")
            or component.get("problem")
            or "Unknown Salesforce deployment error."
        )

        errors.append({
            "component_type": component_type,
            "full_name": full_name,
            "message": message
        })

    return errors


def _load_json(output):
    """
    Safely parse JSON command output.

    Args:
        output (str):
            Command output.

    Returns:
        dict | None:
            Parsed JSON object or None when parsing fails.
    """

    output = (output or "").strip()

    if not output:
        return None

    try:
        data = json.loads(output)

    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    return data