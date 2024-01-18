#!/usr/bin/env python

from distutils.core import setup, Extension

setup(
    name = 'pdbparse',
    version = '0.1',
    description = 'Python parser for Microsoft PDB files',
    author = 'Johnny Cheng',
    author_email = 'zhung1206@gmail.com',
    url = 'https://github.com/ukyouz/pdbparse/',
    packages = ['pdbparse'],
    install_requires = ['construct>=2.9', 'construct<2.10'],
    classifiers = [
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
    ],
    include_package_data=True,
    scripts = [

    ])
