import os
import re
from setuptools import setup, find_packages

def find_version(filename):
    _version_re = re.compile(r'__version__ = "(.*)"')
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)

version = find_version("opl/__init__.py")

packages = find_packages(exclude=("examples*", "test*", "scrap*", "build*"))

setup(
    name='opl',
    version=opl.__version__,
    description='Open-MBEE Python Library',
    author='Blake Regalia',
    author_email='blake.d.regalia@jpl.nasa.gov',
    url='https://github.com/Open-MBEE/opl',
    keywords=['OPL'],
    include_package_data=True,
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    packages=['opl'],
    install_requires=read('requirements.txt').strip().split('\n'),
    extras_require={
        "docs": [
            "sphinx",
            "sphinxcontrib-apidoc",
        ],
    },
    license='Apache 2.0',
    classifiers=[
        'Programming Language :: Python :: 3',
    ]
)
