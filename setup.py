"""Package setup script."""
from typing import Optional

import setuptools

try:
    with open("README.md", "r") as f:
        long_description: Optional[str] = f.read()
except FileNotFoundError:
    long_description = None

setuptools.setup(
    name="edict",
    version="0.1.0",
    author="Eric Langlois",
    author_email="eric@langlois.xyz",
    description="Eric's Dictionary Transformer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=["edict"],
    package_data={"edict": ["edict.lark"]},
    entry_points={"console_scripts": ["edict=edict.cli:main"]},
    install_requires=["lark-parser", "setuptools"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        # "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.7",
)
