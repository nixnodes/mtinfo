from setuptools import setup

from mtinfo import __version__ as version

setup(
    name = 'mtinfo',
    version = version,
    description = 'TVmaze/iMDB query tool',
    long_description = 'TVmaze/iMDB query tool',
    url = 'https://github.com/nixnodes/mtinfo',
    author = 'nixnodes',
    author_email = 'io@nixnodes.net',
    license = 'MIT',
    packages = [
        'mtinfo',
        'mtinfo.tvmaze',
    ],
    install_requires = [
        'requests>=2.18',
    ],
    entry_points = {
        'console_scripts': [
            'tvmaze=mtinfo.tvmaze.main:main',
        ],
    },
    classifiers = (
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
