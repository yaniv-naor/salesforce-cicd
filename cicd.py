"""
Main CI/CD entry point.

This module is responsible for:

1. Parsing the requested CI/CD command.
2. Initializing the centralized logger.
3. Loading and validating CI/CD environment variables.
4. Orchestrating the requested CI/CD stage.
5. Returning the appropriate CI/CD exit code.
6. Displaying a final CI/CD execution summary.

The authentication stage obtains the Salesforce username, Org ID,
and Org name of the authenticated Org and stores the username inside
the current CI/CD workspace.

Validate and Deploy use this username explicitly through the
Salesforce CLI --target-org parameter.

Validate and Deploy share the same Salesforce deployment mechanism.
The only difference is the validate_only flag passed to deployment().
"""

import sys
from pathlib import Path

from authentication.authenticate import authenticate
from configuration.config_manager import apply_auth_url
from configuration.environment import load_environment
from deployment.deployment import deployment
from preparation.prepare import prepare
from utils.error_parser import (
    parse_code_coverage_warnings,
    parse_command_error,
    parse_deployment_errors,
    parse_test_failures
)
from utils.exit_codes import (
    AUTHENTICATION_FAILED,
    CONFIGURATION_ERROR,
    DEPLOYMENT_FAILED,
    GENERAL_ERROR,
    SUCCESS,
    VALIDATION_FAILED,
)
from utils.logger import get_logger, initialize_logger


def _report_deployment_errors(stage_name, deployment_result):
    """
    Report Salesforce deployment or validation errors.

    The original deployment output is checked first.

    If no clear error can be extracted there, the deployment report
    retrieved by deployment.py is checked.

    The report can contain:

    - Component failures
    - Test failures
    - Code coverage warnings

    If neither the original output nor the deployment report contains
    a clear reason, a general failure message is displayed.

    Args:
        stage_name (str):
            Name of the CI/CD stage that failed.

        deployment_result (DeploymentResult):
            Structured Salesforce deployment result.

    Returns:
        None
    """

    logger = get_logger()

    logger.error(
        f"Salesforce {stage_name} failed."
    )

    # ------------------------------------------------------------
    # FIRST: CHECK THE ORIGINAL DEPLOYMENT OUTPUT
    # ------------------------------------------------------------

    deployment_errors = parse_deployment_errors(
        deployment_result.output
    )

    if deployment_errors:
        _display_component_errors(
            logger,
            deployment_errors
        )
        return

    test_failures = parse_test_failures(
        deployment_result.output
    )

    if test_failures:
        _display_test_failures(
            logger,
            test_failures
        )
        return

    coverage_warnings = parse_code_coverage_warnings(
        deployment_result.output
    )

    if coverage_warnings:
        _display_coverage_warnings(
            logger,
            coverage_warnings
        )
        return

    command_error = parse_command_error(
        deployment_result.output
    )

    if _has_meaningful_command_error(
        command_error,
        deployment_result.output
    ):
        _display_command_error(
            logger,
            command_error
        )
        return

    # ------------------------------------------------------------
    # SECOND: CHECK THE DEPLOYMENT REPORT
    # ------------------------------------------------------------

    if deployment_result.report_output:

        logger.debug(
            "Analyzing Salesforce deployment report."
        )

        deployment_errors = parse_deployment_errors(
            deployment_result.report_output
        )

        if deployment_errors:
            _display_component_errors(
                logger,
                deployment_errors
            )
            return

        test_failures = parse_test_failures(
            deployment_result.report_output
        )

        if test_failures:
            _display_test_failures(
                logger,
                test_failures
            )
            return

        coverage_warnings = parse_code_coverage_warnings(
            deployment_result.report_output
        )

        if coverage_warnings:
            _display_coverage_warnings(
                logger,
                coverage_warnings
            )
            return

        report_error = parse_command_error(
            deployment_result.report_output
        )

        if _has_meaningful_command_error(
            report_error,
            deployment_result.report_output
        ):
            _display_command_error(
                logger,
                report_error
            )
            return

    # ------------------------------------------------------------
    # LAST FALLBACK
    # ------------------------------------------------------------

    logger.error(
        "Salesforce deployment failed, but no specific "
        "error information was available."
    )


def _display_component_errors(logger, errors):
    """
    Display Salesforce component failures.
    """

    logger.info(
        "Failed components:"
    )

    for error in errors:

        logger.info(
            f"  • {error['component_type']}: "
            f"{error['full_name']}"
        )

        logger.info(
            f"    {error['message']}"
        )

        logger.info("")


def _display_test_failures(logger, failures):
    """
    Display Salesforce test failures.
    """

    logger.info(
        "Failed tests:"
    )

    for failure in failures:

        logger.info(
            f"  • {failure['name']}"
        )

        if failure["method"] != "Unknown":
            logger.info(
                f"    Method: {failure['method']}"
            )

        logger.info(
            f"    {failure['message']}"
        )

        logger.info("")


def _display_coverage_warnings(logger, warnings):
    """
    Display Salesforce code coverage warnings.
    """

    logger.info(
        "Code coverage:"
    )

    for warning in warnings:
        logger.info(
            f"  • {warning}"
        )

    logger.info("")


def _display_command_error(logger, error):
    """
    Display a structured Salesforce CLI command error.
    """

    if error["code"]:
        logger.error(
            f"Code: {error['code']}"
        )

    logger.error(
        f"Message: {error['message']}"
    )


def _has_meaningful_command_error(error, output):
    """
    Determine whether a parsed command error contains a useful
    human-readable explanation.

    A raw JSON response that only reports status=Failed is not
    considered a meaningful error.
    """

    message = error.get(
        "message"
    )

    if not message:
        return False

    message = message.strip()
    output = (output or "").strip()

    if not message:
        return False

    if message == output:
        try:
            import json

            data = json.loads(
                output
            )

        except json.JSONDecodeError:
            return True

        result = (
            data.get("result")
            if isinstance(data, dict)
            else None
        )

        if isinstance(result, dict):
            if result.get("message"):
                return True

            return False

    return True


def _display_final_summary(
    stage_name,
    exit_code,
    deployment_result=None
):
    """
    Display the final summary of the CI/CD execution.

    The summary provides a concise result for the user while the
    detailed execution information remains available in cicd.log.

    When a Salesforce deployment result is available, the summary
    also displays the Deployment ID and component statistics.

    Args:
        stage_name (str):
            Name of the executed CI/CD stage.

        exit_code (int):
            Final CI/CD exit code.

        deployment_result (DeploymentResult | None):
            Structured Salesforce deployment result when the stage
            is validate or deploy.

    Returns:
        None
    """

    logger = get_logger()

    status = (
        "SUCCESS"
        if exit_code == SUCCESS
        else "FAILED"
    )

    logger.info(
        "============================================================"
    )

    logger.info(
        f"Status: {status}"
    )

    logger.info(
        f"Stage: {stage_name}"
    )

    logger.info(
        f"Exit Code: {exit_code}"
    )

    if deployment_result is not None:

        if deployment_result.deployment_id:
            logger.info(
                f"Deployment ID: "
                f"{deployment_result.deployment_id}"
            )

        if (
            deployment_result.total_components is not None
            and deployment_result.deployed_components is not None
        ):
            logger.info(
                "Components: "
                f"{deployment_result.deployed_components} / "
                f"{deployment_result.total_components}"
            )

        if deployment_result.component_errors is not None:
            logger.info(
                f"Errors: "
                f"{deployment_result.component_errors}"
            )

    logger.info(
        "============================================================"
    )


def validate(project_root):
    """
    Execute the Salesforce validation stage.
    """

    logger = get_logger()

    result = deployment(
        project_root,
        validate_only=True
    )

    if result.exit_code == SUCCESS:

        logger.info(
            "Salesforce validation completed successfully."
        )

        _display_final_summary(
            "Validation",
            SUCCESS,
            result
        )

        return SUCCESS

    _report_deployment_errors(
        "validation",
        result
    )

    _display_final_summary(
        "Validation",
        VALIDATION_FAILED,
        result
    )

    return VALIDATION_FAILED


def deploy(project_root):
    """
    Execute the Salesforce deployment stage.
    """

    logger = get_logger()

    result = deployment(
        project_root,
        validate_only=False
    )

    if result.exit_code == SUCCESS:

        logger.info(
            "Salesforce deployment completed successfully."
        )

        _display_final_summary(
            "Deployment",
            SUCCESS,
            result
        )

        return SUCCESS

    _report_deployment_errors(
        "deployment",
        result
    )

    _display_final_summary(
        "Deployment",
        DEPLOYMENT_FAILED,
        result
    )

    return DEPLOYMENT_FAILED


def main():
    """
    Parse the requested command and execute the corresponding CI/CD stage.

    Returns:
        int:
            Final CI/CD exit code.
    """

    valid_commands = {
        "authenticate",
        "prepare",
        "validate",
        "deploy"
    }

    if len(sys.argv) < 2:
        print(
            "[ERROR] No CI/CD command was provided.",
            flush=True
        )

        print(
            "[INFO] Available commands: "
            + ", ".join(sorted(valid_commands)),
            flush=True
        )

        return CONFIGURATION_ERROR

    command = sys.argv[1].lower()

    if command not in valid_commands:
        print(
            f"[ERROR] Unknown CI/CD command: {command}",
            flush=True
        )

        print(
            "[INFO] Available commands: "
            + ", ".join(sorted(valid_commands)),
            flush=True
        )

        return CONFIGURATION_ERROR

    project_root = Path(__file__).resolve().parent.parent

    log_file = Path(__file__).resolve().parent / "cicd.log"

    initialize_logger(log_file)

    logger = get_logger()

    logger.debug(
        f"Requested CI/CD command: {command}"
    )

    if command in {
        "authenticate",
        "prepare",
        "validate",
        "deploy"
    }:
        logger.info(
            "============================================================"
        )

        logger.info(
            "Salesforce CI/CD".center(60)
        )

        logger.info(
            "============================================================"
        )

    try:
        if command == "authenticate":

            logger.info(
                "AUTHENTICATION".center(60)
            )

            logger.info(
                "------------------------------------------------------------"
            )

            environment = load_environment()

            apply_auth_url(
                project_root,
                environment["auth_url"]
            )

            authentication = authenticate(
                project_root
            )

            result = authentication.command_result

            if result.exit_code != SUCCESS:
                error = parse_command_error(
                    result.output
                )

                if error["code"]:
                    logger.info(
                        f"Code: {error['code']}"
                    )

                logger.info(
                    f"Message: {error['message']}"
                )

                _display_final_summary(
                    "Authentication",
                    AUTHENTICATION_FAILED
                )

                return AUTHENTICATION_FAILED

            logger.info(
                f"Target Org Id: {authentication.org_id}"
            )

            logger.info(
                f"Target Org Name: {authentication.org_name}"
            )

            logger.info(
                f"Username: {authentication.target_org}"
            )

            _display_final_summary(
                "Authentication",
                SUCCESS
            )

            return SUCCESS

        if command == "prepare":

            logger.info(
                "PREPARATION".center(60)
            )

            logger.info(
                "------------------------------------------------------------"
            )

            environment = load_environment()

            prepare(
                project_root,
                environment["target_env"]
            )

            _display_final_summary(
                "Preparation",
                SUCCESS
            )

            return SUCCESS

        if command == "validate":

            logger.info(
                "VALIDATION".center(60)
            )

            logger.info(
                "------------------------------------------------------------"
            )

            return validate(
                project_root
            )

        if command == "deploy":

            logger.info(
                "DEPLOYMENT".center(60)
            )

            logger.info(
                "------------------------------------------------------------"
            )

            return deploy(
                project_root
            )

        return CONFIGURATION_ERROR

    except (ValueError, FileNotFoundError) as error:
        logger.error(
            "CI/CD configuration error."
        )

        logger.error(
            f"Message: {error}"
        )

        _display_final_summary(
            command.capitalize(),
            CONFIGURATION_ERROR
        )

        return CONFIGURATION_ERROR

    except Exception as error:
        logger.error(
            "Unexpected CI/CD error."
        )

        logger.error(
            f"Message: {error}"
        )

        _display_final_summary(
            command.capitalize(),
            GENERAL_ERROR
        )

        return GENERAL_ERROR


if __name__ == "__main__":
    exit_code = main()

    sys.exit(exit_code)