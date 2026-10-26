"""Path validation helpers for configuration-driven file operations."""

from pathlib import Path, PureWindowsPath


def resolve_within(base_directory, configured_path, label="Path"):
    """Resolve a relative path and reject paths escaping the allowed base.

    Windows absolute paths are rejected even when validation runs on a
    non-Windows host. Resolved paths also account for existing symlinks.
    """
    if not isinstance(configured_path, str) or not configured_path.strip():
        raise ValueError(f"{label} must be a non-empty relative path.")

    normalized = configured_path.replace("\\", "/")
    windows_path = PureWindowsPath(configured_path)
    candidate_path = Path(normalized)

    if candidate_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise ValueError(f"{label} must be relative to its allowed directory.")

    base = Path(base_directory).resolve()
    resolved = (base / candidate_path).resolve()

    try:
        resolved.relative_to(base)
    except ValueError as error:
        raise ValueError(
            f"{label} must remain inside the allowed directory: {configured_path!r}."
        ) from error

    return resolved
