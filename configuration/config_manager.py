"""
Project configuration management module.

This module is responsible for applying CI/CD variables to the
Salesforce project's configuration files.
"""

import json
from pathlib import Path

from utils.logger import get_logger


def apply_auth_url(project_root, auth_url):
    """
    Apply the Salesforce authentication URL to the project's config.json.

    The function reads the existing Salesforce project configuration,
    replaces the #{auth_url}# placeholder in the sfdxAuthUrl property,
    and saves the updated configuration back to the project.

    Args:
        project_root (str | Path):
            Path to the Salesforce project root.

        auth_url (str):
            Salesforce authentication URL received from the CI/CD
            environment.

    Raises:
        FileNotFoundError:
            If config/config.json does not exist.

        ValueError:
            If the configuration structure is invalid.

        json.JSONDecodeError:
            If config.json contains invalid JSON.
    """

    # Get the centralized logger.
    logger = get_logger()

    # Convert the project root to a Path object.
    project_root = Path(project_root)

    # Locate the Salesforce project configuration file.
    config_file = project_root / "config" / "config.json"

    # Make sure the configuration file exists.
    if not config_file.is_file():
        raise FileNotFoundError(
            f"Salesforce configuration file not found: {config_file}"
        )

    # Load the existing JSON configuration.
    with config_file.open("r", encoding="utf-8") as file:
        config = json.load(file)

    # Make sure the expected authentication property exists.
    if "sfdxAuthUrl" not in config:
        raise ValueError(
            f"Missing 'sfdxAuthUrl' property in {config_file}"
        )

    # Make sure the authentication property contains a string.
    if not isinstance(config["sfdxAuthUrl"], str):
        raise ValueError(
            f"'sfdxAuthUrl' must be a string in {config_file}"
        )

    # Replace the CI/CD placeholder with the authentication URL.
    #
    # The actual authentication URL is never written to the log.
    config["sfdxAuthUrl"] = config["sfdxAuthUrl"].replace(
        "#{auth_url}#",
        auth_url
    )

    # Save the updated configuration.
    with config_file.open("w", encoding="utf-8") as file:
        json.dump(
            config,
            file,
            indent=4,
            ensure_ascii=False
        )

    # Log only the configuration file path.
    # Never log the authentication URL itself.
    logger.info(
        f"Auth URL applied to: {config_file}"
    )