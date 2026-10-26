"""
File replacement preparation module.

This module contains the logic required to replace project files before
Salesforce validation or deployment.
"""

import shutil
from pathlib import Path

from utils.logger import get_logger
from utils.path_security import resolve_within


def process_files_replacement(project_root, files_replacement):
    """
    Replace project files according to the File Replacement configuration.

    Each configuration entry defines a source file and a target file.
    Both paths are resolved relative to the Salesforce project root.

    Args:
        project_root (str | Path):
            Path to the Salesforce project root.

        files_replacement (list):
            File replacement configuration entries.

    Raises:
        ValueError:
            If the configuration structure is invalid.

        FileNotFoundError:
            If a configured source file does not exist.
    """

    # Get the centralized logger.
    logger = get_logger()

    # Convert the project root to a Path object.
    project_root = Path(project_root)

    # Validate the configuration type.
    if not isinstance(files_replacement, list):
        raise ValueError(
            "'filesReplacement' must be a list."
        )

    # Nothing needs to be done when no files are configured.
    if not files_replacement:
        logger.info(
            "No files configured for replacement."
        )
        return

    # Log the beginning of the preparation operation.
    logger.info(
        "File Replacement preparation started."
    )

    # Process every configured replacement.
    for replacement in files_replacement:

        # Validate each configuration entry.
        if not isinstance(replacement, dict):
            raise ValueError(
                "Each 'filesReplacement' entry must be an object."
            )

        # Read the source and target paths.
        source_file = replacement.get("sourceFile")
        target_file = replacement.get("targetFile")

        # Validate the source path.
        if not isinstance(source_file, str) or not source_file.strip():
            raise ValueError(
                "Each 'filesReplacement' entry must contain "
                "a valid 'sourceFile'."
            )

        # Validate the target path.
        if not isinstance(target_file, str) or not target_file.strip():
            raise ValueError(
                "Each 'filesReplacement' entry must contain "
                "a valid 'targetFile'."
            )

        # Resolve both configured paths and reject absolute paths, traversal,
        # and symlinks that escape the Salesforce project root.
        source_path = resolve_within(
            project_root,
            source_file,
            "File replacement sourceFile"
        )
        target_path = resolve_within(
            project_root,
            target_file,
            "File replacement targetFile"
        )

        # Make sure the source file exists.
        if not source_path.is_file():
            raise FileNotFoundError(
                f"Source file for replacement not found: {source_path}"
            )

        # Make sure the target directory exists.
        target_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Replace the target file with the source file.
        shutil.copyfile(
            source_path,
            target_path
        )

        # Log the completed replacement.
        logger.info(
            f"Replaced '{source_file}' with '{target_file}'."
        )

    # Log successful completion.
    logger.info("")

    logger.info(
        "File Replacement preparation completed successfully."
    )