from setuptools import setup

from mtinfo import __version__ as version

setup(
		name = 'mtinfo',
		version = version,
		description = 'N/A',
		url = 'N/A',
		author = 'N/A',
		author_email = 'N/A',
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
		zip_safe = False,		
)
