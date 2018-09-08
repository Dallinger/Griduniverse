#!/usr/bin/env python

import os
import sys

from setup_utils import update_pins
from setuptools import setup, find_packages


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

try:
    import pypandoc
    readme = pypandoc.convert('README.md', 'rst')
    history = pypandoc.convert('CHANGELOG.md', 'rst')
except (IOError, ImportError):
    try:
        # Python 3
        readme = open('README.md', encoding='utf-8').read()
        history = open('CHANGELOG.md', encoding='utf-8').read()
    except TypeError:
        # Python 2
        readme = open('README.md').read()
        history = open('CHANGELOG.md').read()

# Get rid of Sphinx markup
history = history.replace('.. :changelog:', '')

doclink = """
Documentation
-------------

The full documentation is at http://dallinger-griduniverse.rtfd.org."""

setup_args = dict(
    name='dlgr.griduniverse',
    version='0.1.0',
    description='A Dallinger experiment that creates a Griduniverse for the '
                'study of human social behavior - a parameterized space of '
                'games expansive enough to capture a diversity of relevant '
                'dynamics, yet simple enough to permit rigorous analysis.',
    long_description=readme + '\n\n' + doclink + '\n\n' + history,
    author='Jordan Suchow',
    author_email='suchow@berkeley.edu',
    url='https://github.com/suchow/Griduniverse',
    packages=find_packages('.'),
    package_dir={'': '.'},
    namespace_packages=['dlgr'],
    include_package_data=True,
    install_requires=[],
    license='MIT',
    zip_safe=False,
    keywords='Dallinger Griduniverse',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
    ],
    entry_points={
        'dallinger.experiments': [
            'Griduniverse = dlgr.griduniverse.experiment:Griduniverse',
        ],
    },
    extras_require={},
)

update_pins(setup_args)
setup(**setup_args)
