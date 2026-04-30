from setuptools import setup
import glob
import os

# Buscar todos los módulos de Python en la raíz (excepto setup.py)
py_files = [os.path.splitext(f)[0] for f in glob.glob("*.py") if f != "setup.py"]

setup(
    name="spv",
    version="3.1.0",
    description="System Process Viewer & Optimizer",
    author="Kentucky",
    py_modules=py_files,
    include_package_data=True,
    install_requires=[
        "Flask",
        "psutil",
        "requests"
    ],
    entry_points={
        'console_scripts': [
            # Esto le dice a pip que cree "spv.exe" en la carpeta Scripts de Python/venv
            # que ejecute la función main() del archivo cli.py
            'spv=cli:main',
        ],
    },
)
