"""
Salesforce deployment module.

This module provides one shared deployment mechanism for both:

- Validation
- Actual Deployment

The behavior is controlled by the validate_only parameter.

Validation:
    validate_only=True
    Adds --dry-run to the Salesforce CLI command.

Deployment:
    validate_only=False
    Performs the actual Salesforce deployment.

Both validation and deployment use --ignore-conflicts.

The authenticated Salesforce Org is read from target_org.txt,
which is created during the authentication stage.

The Salesforce CLI command is executed through the centralized
command runner so that stdout/stderr are streamed live and the
complete output is collected for later processing.
"""

from dataclasses import dataclass
from pathlib import Path

from utils.command_runner import run_command
from utils.error_parser import parse_deployment_result
from utils.logger import get_logger


@dataclass
class DeploymentResult:
    """
    Represent the result of a Salesforce validation or deployment.

    Attributes:
        exit_code (int):
            Exit code returned by the Salesforce CLI command.

        output (str):
            Complete Salesforce CLI output from the deployment
            command.

        deployment_id (str | None):
            Salesforce deployment ID returned by the CLI.

        status (str | None):
            Salesforce deployment status.

        success (bool | None):
            Whether Salesforce reports the operation as successful.

        done (bool | None):
            Whether Salesforce reports the operation as completed.

        check_only (bool | None):
            Whether Salesforce reports the operation as validation-only.

        total_components (int | None):
            Total number of components processed.

        deployed_components (int | None):
            Number of components successfully deployed.

        component_errors (int | None):
            Number of component errors.

        test_errors (int | None):
            Number of test errors.
    """

    exit_code: int
    output: str
    deployment_id: str | None
    status: str | None
    success: bool | None
    done: bool | None
    check_only: bool | None
    total_components: int | None
    deployed_components: int | None
    component_errors: int | None
    test_errors: int | None


def deployment(project_root, validate_only=False):
    """
    Execute Salesforce validation or deployment.

    Validation and deployment intentionally use the same mechanism.
    The only difference is whether --dry-run is added to the command.

    The Salesforce CLI output from the original deployment command
    is used directly for result processing. No additional Salesforce
    deployment report command is executed.

    Args:
        project_root (Path):
            Root directory of the Salesforce project.

        validate_only (bool):
            True  -> Validate without deploying.
            False -> Perform the actual deployment.

    Returns:
        DeploymentResult:
            Structured Salesforce deployment result.

    Raises:
        FileNotFoundError:
            If target_org.txt does not exist.

        ValueError:
            If target_org.txt is empty.
    """

    logger = get_logger()

    project_root = Path(project_root)

    target_org_file = (
        project_root
        / "Pipeline"
        / "target_org.txt"
    )

    if not target_org_file.exists():
        raise FileNotFoundError(
            "Authenticated Salesforce Org was not found. "
            "Run the authenticate stage first."
        )

    target_org = target_org_file.read_text(
        encoding="utf-8"
    ).strip()

    if not target_org:
        raise ValueError(
            "Authenticated Salesforce Org information is empty."
        )

    command = _build_deployment_command(
        validate_only,
        target_org
    )

    if validate_only:
        logger.debug(
            "Salesforce deployment mode: validation."
        )
    else:
        logger.debug(
            "Salesforce deployment mode: deployment."
        )

    logger.debug(
        f"Salesforce target Org: {target_org}"
    )

    logger.debug(
        f"Salesforce deployment command: {' '.join(command)}"
    )

    # Execute the Salesforce CLI command and collect its complete output.
    command_result = run_command(
        command
    )

    # Parse the result directly from the original Salesforce CLI output.
    parsed_result = parse_deployment_result(
        command_result.output
    )

    return DeploymentResult(
        exit_code=command_result.exit_code,
        output=command_result.output,
        deployment_id=parsed_result["deployment_id"],
        status=parsed_result["status"],
        success=parsed_result["success"],
        done=parsed_result["done"],
        check_only=parsed_result["check_only"],
        total_components=parsed_result["total_components"],
        deployed_components=parsed_result["deployed_components"],
        component_errors=parsed_result["component_errors"],
        test_errors=parsed_result["test_errors"]
    )


def _build_deployment_command(validate_only, target_org):
    """
    Build the Salesforce CLI deployment command.

    The common deployment options are always included.

    --ignore-conflicts is intentionally included for both validation
    and actual deployment.

    Args:
        validate_only (bool):
            Whether the command should run as a validation.

        target_org (str):
            Salesforce username of the authenticated target Org.

    Returns:
        list[str]:
            Salesforce CLI command arguments.
    """

    command = [
        "sf",
        "project",
        "deploy",
        "start",
        "--source-dir",
        "force-app",
        "--test-level",
        # "RunLocalTests",
        "RunRelevantTests",
        "--target-org",
        target_org,
        "--ignore-conflicts",
        "--json"
    ]

    if validate_only:
        command.append(
            "--dry-run"
        )

    return command