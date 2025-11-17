"""File system state model."""

from models.base_state import ModalityState


class FileSystemState(ModalityState):
    """Current file system state.

    Args:
        directory_tree: Nested structure representing the directory tree.
        file_contents: Dictionary mapping file paths to their contents.
        file_metadata: Dictionary mapping file paths to metadata (size, permissions, etc.).
    """

    pass
