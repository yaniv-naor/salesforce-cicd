"""
CI/CD Engine exit codes.

This module defines the standard exit codes used by the CI/CD Engine.

Exit codes allow the CI/CD pipeline to identify the type of failure
without having to parse the console output.

The detailed error message is still printed to the console so that
the user can understand what went wrong.
"""


# The CI/CD operation completed successfully.
SUCCESS = 0


# A general error occurred that does not belong to a more specific category.
GENERAL_ERROR = 1


# Salesforce validation failed.
VALIDATION_FAILED = 2


# Salesforce deployment failed.
DEPLOYMENT_FAILED = 3


# Salesforce authentication failed.
AUTHENTICATION_FAILED = 4


# CI/CD preparation failed.
PREPARATION_FAILED = 5


# The CI/CD or Salesforce project configuration is invalid or incomplete.
CONFIGURATION_ERROR = 6