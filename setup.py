from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="physai",
    version="0.0.1",
    author="Andres Caicedo",
    author_email="andres.felipe.caicedo.ultengo@outlook.com",
    description="An AI-driven platform for generating, testing, and validating physical equations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AndresCdo/PhysiAI.git",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.7",
    install_requires=[
        # Add your project's dependencies here
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "physai=physai.commands:main",
        ],
    },
)
