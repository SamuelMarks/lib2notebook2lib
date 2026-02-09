"""
Defines the Pydantic models for the SDK configuration.

Ensures type safety and validation for user inputs before processing begins.
"""

from pathlib import Path
from typing import Optional, Set
from pydantic import BaseModel, Field, FilePath, ConfigDict, EmailStr


class UserConfig(BaseModel):
    """
    Configuration definition for a Notebook-to-Library conversion.

    Attributes:
        notebook_path: Path to the existing .ipynb file. Must exist.
        project_name: Name of the generated python package. Must be a valid identifier.
        version: Semantic version string for the package.
        author_name: Name of the package author.
        author_email: Email of the package author.
        output_dir: The parent directory where the project folder will be created.
        override_dependencies: Optional set of dependency strings. If provided,
            auto-detection is skipped or replaced by this set.
    """

    notebook_path: FilePath
    project_name: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$")
    version: str = "0.0.1"
    author_name: str = "Jupyter User"
    # Using simple str for email to avoid strict EmailStr dependency if not strictly required,
    # but could use EmailStr if pydantic[email] is installed. Keeping simple for core compat.
    author_email: str = "user@example.com"
    output_dir: Path = Path(".")
    override_dependencies: Optional[Set[str]] = None

    model_config = ConfigDict(frozen=True)
