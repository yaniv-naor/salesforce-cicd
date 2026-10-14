"""
Environment configuration module.

This module is responsible for reading CI/CD environment variables
and validating that all required variables are available.
"""

import os


def get_required_variable(name):
    """
    Read a required environment variable and validate that it exists.

    Args:
        name (str): Name of the environment variable.

    Returns:
        str: Value of the environment variable.

    Raises:
        ValueError: If the variable does not exist or is empty.
    """

    # Read the requested environment variable.
    value = os.getenv(name)

    # Stop the CI/CD process when the variable is missing or empty.
    if not value or not value.strip():
        raise ValueError(
            f"Required environment variable '{name}' is missing or empty."
        )

    return value


def load_environment():
    """
    Load and validate all CI/CD environment variables required by the Engine.

    Returns:
        dict: Validated environment configuration.

    Raises:
        ValueError: If SF_TARGET_ENV contains an unsupported environment.
    """

    # Read the Salesforce authentication URL from the CI/CD environment.
    auth_url = get_required_variable("auth_url")

    # Read the target Salesforce environment from the CI/CD environment.
    target_env = get_required_variable("SF_TARGET_ENV").lower()

    # Define the environments supported by the CI/CD Engine.
    allowed_environments = {
        "dev",
        "test",
        "prod"
    }

    # Prevent the Engine from loading an invalid before-deploy configuration.
    if target_env not in allowed_environments:
        raise ValueError(
            f"Invalid SF_TARGET_ENV '{target_env}'. "
            f"Allowed values are: {', '.join(sorted(allowed_environments))}."
        )

    # Return all validated environment values to the Engine.
    return {
        "auth_url": auth_url,
        "target_env": target_env
    }