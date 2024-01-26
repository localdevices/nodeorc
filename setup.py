#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages
here = os.path.abspath(os.path.dirname(__file__))

setup(
    name="nodeopenrivercam",
    description="nodeopenrivercam (nodeorc) is a node processor shell around pyOpenRiverCam",
    version="0.1.0",
    url="https://github.com/localdevices/nodeorc",
    author="Hessel Winsemius",
    author_email="winsemius@rainbowsensing.com",
    packages=find_packages(),
    package_dir={"nodeorc": "nodeorc"},
    test_suite="tests",
    python_requires=">=3.9",
    install_requires=[
        "boto3",
        "dask[distributed]"
        "ibm-cos-sdk",
        "pika",
        "pydantic==2.3.0",
        "pyopenrivercam",
        "python-dotenv",
        "requests",
        "sqlalchemy"
    ],
    extras_require={
        "dev": ["pytest", "pytest-cov", "pytest-lazy-fixtures"],
        "optional": [],
    },
    entry_points={
        "console_scripts": [
            "nodeorc = nodeorc.main:cli"
        ]
    },

    include_package_data=True,
    license="AGPLv3",
    zip_safe=False,
    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Hydrology",
        "Topic :: Scientific/Engineering :: Image Processing",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="hydrology, hydrometry, river-flow, pyorc, nodeorc",
)
