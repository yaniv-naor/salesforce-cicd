"""
Salesforce authentication module.

This module contains the logic required to authenticate against a
Salesforce organization using the authentication information stored
in the project's config directory.

After successful authentication, the Salesforce username returned by
Salesforce CLI is stored as the target Org identifier for subsequent
Validate and Deploy operations.

The username is stored inside the current CI/CD workspace so that
separate commands can reuse it without relying on a Salesforce CLI
default Org.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from utils.command_runner import CommandResult, run_command


@dataclass
class AuthenticationResult:
    """
    Represent the result of Salesforce authentication.

    Attributes:
        command_result (CommandResult):
            Result returned by the Salesforce CLI authentication command.

        target_org (str):
            Salesforce username returned by the CLI. This value identifies
            the authenticated Org and is used later as --target-org.

        org_id (str):
            Salesforce Org ID returned by the CLI.

        org_name (str):
            Salesforce Org name returned by the CLI.
    """

    command_result: CommandResult
    target_org: str
    org_id: str
    org_name: str


def authenticate(project_root):
    """
    Authenticate to the Salesforce organization.

    The Salesforce project's existing config/config.json file is used as
    the source for the SFDX authentication URL, preserving the current
    project structure.

    The Salesforce CLI default Org mechanism is intentionally not used.
    This prevents concurrent CI/CD jobs running on the same server from
    interfering with each other.

    After successful authentication, the Salesforce username returned by
    the CLI is saved inside the main directory so that subsequent
    commands can explicitly target the same Org.

    Args:
        project_root (str | Path):
            Path to the root directory of the Salesforce project.

    Returns:
        AuthenticationResult:
            Result returned by the Salesforce CLI command together with
            the authenticated Org username, Org ID, and Org name.

    Raises:
        FileNotFoundError:
            If config/config.json does not exist.

        ValueError:
            If Salesforce CLI succeeds but does not return valid
            authentication or Org information.
    """

    # Convert the project root to a Path object.
    project_root = Path(project_root)

    # Locate the Salesforce project configuration file.
    config_file = project_root / "config" / "config.json"

    # Make sure the Salesforce project configuration exists before
    # attempting authentication.
    if not config_file.is_file():
        raise FileNotFoundError(
            f"Salesforce configuration file not found: {config_file}"
        )

    # Build the Salesforce CLI authentication command.
    #
    # We intentionally do NOT use:
    #     --set-default
    #     --set-default-dev-hub
    #
    # The CI/CD process must not depend on a shared Salesforce CLI
    # default Org because multiple jobs may run concurrently.
    command = [
        "sf",
        "org",
        "login",
        "sfdx-url",
        "--sfdx-url-file",
        str(config_file),
        "--json"
    ]

    # Execute the authentication command through the centralized
    # command runner.
    command_result = run_command(command)

    # Authentication failed.
    #
    # Return the original command result so that cicd.py can parse
    # the Salesforce CLI error and return the correct CI/CD exit code.
    if command_result.exit_code != 0:
        return AuthenticationResult(
            command_result=command_result,
            target_org="",
            org_id="",
            org_name=""
        )

    # Parse the successful Salesforce CLI JSON response.
    try:
        authentication_data = json.loads(
            command_result.output
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "Salesforce authentication succeeded, but the Salesforce CLI "
            "returned invalid JSON output."
        ) from error

    # Salesforce CLI places the authentication result inside the
    # "result" property when --json is used.
    result_data = authentication_data.get(
        "result",
        {}
    )

    # Extract the Salesforce Org information returned by the CLI.
    target_org = result_data.get("username")
    org_id = result_data.get("orgId")
    org_name = result_data.get("name")

    # Make sure the username was returned and contains a valid value.
    if not isinstance(target_org, str) or not target_org.strip():
        raise ValueError(
            "Salesforce authentication succeeded, but the Salesforce CLI "
            "did not return a valid Salesforce username."
        )

    # Make sure the Org ID was returned and contains a valid value.
    if not isinstance(org_id, str) or not org_id.strip():
        raise ValueError(
            "Salesforce authentication succeeded, but the Salesforce CLI "
            "did not return a valid Org ID."
        )

    # Make sure the Org name was returned and contains a valid value.
    if not isinstance(org_name, str) or not org_name.strip():
        raise ValueError(
            "Salesforce authentication succeeded, but the Salesforce CLI "
            "did not return a valid Org name."
        )

    # Normalize whitespace before storing and returning the values.
    target_org = target_org.strip()
    org_id = org_id.strip()
    org_name = org_name.strip()

    # Store the target Org identifier inside the current CI/CD workspace.
    #
    # This file belongs to the current job workspace.
    # Different concurrent jobs therefore have different target_org.txt files.
    target_org_file = (
        project_root
        / "target_org.txt"
    )
    # Make sure the workspace directory exists.
    target_org_file.parent.mkdir(
    parents=True,
    exist_ok=True
    )

    # Write only the Salesforce username.
    #
    # The username is an identifier and is not an authentication secret.
    target_org_file.write_text(
        target_org,
        encoding="utf-8"
    )

    # Return the command result and the authenticated Org information.
    return AuthenticationResult(
        command_result=command_result,
        target_org=target_org,
        org_id=org_id,
        org_name=org_name
    )