"""
Unit tests for the project scaffolding logic.
"""

import unittest
import tempfile
from pathlib import Path
from lib2notebook2lib.scaffold import ProjectGenerator, ProjectConfig


class TestProjectGenerator(unittest.TestCase):
    """Test suite for ProjectGenerator."""

    def setUp(self) -> None:
        """Set up temporary directory for scaffolding."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Cleanup temporary directory."""
        self.temp_dir.cleanup()

    def test_generate_structure(self) -> None:
        """Test that the basic file structure is created."""
        config = ProjectConfig(name="my-lib")
        generator = ProjectGenerator(config)
        generator.generate(self.root)

        # check root files
        self.assertTrue((self.root / "pyproject.toml").exists())
        self.assertTrue((self.root / "README.md").exists())
        self.assertTrue((self.root / "requirements.txt").exists())

        # check src
        pkg_slug = "my_lib"  # hyphens to underscores
        self.assertTrue((self.root / "src" / pkg_slug / "__init__.py").exists())

        # check tests
        self.assertTrue((self.root / "tests" / "__init__.py").exists())

    def test_pyproject_content(self) -> None:
        """Test that pyproject.toml contains Hatch configuration."""
        config = ProjectConfig(name="cool-tool", author_name="Tester")
        generator = ProjectGenerator(config)
        generator.generate(self.root)

        toml_content = (self.root / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[build-system]", toml_content)
        self.assertIn(
            'requires = ["hatchling", "hatch-requirements-txt"]', toml_content
        )
        self.assertIn('name = "cool-tool"', toml_content)
        self.assertIn('dynamic = ["dependencies"]', toml_content)
        self.assertIn("requirements_txt", toml_content)

    def test_requirements_population(self) -> None:
        """Test that requirements.txt is populated with sorted dependencies."""
        deps = {"pandas", "numpy", "requests"}
        config = ProjectConfig(name="data-lib", dependencies=deps)
        generator = ProjectGenerator(config)
        generator.generate(self.root)

        req_content = (self.root / "requirements.txt").read_text(encoding="utf-8")
        lines = req_content.strip().splitlines()

        self.assertEqual(len(lines), 3)
        self.assertEqual(lines, ["numpy", "pandas", "requests"])

    def test_existing_requirements_preserved(self) -> None:
        """Test that an existing requirements.txt is NOT overwritten."""
        # Pre-create requirements.txt
        req_path = self.root / "requirements.txt"
        with open(req_path, "w", encoding="utf-8") as f:
            f.write("pre-existing-dep\n")

        config = ProjectConfig(name="existing-lib", dependencies={"new-dep"})
        generator = ProjectGenerator(config)
        generator.generate(self.root)

        content = req_path.read_text(encoding="utf-8")
        self.assertIn("pre-existing-dep", content)
        self.assertNotIn("new-dep", content)

    def test_empty_requirements_created(self) -> None:
        """Test that an empty requirements.txt is created if no deps exist."""
        config = ProjectConfig(name="nodeps")
        generator = ProjectGenerator(config)
        generator.generate(self.root)

        req_path = self.root / "requirements.txt"
        self.assertTrue(req_path.exists())
        self.assertEqual(req_path.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
