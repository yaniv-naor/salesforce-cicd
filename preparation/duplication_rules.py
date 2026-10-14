"""
Duplication Rules preparation module.

This module contains the logic required to update Salesforce
Duplicate Rule XML files before validation or deployment.

The configuration determines which Duplicate Rule XML files
should be processed and what sortOrder value should be applied.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from utils.logger import get_logger


# Salesforce Metadata API XML namespace.
SALESFORCE_NAMESPACE = {
    "sf": "http://soap.sforce.com/2006/04/metadata"
}


# Preserve the Salesforce XML namespace when writing the XML file.
ET.register_namespace(
    "",
    "http://soap.sforce.com/2006/04/metadata"
)


def process_duplication_rules(project_root, duplication_rules_config):
    """
    Update the sortOrder of configured Salesforce Duplicate Rules.

    Each configuration entry defines:
        - fileName: Duplicate Rule XML file to process.
        - sortOrder: New value for the last sortOrder element.

    Only the files explicitly defined in the configuration are processed.

    Args:
        project_root (str | Path):
            Path to the Salesforce project root.

        duplication_rules_config (list):
            Duplicate Rules configuration entries.

    Raises:
        ValueError:
            If the configuration structure is invalid or the XML does not
            contain a sortOrder element.

        FileNotFoundError:
            If a configured Duplicate Rule XML file does not exist.

        ET.ParseError:
            If a Duplicate Rule XML file contains invalid XML.
    """

    # Get the centralized CI/CD logger.
    logger = get_logger()

    # Convert the project root to a Path object so that all file paths
    # are resolved relative to the Salesforce project.
    project_root = Path(project_root)

    # Validate that the configuration is a list.
    if not isinstance(duplication_rules_config, list):
        raise ValueError(
            "'duplicationRule' must be a list."
        )

    # Nothing needs to be processed when the list is empty.
    if not duplication_rules_config:
        logger.info(
            "No Duplicate Rules configured."
        )
        return

    logger.info(
        "Duplication Rules preparation started."
    )

    # Process every Duplicate Rule explicitly configured in the JSON.
    for duplicate_rule in duplication_rules_config:

        # Validate the individual configuration entry.
        if not isinstance(duplicate_rule, dict):
            raise ValueError(
                "Each 'duplicationRule' entry must be an object."
            )

        # Read the configured XML filename.
        file_name = duplicate_rule.get("fileName")

        if not isinstance(file_name, str) or not file_name.strip():
            raise ValueError(
                "Each 'duplicationRule' entry must contain "
                "a valid 'fileName'."
            )

        # Read the new sortOrder value.
        sort_order = duplicate_rule.get("sortOrder")

        if not isinstance(sort_order, int):
            raise ValueError(
                f"'sortOrder' must be an integer for "
                f"Duplicate Rule '{file_name}'."
            )

        # Build the complete path to the Duplicate Rule XML file.
        duplicate_rule_path = (
            project_root
            / "force-app"
            / "main"
            / "default"
            / "duplicateRules"
            / file_name
        )

        # Stop the preparation stage if the configured file is missing.
        if not duplicate_rule_path.is_file():
            raise FileNotFoundError(
                f"Duplicate Rule file not found: "
                f"{duplicate_rule_path}"
            )

        logger.info(
            f"Processing Duplicate Rule file: {file_name}"
        )

        # Read the Duplicate Rule XML file.
        tree = ET.parse(duplicate_rule_path)
        root = tree.getroot()

        # Find all sortOrder elements in the Duplicate Rule.
        sort_orders = root.findall(
            ".//sf:sortOrder",
            SALESFORCE_NAMESPACE
        )

        # The original implementation updates the last sortOrder element.
        if not sort_orders:
            raise ValueError(
                f"Duplicate Rule '{file_name}' does not contain "
                "a 'sortOrder' element."
            )

        # Select the last sortOrder element, preserving the original
        # behavior of the existing manipulation script.
        last_sort_order = sort_orders[-1]

        # Store the new configured sortOrder value in the XML element.
        last_sort_order.text = str(sort_order)

        # Save the updated XML file.
        tree.write(
            duplicate_rule_path,
            encoding="UTF-8",
            xml_declaration=True
        )

        logger.info(
            f"Updated 'sortOrder' in '{file_name}' "
            f"to '{sort_order}'."
        )

        logger.info(
            f"Duplicate Rule file updated: "
            f"{duplicate_rule_path}"
        )

    logger.info(
        "Duplication Rules preparation completed successfully."
    )