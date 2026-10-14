"""
Salesforce project preparation module.

This module is responsible for loading the environment-specific
before-deploy configuration and orchestrating all preparation
manipulations in the required order.

Preparation order:
    1. File Replacement
    2. Workflow Alerts
    3. Quick Actions / Send Email
    4. Duplication Rules

The actual manipulation logic is implemented in separate modules.
This module only loads the configuration and orchestrates execution.
"""

import json
from pathlib import Path

from preparation.file_replacement import process_files_replacement
from preparation.workflows import process_workflows_alerts
from preparation.quick_actions import process_quick_actions_send_email
from preparation.duplication_rules import process_duplication_rules
from utils.logger import get_logger


def load_before_deploy_config(project_root, target_env):
    """
    Load the before-deploy configuration for the target environment.

    The configuration file is expected to be located inside the
    Salesforce project's config directory and follow this naming pattern:

        before-deploy-{environment}.json

    The configuration file is optional:
        - If the file does not exist, preparation is skipped.
        - If the file exists but is empty, preparation is skipped.
        - If the file exists and contains valid JSON, the configuration
          is returned for processing.

    Args:
        project_root (str | Path):
            Path to the Salesforce project root.

        target_env (str):
            Target environment, for example 'dev', 'test', or 'prod'.

    Returns:
        dict or None:
            Parsed before-deploy configuration when available.
            None when the configuration file does not exist or is empty.

    Raises:
        ValueError:
            If the configuration file contains invalid JSON or does not
            contain a JSON object.
    """

    # Get the centralized logger.
    logger = get_logger()

    # Convert the project root to a Path object.
    project_root = Path(project_root)

    # Build the environment-specific configuration filename.
    config_filename = f"before-deploy-{target_env}.json"

    # Locate the configuration file.
    config_file = project_root / "config" / config_filename

    # ------------------------------------------------------------
    # OPTIONAL CONFIGURATION FILE
    # ------------------------------------------------------------

    # The before-deploy configuration is optional.
    # If it does not exist, there is simply nothing to prepare.
    if not config_file.is_file():
        logger.info(
            f"Before-deploy configuration file not found: {config_file}. "
            "Preparation configuration will be skipped."
        )
        return None

    # Log the configuration file being loaded.
    logger.info(
        f"Loading before-deploy configuration: {config_file}"
    )

    # Read the configuration file as text first so that an empty file
    # can be handled as a valid "nothing to prepare" scenario.
    configuration_text = config_file.read_text(
        encoding="utf-8"
    )

    # An existing but empty/whitespace-only file means there is no
    # preparation configuration to execute.
    if not configuration_text.strip():
        logger.info(
            f"Before-deploy configuration file is empty: {config_file}. "
            "Preparation configuration will be skipped."
        )
        return None

    # ------------------------------------------------------------
    # JSON CONFIGURATION
    # ------------------------------------------------------------

    # Parse the JSON configuration.
    try:
        configuration = json.loads(configuration_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Invalid JSON in before-deploy configuration: "
            f"{config_file}. {error}"
        ) from error

    # Make sure the root configuration is a JSON object.
    if not isinstance(configuration, dict):
        raise ValueError(
            "Before-deploy configuration must be a JSON object: "
            f"{config_file}"
        )

    # Log successful configuration loading.
    logger.info(
        "Before-deploy configuration loaded successfully "
        f"for environment '{target_env}'."
    )

    return configuration


def prepare(project_root, target_env):
    """
    Execute all configured preparation manipulations.

    The preparation stages are executed in a fixed order so that the
    Salesforce project is transformed consistently before validation
    or deployment.

    If the environment-specific before-deploy configuration does not
    exist or is empty, preparation is skipped successfully.

    Execution order:
        1. File Replacement
        2. Workflow Alerts
        3. Quick Actions / Send Email
        4. Duplication Rules

    Args:
        project_root (str | Path):
            Path to the Salesforce project root.

        target_env (str):
            Target environment, for example 'dev', 'test', or 'prod'.
    """

    # Get the centralized logger.
    logger = get_logger()

    # Convert the project root to a Path object.
    project_root = Path(project_root)

    # Load the environment-specific preparation configuration.
    configuration = load_before_deploy_config(
        project_root,
        target_env
    )

    # If there is no configuration file or the file is empty,
    # there is nothing to prepare.
    if configuration is None:
        logger.info(
            "No before-deploy configuration to process. "
            "Preparation completed successfully."
        )
        return

    # ------------------------------------------------------------
    # STEP 1 - FILE REPLACEMENT
    # ------------------------------------------------------------

    logger.info(
        "Step 1/4 - File Replacement"
    )

    # Read the file replacement configuration.
    files_replacement = configuration.get(
        "filesReplacement",
        []
    )

    # Execute the configured file replacements.
    process_files_replacement(
        project_root,
        files_replacement
    )

    # ------------------------------------------------------------
    # STEP 2 - WORKFLOW ALERTS
    # ------------------------------------------------------------

    logger.info(
        "Step 2/4 - Workflow Alerts"
    )

    # Read the workflow configuration.
    workflows_config = configuration.get(
        "workflows",
        {}
    )

    # Execute the configured workflow manipulations.
    process_workflows_alerts(
        project_root,
        workflows_config
    )

    # ------------------------------------------------------------
    # STEP 3 - QUICK ACTIONS / SEND EMAIL
    # ------------------------------------------------------------

    logger.info(
        "Step 3/4 - Quick Actions / Send Email"
    )

    # Read the Quick Actions configuration.
    quick_actions_config = configuration.get(
        "quickActions",
        {}
    )

    # Execute the configured Quick Action manipulations.
    process_quick_actions_send_email(
        project_root,
        quick_actions_config
    )

    # ------------------------------------------------------------
    # STEP 4 - DUPLICATION RULES
    # ------------------------------------------------------------

    logger.info(
        "Step 4/4 - Duplication Rules"
    )

    # Read the Duplicate Rule configuration.
    duplication_rules_config = configuration.get(
        "duplicationRule",
        []
    )

    # Execute the configured Duplicate Rule manipulations.
    process_duplication_rules(
        project_root,
        duplication_rules_config
    )

    logger.info(
        "Preparation completed successfully."
    )