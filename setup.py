#coding=utf8
import os
form setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name    = 'flow-conduit',
    version = '0.0.1',
    author  = 'Kui Tang',
    author_email = 'kuitang@gmail.com',
    description = ('Abstracts and parallelizes functional control flow based on data dependencies, à la make.'),
    packages = [ 'flowconduit', 'test' ],
    long_description = read('README.markdown'),
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
    ],
)

