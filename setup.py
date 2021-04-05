import os
from setuptools import setup, find_packages

import ced

def read(sr_file):
    with open(os.path.join(os.path.dirname(__file__), sr_file)) as dh_file:
        return dh_file.read()

setup(
    name='ced',
    version=ced.__version__,
    description='CED Python Library',
    author='Blake Regalia',
    author_email='blake.d.regalia@jpl.nasa.gov',
    url='https://github.jpl.nasa.gov/OpenCAE/ced-python-lib',
    keywords=['CED'],
    include_package_data=True,
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    packages=['ced'],
    install_requires=read('requirements.txt').strip().split('\n'),
    license='Apache 2.0',
    classifiers=[
        'Programming Language :: Python :: 3',
    ]
)