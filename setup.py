""" Besett setup script.
"""

from setuptools import setup

setup(
    name='besett',
    version='0.1.0',
    short_description='Simple settings file management for Python applications',
    description='Besett helps you manage settings across multiple JSON files.',
    url='https://github.com/mscelnik/besett',
    author='Matthew Celnik',
    author_email='besett@celnik.co.uk',
    licence='LGPLv3+',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)'
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='json settings library',
    packages=[],
    py_modules=['besett'],
    install_requires=[],
)
