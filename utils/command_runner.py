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
import queue
import signal
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


def _terminate_process_tree(process):
    """Terminate the command and its child processes where supported."""
    if process.poll() is not None:
        return

    try:
        if os.name == "nt":
            # taskkill /T targets descendants created by CLI wrappers such as sf.cmd.
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        try:
            process.kill()
        except OSError:
            pass


def run_command(command, timeout=600, max_output_bytes=10 * 1024 * 1024):
    """Run a command, stream output to the log, and enforce resource limits.

    Args:
        command (list[str]): Command and arguments to execute.
        timeout (int | float): Maximum runtime in seconds (default: 10 minutes).
        max_output_bytes (int): Maximum output retained in memory. Output is
            still streamed to the log; exceeding this limit terminates the
            command and returns exit code 125 to avoid incomplete JSON being
            mistaken for a successful command result.

    Returns:
        CommandResult: Exit code and captured output.

    Raises:
        ValueError: If a resource limit is invalid.
        RuntimeError: If the external command cannot be started.
    """
    if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
        raise ValueError("timeout must be a positive number of seconds or None.")
    if not isinstance(max_output_bytes, int) or max_output_bytes <= 0:
        raise ValueError("max_output_bytes must be a positive integer.")

    logger = get_logger()
    prepared_command = prepare_command(command)
    logger.info(f"Command: {' '.join(prepared_command)}")

    process_environment = os.environ.copy()
    process_environment["SF_USE_PROGRESS_BAR"] = "false"
    spinner = CommandSpinner("Executing Salesforce command")
    output_queue = queue.Queue()
    output_chunks = []
    captured_bytes = 0
    output_limit_exceeded = False
    timed_out = False

    popen_options = {}
    if os.name == "nt":
        popen_options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_options["start_new_session"] = True

    try:
        process = subprocess.Popen(
            prepared_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=process_environment,
            **popen_options
        )

        def read_output():
            try:
                for output_line in process.stdout:
                    output_queue.put(output_line)
            finally:
                output_queue.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        spinner.start()
        deadline = None if timeout is None else time.monotonic() + timeout
        stream_finished = False

        while not stream_finished:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                timed_out = True
                _terminate_process_tree(process)
                deadline = None
                # Continue draining output after termination, without another timeout.
                continue

            try:
                item = output_queue.get(timeout=remaining)
            except queue.Empty:
                timed_out = True
                _terminate_process_tree(process)
                deadline = None
                continue

            if item is None:
                stream_finished = True
                continue

            logger.debug(item.rstrip("\r\n"))
            encoded_size = len(item.encode("utf-8", errors="replace"))
            if not output_limit_exceeded and captured_bytes + encoded_size <= max_output_bytes:
                output_chunks.append(item)
                captured_bytes += encoded_size
            elif not output_limit_exceeded:
                output_limit_exceeded = True
                logger.error(
                    f"Command output exceeded the {max_output_bytes}-byte capture limit; "
                    "terminating command to protect memory."
                )
                _terminate_process_tree(process)

        return_code = process.wait()
        reader.join(timeout=2)

        if timed_out:
            return_code = 124
            output_chunks.append(
                f"\n[ERROR] Command timed out after {timeout} seconds.\n"
            )
            logger.error(f"Command timed out after {timeout} seconds.")
        elif output_limit_exceeded:
            return_code = 125
            output_chunks.append(
                f"\n[ERROR] Output exceeded the {max_output_bytes}-byte limit; "
                "command was terminated.\n"
            )

        if return_code == 0:
            logger.debug("Command completed successfully.")
        else:
            logger.debug(f"Command failed with exit code {return_code}.")

        return CommandResult(
            exit_code=return_code,
            output="".join(output_chunks)
        )

    except OSError as error:
        logger.error(f"Failed to execute command: {error}")
        raise RuntimeError(
            f"Failed to execute command: {prepared_command[0]}"
        ) from error
    finally:
        spinner.stop()
