""" Besett setup script.
"""

from setuptools import setup

version = '0.1.0'

setup(
    name='besett',
    version=version,
    short_description='Simple settings file management for Python applications',
    description='Besett helps you manage settings across multiple JSON files.',
    url='https://github.com/mscelnik/besett',
    author='Matthew Celnik',
    author_email='besett@celnik.co.uk',
    licence='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License'
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='json settings library',
    packages=[],
    py_modules=['besett'],
    install_requires=[],
)
