lib2notebook2lib
================

**lib2notebook2lib** is a bi-directional conversion tool for Python developers who move between exploratory Jupyter Notebooks and production-grade Libraries.

It automates the transition from detection-to-distribution by turning a `.ipynb` file into a strictly scaffolded, `pip install`able library using modern standards (Hatch, PyProject.toml). It can also reverse-engineer Python source files back into Notebooks for educational or demonstrative playgrounds.

## Features

- **Notebook → Library**:
  - Auto-detects dependencies (`!pip install`, `import numpy`) and populates `requirements.txt`.
  - Sanitizes code (removes Magics `%`, Shell `!`, and Help `?`).
  - Scaffolds a production-ready directory structure (`src/`, `tests/`) using `hatch`.
  - Configures `pyproject.toml` with dynamic dependencies.

- **Library → Notebook**:
  - Uses static analysis (LibCST) to reconstruct execution flow.
  - Converts Docstrings to Markdown cells.
  - Heuristically groups Imports, Definitions, and Logic.
  - Generates "Interactive Playground" cells for functions by inferring arguments.

## Installation

```bash
pip install lib2notebook2lib
```

*Note: Requires Python 3.8+*

## Usage

### CLI: Notebook to Library

Convert a notebook into a package named `my-analytics-lib`:

```bash
# Basic conversion
python -m lib2notebook2lib notebooks/experiment.ipynb --name my-analytics-lib

# Dry run (see dependencies without writing files)
python -m lib2notebook2lib notebooks/experiment.ipynb --name my-analytics-lib --dry-run

# Specify output directory and metadata
python -m lib2notebook2lib notebooks/experiment.ipynb \
    --name my-analytics-lib \
    --version 1.0.0 \
    --author "Jane Doe" \
    --output-dir ./dist
```

After conversion, your new library is ready to install:

```bash
cd my-analytics-lib
pip install .
```

### Python SDK

You can integrate the conversion logic into your own scripts or pipelines.

**Notebook to Library:**

```python
from pathlib import Path
from lib2notebook2lib.schema import UserConfig
from lib2notebook2lib.sdk import JupyterToPackage

config = UserConfig(
    notebook_path=Path("analysis.ipynb"),
    project_name="quant_lib",
    author_name="Quant Team",
    version="0.1.0"
)

converter = JupyterToPackage(config)
project_path = converter.convert()

print(f"Library created at: {project_path}")
```

**Library to Notebook:**

```python
from pathlib import Path
from lib2notebook2lib.reverser import LibraryToNotebook
import json

source_file = Path("src/my_lib/core.py")
converter = LibraryToNotebook(source_file)

notebook_json = converter.convert()

# Save as .ipynb
with open("playground.ipynb", "w") as f:
    json.dump(notebook_json, f, indent=2)
```

## How It Works

1. **Extraction**: We use `LibCST` to parse Python code and Regex to handle Jupyter Magic commands.
2. **Analysis**: Dependency extraction checks both standard imports and shell pip commands.
3. **Inference**: When reversing code, we detect `if __name__ == "__main__":` blocks to create run cells, or infer function signatures to generate placeholder code for variables.

## Development

This project itself is built with `hatch`.

```bash
# Run tests
python -m unittest discover tests
```
