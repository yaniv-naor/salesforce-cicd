"""
Quick Actions preparation module.

This module contains the logic required to update Salesforce
Quick Actions of type Send Email before validation or deployment.

The configuration determines which Quick Action XML files should
be processed and which email address should be used as the
ValidatedFromAddress value.
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


def process_quick_actions_send_email(project_root, quick_actions_config):
    """
    Update Send Email Quick Actions with the configured email address.

    Each configuration entry defines:
        - filename: Quick Action XML file to process.
        - mailAddress: Email address to assign to ValidatedFromAddress.

    The function processes only the files explicitly defined in the
    configuration and does not scan all Quick Action files.

    Args:
        project_root (str | Path):
            Path to the Salesforce project root.

        quick_actions_config (dict):
            Quick Actions configuration containing the SendEmail list.

    Raises:
        ValueError:
            If the configuration structure is invalid.

        FileNotFoundError:
            If a configured Quick Action XML file does not exist.

        ET.ParseError:
            If a Quick Action XML file contains invalid XML.
    """

    # Get the centralized CI/CD logger.
    logger = get_logger()

    # Convert the project root to a Path object so that all paths
    # are resolved relative to the Salesforce project.
    project_root = Path(project_root)

    # Validate that the Quick Actions configuration is an object.
    if not isinstance(quick_actions_config, dict):
        raise ValueError(
            "'quickActions' must be an object."
        )

    # Read the Send Email configuration.
    send_email_config = quick_actions_config.get(
        "SendEmail",
        []
    )

    # The SendEmail configuration must be a list.
    if not isinstance(send_email_config, list):
        raise ValueError(
            "'quickActions.SendEmail' must be a list."
        )

    # Nothing needs to be processed when the list is empty.
    if not send_email_config:
        logger.info(
            "No Send Email Quick Actions configured."
        )
        return

    logger.info(
        "Quick Actions / Send Email preparation started."
    )

    # Process each configured Send Email Quick Action group.
    for quick_action in send_email_config:

        # Validate the individual configuration entry.
        if not isinstance(quick_action, dict):
            raise ValueError(
                "Each 'quickActions.SendEmail' entry must be an object."
            )

        # Read the configured email address.
        mail_address = quick_action.get("mailAddress")

        if not isinstance(mail_address, str) or not mail_address.strip():
            raise ValueError(
                "Each Send Email Quick Action entry must contain "
                "a valid 'mailAddress'."
            )

        # Read the list of Quick Action XML files.
        filenames = quick_action.get("files")

        if not isinstance(filenames, list):
            raise ValueError(
                "Each Send Email Quick Action entry must contain "
                "a 'files' list."
            )

        # Process every explicitly configured Quick Action file.
        for filename in filenames:

            if not isinstance(filename, str) or not filename.strip():
                raise ValueError(
                    "Each Quick Action filename must be a non-empty string."
                )

            # The filename is expected to contain the complete XML filename.
            # Example: Send_Email_To_Requester.quickAction-meta.xml
            quick_action_path = (
                project_root
                / "force-app"
                / "main"
                / "default"
                / "quickActions"
                / filename
            )

            # Stop the preparation stage if the configured file is missing.
            if not quick_action_path.is_file():
                raise FileNotFoundError(
                    f"Quick Action file not found: {quick_action_path}"
                )

            logger.info(
                f"Processing Quick Action file: {filename}"
            )

            # Read the Quick Action XML file.
            tree = ET.parse(quick_action_path)
            root = tree.getroot()

            # Track whether the expected field was found.
            field_updated = False

            # Find all fieldOverrides elements in the Quick Action.
            for field_override in root.findall(
                ".//sf:fieldOverrides",
                SALESFORCE_NAMESPACE
            ):

                # Find the field name inside the fieldOverrides element.
                field_element = field_override.find(
                    "sf:field",
                    SALESFORCE_NAMESPACE
                )

                # Ignore malformed fieldOverrides elements.
                if field_element is None:
                    continue

                # We are interested only in ValidatedFromAddress.
                if field_element.text != "ValidatedFromAddress":
                    continue

                # Find the literalValue element that contains the email.
                literal_value = field_override.find(
                    "sf:literalValue",
                    SALESFORCE_NAMESPACE
                )

                # Stop if the expected literalValue element is missing.
                if literal_value is None:
                    raise ValueError(
                        f"Quick Action '{filename}' contains a "
                        "ValidatedFromAddress fieldOverride without "
                        "a literalValue element."
                    )

                # Replace the existing value with the configured email.
                literal_value.text = mail_address

                field_updated = True

                logger.info(
                    f"Updated 'ValidatedFromAddress' in "
                    f"'{filename}' to '{mail_address}'."
                )

            # Save the XML only when the expected field was found.
            if field_updated:
                tree.write(
                    quick_action_path,
                    encoding="UTF-8",
                    xml_declaration=True
                )

                logger.info(
                    f"Quick Action file updated: "
                    f"{quick_action_path}"
                )
            else:
                raise ValueError(
                    f"Quick Action '{filename}' does not contain "
                    "a 'ValidatedFromAddress' fieldOverride."
                )

    logger.info(
        "Quick Actions / Send Email preparation "
        "completed successfully."
    )