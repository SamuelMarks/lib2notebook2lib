"""
The main SDK entry point for lib2notebook2lib.

Orchestrates the parsing, extraction, scaffolding, and code writing logic.
"""

from pathlib import Path
from .schema import UserConfig
from .parser import NotebookReader, DependencyAnalyzer
from .scaffold import ProjectGenerator, ProjectConfig
from .writer import PackageWriter


class JupyterToPackage:
    """
    Service class responsible for converting a Jupyter Notebook into a Python Package.
    """

    def __init__(self, config: UserConfig) -> None:
        """
        Initialize the converter service.

        Args:
            config: Validated UserConfig object containing paths and metadata.
        """
        self.config = config

    def convert(self) -> Path:
        """
        Executes the full conversion pipeline.

        Steps:
        1. Parse the notebook for code and dependencies.
        2. Generate project scaffolding (pyproject.toml, src/, tests/).
        3. Write sanitized code to the source module.

        Returns:
            The Path object pointing to the newly created project root.
        """
        # 1. Parse Notebook
        reader = NotebookReader(self.config.notebook_path)

        if self.config.override_dependencies is not None:
            # Use manual overrides
            dependencies = self.config.override_dependencies
        else:
            # Auto-detect
            analyzer = DependencyAnalyzer(reader)
            dependencies = analyzer.get_all_dependencies()

        code_cells = reader.get_code_cells()

        # 2. Configure Scaffolding
        # Map Pydantic UserConfig to internal ProjectConfig
        scaffold_config = ProjectConfig(
            name=self.config.project_name,
            dependencies=dependencies,
            version=self.config.version,
            author_name=self.config.author_name,
            author_email=self.config.author_email,
        )

        # Determine target directory
        # We create a new folder named after the project inside the output_dir
        project_root = self.config.output_dir / self.config.project_name

        generator = ProjectGenerator(scaffold_config)
        generator.generate(project_root)

        # 3. Write Code
        writer = PackageWriter(self.config.project_name)
        writer.write_code(project_root, code_cells)

        return project_root
