"""File system input model."""

from models.base_input import ModalityInput


class FileSystemInput(ModalityInput):
    """Input for file system changes.

    Args:
        path: File or directory path.
        content: File content (for create/modify operations).
        operation: Operation type (create, modify, delete).
        permissions: Optional file permissions.
    """

    pass
