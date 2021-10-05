"""Run this script with `python setup.py build_ext --inplace` from the db directory.
(The built extension can still be accessed from scripts run from the repository base
directory as normal.)"""

from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("trieparse.pyx", include_path=["./src/"])
)
