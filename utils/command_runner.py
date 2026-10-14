"""
Utility functions for executing external commands.

This module provides a centralized way to execute external commands
such as Salesforce CLI commands.

Command output is:

1. Streamed in real time.
2. Written in full to the CI/CD log file.
3. Collected and returned to the caller for further processing.

While the external command is running, a small spinner is displayed
in the console so that long-running Salesforce operations do not
appear to be stuck.

The command runner remains platform-independent and does not contain
Salesforce-specific error handling or parsing logic.
"""

import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

from utils.logger import get_logger


@dataclass
class CommandResult:
    """
    Represent the result of an executed external command.

    Attributes:
        exit_code (int):
            Exit code returned by the external command.

        output (str):
            Complete output produced by the command.
    """

    exit_code: int
    output: str


class CommandSpinner:
    """
    Display a small animated spinner while an external command runs.

    The spinner runs in a background thread so that command execution
    and command output streaming are not blocked.

    The spinner writes only to the console. Detailed command output
    continues to be handled by the centralized logger.
    """

    def __init__(self, message="Processing"):
        """
        Initialize the command spinner.

        Args:
            message (str):
                Text displayed next to the spinner.
        """

        self.message = message
        self.running = False
        self.thread = None

        self.frames = [
            "⠋",
            "⠙",
            "⠹",
            "⠸",
            "⠼",
            "⠴",
            "⠦",
            "⠧",
            "⠇",
            "⠏"
        ]

    def start(self):
        """
        Start the spinner in a background thread.

        Returns:
            None
        """

        if not sys.stdout.isatty():
            return

        self.running = True

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )

        self.thread.start()

    def stop(self):
        """
        Stop the spinner and clear its console line.

        Returns:
            None
        """

        if not self.running:
            return

        self.running = False

        if self.thread is not None:
            self.thread.join()

        sys.stdout.write(
            "\r\033[K"
        )

        sys.stdout.flush()

    def _run(self):
        """
        Continuously update the spinner while the command is running.

        Returns:
            None
        """

        frame_index = 0

        while self.running:

            frame = self.frames[
                frame_index % len(self.frames)
            ]

            sys.stdout.write(
                f"\r  {frame} {self.message}..."
            )

            sys.stdout.flush()

            frame_index += 1

            time.sleep(0.1)


def prepare_command(command):
    """
    Prepare an external command for execution on the current operating system.

    On Windows, command-line tools installed as .cmd files cannot always be
    executed directly when shell=False is used. Therefore, Salesforce CLI
    commands using 'sf' are converted to 'sf.cmd'.

    Args:
        command (list[str]):
            Command and arguments to execute.

    Returns:
        list[str]:
            Command prepared for the current operating system.
    """

    prepared_command = command.copy()

    if (
        os.name == "nt"
        and prepared_command
        and prepared_command[0].lower() == "sf"
    ):
        prepared_command[0] = "sf.cmd"

    return prepared_command


def run_command(command):
    """
    Execute an external command and stream its output in real time.

    The complete output is written to the CI/CD log file as it is received.
    The output is also collected and returned to the caller so that other
    modules can inspect the complete command output after the process finishes.

    UTF-8 is explicitly used when decoding command output because Salesforce
    CLI can return non-ASCII content, including Hebrew text.

    Salesforce CLI progress bars are disabled for CI/CD execution through
    the SF_USE_PROGRESS_BAR environment variable. This prevents interactive
    progress updates from being repeatedly captured as separate output blocks.

    A console spinner runs while the external command is executing so that
    long-running validation and deployment operations visibly remain active.

    Args:
        command (list[str]):
            Command and arguments to execute.

    Returns:
        CommandResult:
            Structured result containing the command exit code and
            complete command output.

    Raises:
        RuntimeError:
            If the external command cannot be started.
    """

    logger = get_logger()

    prepared_command = prepare_command(command)

    logger.info(
        f"Command: {' '.join(prepared_command)}"
    )

    process_environment = os.environ.copy()

    process_environment["SF_USE_PROGRESS_BAR"] = "false"

    spinner = CommandSpinner(
        "Executing Salesforce command"
    )

    try:
        process = subprocess.Popen(
            prepared_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=process_environment
        )

        output_lines = []

        spinner.start()

        for line in process.stdout:
            output_lines.append(line)

            logger.debug(
                line.rstrip("\r\n")
            )

        return_code = process.wait()

        output = "".join(output_lines)

        if return_code == 0:
            logger.debug(
                "Command completed successfully."
            )
        else:
            logger.debug(
                f"Command failed with exit code {return_code}."
            )

        return CommandResult(
            exit_code=return_code,
            output=output
        )

    except OSError as error:
        logger.error(
            f"Failed to execute command: {error}"
        )

        raise RuntimeError(
            f"Failed to execute command: {prepared_command[0]}"
        ) from error

    finally:
        spinner.stop()