"""
Module for generating project scaffolding.

Handles the creation of directory structures and configuration files
specifically for hatch and hatch-requirements-txt.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, List


@dataclass
class ProjectConfig:
    """
    Configuration data for the new Python project.

    Attributes:
        name: The name of the project (PyPI compliant).
        dependencies: A set of dependency strings detected from the notebook.
        version: The initial version of the project.
        description: A short description for pyproject.toml.
        author_name: The author's name.
        author_email: The author's email.
    """

    name: str
    dependencies: Set[str] = field(default_factory=set)
    version: str = "0.0.1"
    description: str = "Converted from Jupyter Notebook via lib2notebook2lib"
    author_name: str = "Jupyter User"
    author_email: str = "user@example.com"


class ProjectGenerator:
    """
    Generates the file system structure for a Hatch-based Python project.
    """

    def __init__(self, config: ProjectConfig) -> None:
        """
        Initialize the generator with project configuration.

        Args:
            config: The ProjectConfig data object.
        """
        self.config = config

    def _get_pyproject_toml_content(self) -> str:
        """
        Generates the content for pyproject.toml.

        Configures the build-system to use hatchling and hatch-requirements-txt.

        Returns:
            A string containing the TOML configuration.
        """
        return (
            f"[build-system]\n"
            f'requires = ["hatchling", "hatch-requirements-txt"]\n'
            f'build-backend = "hatchling.build"\n\n'
            f"[project]\n"
            f'name = "{self.config.name}"\n'
            f'version = "{self.config.version}"\n'
            f'description = "{self.config.description}"\n'
            f'authors = [{{ name = "{self.config.author_name}", email = "{self.config.author_email}" }}]\n'
            f'readme = "README.md"\n'
            f'requires-python = ">=3.8"\n'
            f'dynamic = ["dependencies"]\n\n'
            f"[tool.hatch.metadata.hooks.requirements_txt]\n"
            f'files = ["requirements.txt"]\n'
        )

    def _get_readme_content(self) -> str:
        """
        Generates a basic README.md.

        Returns:
            String content for the README.
        """
        return (
            f"# {self.config.name}\n\n"
            f"{self.config.description}\n\n"
            f"## Installation\n\n"
            f"```bash\n"
            f"pip install .\n"
            f"```\n"
        )

    def generate(self, output_dir: Path) -> None:
        """
        Creates the project structure at the specified output directory.

        Creates:
        - pyproject.toml
        - requirements.txt (populated with detected deps)
        - README.md
        - src/<package_name>/__init__.py (empty placeholder, populated later by writer)
        - tests/__init__.py

        Args:
            output_dir: The root path where the project should be generated.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write pyproject.toml
        toml_path = output_dir / "pyproject.toml"
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(self._get_pyproject_toml_content())

        # 2. Write requirements.txt
        # Sort for deterministic output
        reqs_path = output_dir / "requirements.txt"
        if not reqs_path.exists() and self.config.dependencies:
            with open(reqs_path, "w", encoding="utf-8") as f:
                for dep in sorted(self.config.dependencies):
                    f.write(f"{dep}\n")
        elif not reqs_path.exists():
            # Create empty file if no deps, to satisfy hatch config
            reqs_path.touch()

        # 3. Write README
        readme_path = output_dir / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(self._get_readme_content())

        # 4. Create Source Layout
        # Normalize package name: replace hyphens with underscores for the module directory
        pkg_slug = self.config.name.replace("-", "_")
        src_path = output_dir / "src" / pkg_slug
        src_path.mkdir(parents=True, exist_ok=True)

        # Create empty __init__.py so it's a valid package
        (src_path / "__init__.py").touch()

        # 5. Create Tests Layout
        tests_path = output_dir / "tests"
        tests_path.mkdir(parents=True, exist_ok=True)
        (tests_path / "__init__.py").touch()
