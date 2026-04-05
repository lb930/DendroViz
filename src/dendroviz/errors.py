class DendrogramError(Exception):
    """Base exception for dendroviz."""


class ValidationError(DendrogramError):
    """Raised when the input CSV does not represent a valid rooted tree."""
