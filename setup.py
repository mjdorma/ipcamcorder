#!/usr/bin/env python
from setuptools import setup
import re
import sys


try:
    import cv2
except ImportError:
    print("Please install OpenCV and configure cv2 for python")
    raise

setup(
    name="ipcamcorder",
    version='0.0.1',
    py_modules=['ipcamcorder'],
    zip_safe=False,
    author="Michael Dorman",
    author_email="mjdorma@gmail.com",
    url="http://",
    description="IP JPG Capture and record software",
    long_description=open('README.rst').read(),
    license="ASL",
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    entry_points={
        'console_scripts': [
            'ipcamcorder = ipcamcorder:main.start',
            ],
    },
    install_requires=['requests', 'begins', 'numpy']
)
