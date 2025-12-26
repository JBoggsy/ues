"""UES version information.

This module provides a single source of truth for the UES version number.
The version is read from the package metadata (defined in pyproject.toml).

Usage:
    >>> from models.version import __version__
    >>> print(__version__)
    '0.1.0'

    >>> from models import UES_VERSION
    >>> print(UES_VERSION)
    '0.1.0'
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ues")
except PackageNotFoundError:
    # Package is not installed (running from source without install)
    # Fall back to a default for development
    __version__ = "0.1.0-dev"

# Alias for backward compatibility and clarity
UES_VERSION = __version__
