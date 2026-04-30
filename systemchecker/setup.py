from setuptools import setup
import glob
import os
from pathlib import Path


def collect_data_files(folder):
    """Keep Flask assets available after pip installs the wheel."""
    root = Path(folder)
    if not root.exists():
        return []

    groups = []
    for directory in [root, *[p for p in root.rglob("*") if p.is_dir()]]:
        files = [str(p) for p in directory.iterdir() if p.is_file()]
        if files:
            groups.append((str(directory), files))
    return groups


# Buscar todos los módulos de Python en la raíz (excepto setup.py)
py_files = [os.path.splitext(f)[0] for f in glob.glob("*.py") if f != "setup.py"]

setup(
    name="spv",
    version="3.1.1",
    description="System Process Viewer & Optimizer",
    author="Kentucky",
    py_modules=py_files,
    include_package_data=True,
    data_files=[
        *collect_data_files("templates"),
        *collect_data_files("static"),
        *collect_data_files("data"),
    ],
    install_requires=[
        "Flask",
        "psutil",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            # CLI principal. La UI se abre con: spv ui
            "spv=cli:main",
            # Acceso directo alternativo a la UI.
            "spv-ui=app:main",
        ],
    },
)
