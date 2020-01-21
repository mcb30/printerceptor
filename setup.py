#!/usr/bin/env python3

"""Setup script"""

from setuptools import setup, find_packages

setup(
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: No Input/Output (Daemon)",
        "License :: OSI Approved :: "
        "GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 3",
        "Topic :: Printing",
    ],
    packages=find_packages(exclude=['test']),
    use_scm_version=True,
    setup_requires=[
        'setuptools_scm',
    ],
    install_requires=[
        'setuptools',
    ],
    entry_points={
        'console_scripts': [
            'printerceptor = printerceptor.cli:Command.main',
        ],
        'printerceptor.plugins': [
            'lpd = printerceptor.lpd:LpdInterception',
        ],
    },
)
