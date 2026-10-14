"""
CI/CD Engine logging module.

This module provides centralized logging for the CI/CD Engine.

The logger writes output to two destinations:

1. Console:
   User-friendly output with clear sections, colors and symbols.

2. Log file:
   Full technical logging including DEBUG messages and detailed
   command output.

The log file is overwritten at the beginning of every CI/CD run.
"""

import logging
import os
import re
from pathlib import Path


# Name of the logger used by the CI/CD Engine.
LOGGER_NAME = "salesforce_cicd"


# ANSI colors used only for terminal output.
COLOR_RESET = "\033[0m"
COLOR_BLUE = "\033[94m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_GRAY = "\033[90m"


def enable_windows_terminal_colors():
    """
    Enable ANSI color support in Windows terminals when possible.

    Modern Windows terminals normally support ANSI escape sequences.
    This function enables virtual terminal processing for older Windows
    console environments when possible.

    No exception is raised if color support cannot be enabled.
    """

    # Color handling is only required on Windows.
    if os.name != "nt":
        return

    try:
        # Import ctypes only when running on Windows.
        import ctypes

        # Access the Windows kernel API.
        kernel32 = ctypes.windll.kernel32

        # Get the standard output console handle.
        stdout_handle = kernel32.GetStdHandle(-11)

        # Store the current console mode.
        mode = ctypes.c_uint32()

        # Read the current console mode.
        if kernel32.GetConsoleMode(
            stdout_handle,
            ctypes.byref(mode)
        ):
            # Windows flag that enables ANSI escape sequences.
            enable_virtual_terminal_processing = 0x0004

            # Enable ANSI color support without removing
            # the existing console mode flags.
            kernel32.SetConsoleMode(
                stdout_handle,
                mode.value | enable_virtual_terminal_processing
            )

    except Exception:
        # Terminal colors are optional.
        # Failure to enable them must never stop the CI/CD Engine.
        pass


def colorize(text, color):
    """
    Apply a terminal color to the supplied text.

    Args:
        text (str):
            Text to color.

        color (str):
            ANSI color escape sequence.

    Returns:
        str:
            Colored text.
    """

    return f"{color}{text}{COLOR_RESET}"


def format_console_message(level, message):
    """
    Convert a technical log message into user-friendly terminal output.

    The technical log file is not affected by this formatting.

    Args:
        level (int):
            Logging level of the message.

        message (str):
            Original log message.

    Returns:
        str:
            Formatted terminal message.
    """

    # ------------------------------------------------------------
    # LOGGER INITIALIZATION
    # ------------------------------------------------------------

    # This message is useful in the technical log but does not need
    # to appear in the user-facing terminal.
    if message == "CI/CD logging initialized.":
        return ""

    # ------------------------------------------------------------
    # ENGINE HEADER
    # ------------------------------------------------------------

    # Keep the separator lines and title visible in the terminal.
    if message == "============================================================":
        return colorize(
            message,
            COLOR_BLUE
        )

    if message == "                    Salesforce CI/CD Engine":
        return colorize(
            message,
            COLOR_BLUE
        )

    # ------------------------------------------------------------
    # SALESFORCE CLI COMMAND
    # ------------------------------------------------------------

    # Display the full Salesforce CLI command in yellow so that
    # the exact command being executed is easy to identify.
    if message.startswith("Command: "):
        return colorize(
            f"{message}",
            COLOR_YELLOW
        )

    # ------------------------------------------------------------
    # FINAL CI/CD SUMMARY
    # ------------------------------------------------------------

    # Color the complete final summary according to its status.
    #
    # The summary is intentionally handled before the generic
    # INFO/ERROR formatting so that every line in the final
    # summary receives the same color.
    if message == "CI/CD Engine finished":
        return message

    if message.startswith("Status: "):

        if message == "Status: SUCCESS":
            return colorize(
                message,
                COLOR_GREEN
            )

        if message == "Status: FAILED":
            return colorize(
                message,
                COLOR_RED
            )

    # The summary separators are colored according to the status.
    #
    # The formatter keeps track of the selected summary color by
    # storing it on the logger instance through the helper below.
    if message.startswith("Stage: "):
        summary_color = _get_final_summary_color()

        if summary_color:
            return colorize(
                message,
                summary_color
            )

    if message.startswith("Exit Code: "):
        summary_color = _get_final_summary_color()

        if summary_color:
            return colorize(
                message,
                summary_color
            )

    if message.startswith("Deployment ID: "):
        summary_color = _get_final_summary_color()

        if summary_color:
            return colorize(
                message,
                summary_color
            )

    if message.startswith("Components: "):
        summary_color = _get_final_summary_color()

        if summary_color:
            return colorize(
                message,
                summary_color
            )

    if message.startswith("Errors: "):
        summary_color = _get_final_summary_color()

        if summary_color:
            return colorize(
                message,
                summary_color
            )

    # ------------------------------------------------------------
    # PREPARATION HEADER
    # ------------------------------------------------------------


    # ------------------------------------------------------------
    # BEFORE-DEPLOY CONFIGURATION
    # ------------------------------------------------------------

    if message.startswith(
        "Loading before-deploy configuration:"
    ):

        # Extract the complete configuration path from the message.
        config_path = message.split(":", 1)[1].strip()

        # Extract only the filename for the user-facing terminal.
        config_filename = Path(
            config_path.replace("\\", "/")
        ).name

        # Extract the Salesforce environment from the filename.
        environment = _extract_environment_from_config(
            config_filename
        )

        return (
            f"  Environment: {environment}\n"
            f"  Configuration: {config_filename}"
        )

    if message.startswith(
        "Before-deploy configuration loaded successfully"
    ):
        return colorize(
            "  Configuration loaded successfully",
            COLOR_GREEN
        )

    # ------------------------------------------------------------
    # PREPARATION STEPS
    # ------------------------------------------------------------

    if message.startswith("Step 1/4 -"):
        return (
            "\n"
            + colorize(
                "[1/4] FILE REPLACEMENT",
                COLOR_BLUE
            )
            + "\n"
            + colorize(
                "------------------------------------------------------------",
                COLOR_BLUE
            )
        )

    if message.startswith("Step 2/4 -"):
        return (
            "\n"
            + colorize(
                "[2/4] WORKFLOW ALERTS",
                COLOR_BLUE
            )
            + "\n"
            + colorize(
                "------------------------------------------------------------",
                COLOR_BLUE
            )
        )

    if message.startswith("Step 3/4 -"):
        return (
            "\n"
            + colorize(
                "[3/4] QUICK ACTIONS / SEND EMAIL",
                COLOR_BLUE
            )
            + "\n"
            + colorize(
                "------------------------------------------------------------",
                COLOR_BLUE
            )
        )

    if message.startswith("Step 4/4 -"):
        return (
            "\n"
            + colorize(
                "[4/4] DUPLICATION RULES",
                COLOR_BLUE
            )
            + "\n"
            + colorize(
                "------------------------------------------------------------",
                COLOR_BLUE
            )
        )

    # ------------------------------------------------------------
    # PREPARATION START / COMPLETION MESSAGES
    # ------------------------------------------------------------

    # The numbered stage headers already indicate the beginning
    # of each preparation operation.
    if message.endswith("preparation started."):
        return ""

    # Display a single success indicator when a preparation operation
    # has completed successfully.
    if message.endswith("preparation completed successfully."):
        operation = message.replace(
            " preparation completed successfully.",
            ""
        )

        return colorize(
            f"  ✓ {operation} completed successfully",
            COLOR_GREEN
        )

    # ------------------------------------------------------------
    # FILE REPLACEMENT
    # ------------------------------------------------------------

    if message.startswith("Replaced "):

        # Convert:
        # Replaced 'source' with 'target'.
        #
        # Into:
        # source → target
        match = re.match(
            r"Replaced '(.+)' with '(.+)'\.",
            message
        )

        if match:
            source_file = match.group(1)
            target_file = match.group(2)

            return (
                f"  {source_file} "
                f"→ "
                f"{target_file}"
            )

        # Fall back to the original message if the expected format
        # could not be parsed.
        return f"  {message}"

    # ------------------------------------------------------------
    # WORKFLOW FILES
    # ------------------------------------------------------------

    if message.startswith("Processing Workflow file:"):
        filename = message.split(":", 1)[1].strip()

        return (
            f"  {filename}"
        )

    if message.startswith("Updated Workflow Alert"):

        # Extract the Alert name from:
        # Updated Workflow Alert 'NAME' in 'FILE'.
        match = re.search(
            r"Updated Workflow Alert '([^']+)'",
            message
        )

        if match:
            alert_name = match.group(1)

            return colorize(
                f"      • {alert_name}",
                COLOR_GRAY
            )

        return message

    # The full technical path is already stored in the log file.
    if message.startswith("Workflow file updated:"):
        return ""

    # ------------------------------------------------------------
    # QUICK ACTIONS
    # ------------------------------------------------------------

    if message.startswith("Processing Quick Action file:"):
        filename = message.split(":", 1)[1].strip()

        return (
            f"  {filename}"
        )

    if message.startswith("Updated 'ValidatedFromAddress'"):
        return colorize(
            "      • ValidatedFromAddress updated",
            COLOR_GRAY
        )

    # The full technical path is already stored in the log file.
    if message.startswith("Quick Action file updated:"):
        return ""

    # ------------------------------------------------------------
    # DUPLICATE RULES
    # ------------------------------------------------------------

    if message.startswith("Processing Duplicate Rule file:"):
        filename = message.split(":", 1)[1].strip()

        return (
            f"  {filename}"
        )

    if message.startswith("Updated 'sortOrder'"):

        # Extract the configured sortOrder from:
        #
        # Updated 'sortOrder' in 'FILE' to 'VALUE'.
        match = re.search(
            r"Updated 'sortOrder' in '([^']+)' to '([^']+)'",
            message
        )

        if match:
            sort_order = match.group(2)

            return colorize(
                f"      • sortOrder: {sort_order}",
                COLOR_GRAY
            )

        return f"  {message}"

    # The full technical path is already stored in the log file.
    if message.startswith("Duplicate Rule file updated:"):
        return ""

    # ------------------------------------------------------------
    # NO CONFIGURATION
    # ------------------------------------------------------------

    if message.startswith("No ") and " configured." in message:
        return colorize(
            f"  - {message}",
            COLOR_YELLOW
        )

    # ------------------------------------------------------------
    # HIDDEN CONFIGURATION ERROR
    # ------------------------------------------------------------

    # The detailed configuration message below is sufficient for the
    # user-facing terminal, so do not display the generic error line.
    if message == "CI/CD configuration error.":
        return ""

    # ------------------------------------------------------------
    # BEFORE-DEPLOY CONFIGURATION ERROR
    # ------------------------------------------------------------

    # Display the specific before-deploy configuration error in the
    # normal terminal color while keeping the error symbol visible.
    if message.startswith(
        "Message: Before-deploy configuration file not found:"
    ):
        return f"✗ {message}"

    # ------------------------------------------------------------
    # ERRORS
    # ------------------------------------------------------------

    if level >= logging.ERROR:
        return colorize(
            f"  ✗ {message}",
            COLOR_RED
        )

    # ------------------------------------------------------------
    # WARNINGS
    # ------------------------------------------------------------

    if level >= logging.WARNING:
        return colorize(
            f"  ! {message}",
            COLOR_YELLOW
        )

    # ------------------------------------------------------------
    # DEFAULT INFORMATION
    # ------------------------------------------------------------

    return message


def _get_final_summary_color():
    """
    Return the color currently selected for the final CI/CD summary.

    The summary status is stored globally so that all lines belonging
    to the summary can use the same color.

    Returns:
        str | None:
            ANSI color code for the current summary status.
    """

    return getattr(
        format_console_message,
        "final_summary_color",
        None
    )


def _set_final_summary_color(color):
    """
    Set the color used for the final CI/CD summary.

    Args:
        color (str):
            ANSI color escape sequence.

    Returns:
        None
    """

    format_console_message.final_summary_color = color


def _extract_environment_from_config(config_filename):
    """
    Extract the target Salesforce environment from a before-deploy
    configuration filename.

    Expected filename format:
        before-deploy-dev.json
        before-deploy-test.json
        before-deploy-prod.json

    Args:
        config_filename (str):
            Configuration filename.

    Returns:
        str:
            Target environment when it can be extracted.
            Otherwise, 'unknown'.
    """

    # Match the expected before-deploy filename structure.
    match = re.match(
        r"before-deploy-([^.]+)\.json$",
        config_filename,
        re.IGNORECASE
    )

    # Return the extracted environment when the filename matches.
    if match:
        return match.group(1).lower()

    # Fall back to an explicit value when the filename does not
    # follow the expected naming convention.
    return "unknown"


class ConsoleFormatter(logging.Formatter):
    """
    Format log messages specifically for the CI/CD terminal.

    The file logger continues to use the normal technical format.
    """

    def format(self, record):
        """
        Format one log record for terminal output.

        Args:
            record (logging.LogRecord):
                Logging record produced by Python logging.

        Returns:
            str:
                User-friendly terminal output.
        """

        message = record.getMessage()

        # Detect the final summary status before formatting the
        # individual summary lines.
        if message == "Status: SUCCESS":
            _set_final_summary_color(
                COLOR_GREEN
            )

        elif message == "Status: FAILED":
            _set_final_summary_color(
                COLOR_RED
            )

        # Reset the summary color after the final separator so that
        # the next CI/CD messages are not affected.
        elif (
            message == "============================================================"
            and getattr(
                format_console_message,
                "final_summary_color",
                None
            ) is not None
        ):
            # The first separator belongs to the summary only when
            # the current summary color was already established.
            pass

        return format_console_message(
            record.levelno,
            message
        )


def initialize_logger(log_file):
    """
    Initialize the CI/CD Engine logger.

    The logger is configured with two handlers:

    - Console handler:
      Displays user-friendly INFO, WARNING and ERROR messages.

    - File handler:
      Stores DEBUG and higher-level messages in the full CI/CD log.

    The log file is opened in write mode so that every new CI/CD run
    starts with a fresh log.

    Args:
        log_file (str | Path):
            Path to the CI/CD log file.

    Returns:
        logging.Logger:
            Configured CI/CD Engine logger.
    """

    # Enable ANSI terminal colors when supported by the operating system.
    enable_windows_terminal_colors()

    # Convert the supplied path to a Path object.
    log_file = Path(log_file)

    # Make sure the directory containing the log file exists.
    log_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Get the central CI/CD Engine logger.
    logger = logging.getLogger(LOGGER_NAME)

    # Set the logger to DEBUG so that all messages can reach the
    # file handler. Individual handlers decide what they display.
    logger.setLevel(logging.DEBUG)

    # Prevent messages from being propagated to the root logger.
    logger.propagate = False

    # Remove existing handlers before adding new ones.
    # This prevents duplicate messages if the logger is initialized
    # more than once during the same Python process.
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    # Reset the final summary color at the beginning of every run.
    _set_final_summary_color(
        None
    )

    # ------------------------------------------------------------
    # CONSOLE HANDLER
    # ------------------------------------------------------------

    # Create the console handler.
    # INFO and higher messages are displayed to the user.
    console_handler = logging.StreamHandler()

    console_handler.setLevel(logging.INFO)

    # Use the dedicated user-friendly console formatter.
    console_handler.setFormatter(
        ConsoleFormatter()
    )

    # ------------------------------------------------------------
    # FILE HANDLER
    # ------------------------------------------------------------

    # Create the technical log file handler.
    # mode="w" means every new CI/CD run overwrites the previous log.
    file_handler = logging.FileHandler(
        log_file,
        mode="w",
        encoding="utf-8"
    )

    # Store DEBUG and higher messages in the full log.
    file_handler.setLevel(logging.DEBUG)

    # Keep the technical log format detailed and timestamped.
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(
        file_formatter
    )

    # Attach both handlers to the central logger.
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Write an initial technical log entry.
    #
    # The console formatter intentionally hides this message because
    # the actual Engine header is printed by cicd.py.
    logger.info(
        "CI/CD logging initialized."
    )

    # Store the complete log path only in the technical log.
    logger.debug(
        f"Full CI/CD log file: {log_file}"
    )

    return logger


def get_logger():
    """
    Return the centralized CI/CD Engine logger.

    Returns:
        logging.Logger:
            The configured CI/CD Engine logger.

    Raises:
        RuntimeError:
            If the logger has not been initialized yet.
    """

    # Retrieve the central logger.
    logger = logging.getLogger(LOGGER_NAME)

    # Verify that the logger was initialized before use.
    if not logger.handlers:
        raise RuntimeError(
            "CI/CD logger has not been initialized."
        )

    return logger