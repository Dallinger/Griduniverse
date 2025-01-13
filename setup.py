#!/usr/bin/env python

import os
import pathlib
import sys

from setuptools import find_packages, setup

if sys.argv[-1] == "publish":
    os.system("python setup.py sdist upload")
    sys.exit()

# The directory containing this file
HERE = pathlib.Path(__file__).parent

readme = (HERE / "README.md").read_text(encoding="utf-8")
history = (HERE / "CHANGELOG.md").read_text(encoding="utf-8")

# Get rid of Sphinx markup
history = history.replace(".. :changelog:", "")

doclink = """
Documentation
-------------

The full documentation is at http://dallinger-griduniverse.rtfd.org.
"""

setup_args = dict(
    name="dlgr.griduniverse",
    version="0.1.0",
    description="A Dallinger experiment that creates a Griduniverse for the "
    "study of human social behavior - a parameterized space of "
    "games expansive enough to capture a diversity of relevant "
    "dynamics, yet simple enough to permit rigorous analysis.",
    long_description=readme + "\n\n" + doclink + "\n\n" + history,
    long_description_content_type="text/markdown",
    author="Jordan Suchow",
    author_email="suchow@berkeley.edu",
    url="https://github.com/suchow/Griduniverse",
    packages=find_packages("."),
    package_dir={"": "."},
    namespace_packages=["dlgr"],
    include_package_data=True,
    install_requires=[
        "dallinger",
        "numpy",
        "faker",
        "psycogreen",
        "PyYAML",
        "cached-property",
    ],
    license="MIT",
    zip_safe=False,
    keywords="Dallinger Griduniverse",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "dallinger.experiments": [
            "Griduniverse = dlgr.griduniverse.experiment:Griduniverse",
        ],
    },
    extras_require={
        "dev": [
            "alabaster",
            "black",
            "coverage",
            "coverage_pth",
            "codecov",
            "flake8",
            "pytest",
            "recommonmark",
            "Sphinx",
            "sphinxcontrib-spelling",
            "tox",
            "mock",
            "pip-tools",
            "pre-commit",
        ],
    },
)
setup(**setup_args)
