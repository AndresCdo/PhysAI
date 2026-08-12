"""Packaging configuration for PhysAI."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="physai",
    version="0.1.0",
    author="Andres Caicedo",
    author_email="andres.felipe.caicedo.ultengo@outlook.com",
    description=(
        "Neuro-Symbolic framework for physics equation discovery "
        "via LLM-guided program synthesis"
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AndresCdo/PhysAI.git",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.19.0",
        "pandas>=2.0.0",
        "ollama>=0.1.0",
        "pylatexenc>=2.10",
    ],
    extras_require={
        "wolfram": [
            "wolframclient>=1.1.0",
        ],
        "data": [
            "arxiv>=2.0.0",
            "PyPDF2>=3.0.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "pylint>=2.15.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "physai=physai.commands:main",
        ],
    },
    include_package_data=True,
    package_data={
        "physai": [
            "prompts/*.txt",
            "data/benchmarks/*.csv",
        ],
    },
)
