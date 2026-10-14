"""
Workflow Alerts preparation module.

This module contains the logic required to update Salesforce Workflow
Email Alerts before Salesforce validation or deployment.

The configuration explicitly defines:
    - Which Workflow file should be processed.
    - Which Email Alerts inside that file should be updated.
    - Which email address should be used as the sender address.

This prevents the Engine from scanning unrelated Workflow files.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from utils.logger import get_logger


# Salesforce Metadata API XML namespace.
SALESFORCE_NAMESPACE_URI = "http://soap.sforce.com/2006/04/metadata"

# Namespace mapping used when searching Salesforce XML elements.
SALESFORCE_NAMESPACE = {
    "sf": SALESFORCE_NAMESPACE_URI
}

# Register Salesforce's default namespace when writing XML files.
ET.register_namespace(
    "",
    SALESFORCE_NAMESPACE_URI
)


def process_workflows_alerts(project_root, workflows_config):
    """
    Update Salesforce Workflow Email Alerts according to configuration.

    Each configuration entry explicitly identifies the Workflow file that
    should be processed. The function then searches only that file for the
    configured Email Alerts.

    For every matching Email Alert:
        - senderType is changed to OrgWideEmailAddress.
        - senderAddress is created if it does not exist.
        - senderAddress is updated with the configured email address.

    Args:
        project_root (str | Path):
            Path to the Salesforce project root.

        workflows_config (dict):
            Workflow configuration containing the 'alerts' list.

    Raises:
        ValueError:
            If the configuration structure is invalid.

        FileNotFoundError:
            If the configured Workflow file does not exist.

        ET.ParseError:
            If a Workflow XML file cannot be parsed.
    """

    # Get the centralized CI/CD logger.
    logger = get_logger()

    # Convert the project root to a Path object so all path operations
    # are handled consistently across the module.
    project_root = Path(project_root)

    # Validate the top-level workflows configuration.
    if not isinstance(workflows_config, dict):
        raise ValueError("'workflows' must be an object.")

    # Extract the configured Workflow Alerts.
    alerts_config = workflows_config.get("alerts")

    # The alerts property must always be a list.
    if not isinstance(alerts_config, list):
        raise ValueError("'workflows.alerts' must be a list.")

    # Nothing needs to be processed when no Alerts are configured.
    if not alerts_config:
        logger.info(
            "No Workflow Alerts configured."
        )
        return

    # Salesforce Workflow metadata files are stored in this directory.
    workflows_directory = (
        project_root
        / "force-app"
        / "main"
        / "default"
        / "workflows"
    )

    # Make sure the expected Salesforce Workflow directory exists.
    if not workflows_directory.is_dir():
        raise FileNotFoundError(
            f"Salesforce workflows directory not found: "
            f"{workflows_directory}"
        )

    logger.info(
        "Workflow Alerts preparation started."
    )

    # Process every Workflow configuration entry independently.
    for alert_configuration in alerts_config:

        # Each configuration entry must be an object.
        if not isinstance(alert_configuration, dict):
            raise ValueError(
                "Each Workflow Alert configuration entry "
                "must be an object."
            )

        # Read the Workflow file name from the configuration.
        filename = alert_configuration.get("filename")

        # A Workflow file name is mandatory because it determines exactly
        # which XML file should be modified.
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError(
                "Each Workflow Alert configuration entry must contain "
                "a valid 'filename'."
            )

        # Read the email address that should be configured as the sender.
        mail_address = alert_configuration.get("mailAddress")

        if not isinstance(mail_address, str) or not mail_address.strip():
            raise ValueError(
                "Each Workflow Alert configuration entry must contain "
                "a valid 'mailAddress'."
            )

        # Read the list of Alert fullName values to update.
        configured_alerts = alert_configuration.get("alerts")

        if not isinstance(configured_alerts, list):
            raise ValueError(
                "'alerts' must be a list inside each Workflow "
                "Alert configuration entry."
            )

        # Every configuration entry must contain at least one Alert.
        if not configured_alerts:
            logger.info(
                f"No Alerts configured for Workflow '{filename}'."
            )
            continue

        # Resolve the configured file relative to the Salesforce Workflow
        # directory.
        workflow_file = workflows_directory / filename

        # Stop immediately if the explicitly configured file does not exist.
        if not workflow_file.is_file():
            raise FileNotFoundError(
                f"Configured Workflow file not found: {workflow_file}"
            )

        logger.info(
            f"Processing Workflow file: {workflow_file.name}"
        )

        # Parse the Workflow XML document.
        tree = ET.parse(workflow_file)

        # Get the root element of the XML document.
        root = tree.getroot()

        # Track whether this file was actually modified.
        file_changed = False

        # Find all Email Alert elements in the current Workflow file.
        workflow_alerts = root.findall(
            ".//sf:alerts",
            SALESFORCE_NAMESPACE
        )

        # Process every Alert requested by the configuration.
        for alert_name in configured_alerts:

            # Every Alert name must be a non-empty string.
            if (
                not isinstance(alert_name, str)
                or not alert_name.strip()
            ):
                raise ValueError(
                    "Each Workflow Alert name must be "
                    "a non-empty string."
                )

            # Track whether the configured Alert was found in the file.
            alert_found = False

            # Search only inside the explicitly configured Workflow file.
            for alert in workflow_alerts:

                # Read the Salesforce Alert fullName.
                full_name = alert.find(
                    "sf:fullName",
                    SALESFORCE_NAMESPACE
                )

                # Ignore malformed Alert entries without a fullName.
                if full_name is None:
                    continue

                # Continue searching when this is not the configured Alert.
                if full_name.text != alert_name:
                    continue

                alert_found = True

                # Locate the senderType element.
                sender_type = alert.find(
                    "sf:senderType",
                    SALESFORCE_NAMESPACE
                )

                # The senderType element is required for this manipulation.
                if sender_type is None:
                    raise ValueError(
                        f"Workflow Alert '{alert_name}' in "
                        f"'{workflow_file.name}' does not contain "
                        "'senderType'."
                    )

                # Salesforce requires OrgWideEmailAddress when the
                # configured sender address should be used.
                sender_type.text = "OrgWideEmailAddress"

                # Try to find an existing senderAddress element.
                sender_address = alert.find(
                    "sf:senderAddress",
                    SALESFORCE_NAMESPACE
                )

                # If senderAddress does not exist, create it using the
                # Salesforce Metadata namespace.
                if sender_address is None:
                    sender_address = ET.Element(
                        f"{{{SALESFORCE_NAMESPACE_URI}}}senderAddress"
                    )

                    # Add the new senderAddress to the Alert.
                    alert.append(sender_address)

                # Set or replace the configured sender email address.
                sender_address.text = mail_address

                # Mark the Workflow file as modified.
                file_changed = True

                logger.info(
                    f"Updated Workflow Alert "
                    f"'{alert_name}' in '{workflow_file.name}'."
                )

            # Report a configuration mismatch instead of silently
            # succeeding when the configured Alert does not exist.
            if not alert_found:
                raise ValueError(
                    f"Configured Workflow Alert '{alert_name}' "
                    f"was not found in '{workflow_file.name}'."
                )

        # Save the XML only when at least one Alert was modified.
        if file_changed:
            tree.write(
                workflow_file,
                encoding="UTF-8",
                xml_declaration=True
            )

            logger.info(
                f"Workflow file updated: {workflow_file}"
            )

    logger.info(
        "Workflow Alerts preparation completed successfully."
    )