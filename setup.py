import re

from setuptools import setup

version = re.search(
    '^__version__\\s*=\\s*"(.*)"',
    open('elegant/__init__.py').read(),
    re.M
).group(1)

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name="elegant",
    version=version,
    author="Eduardo Nunes & Fernando Dantas",
    author_email="dioph@pm.me",
    description="Electrical Grid Analysis Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dioph/elegant",
    packages=["elegant"],
    entry_points={"console_scripts": ['elegant=elegant.interface:main']},
    install_requires=["networkx", "numpy", "scipy"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Intended Audience :: Education",
    ],
)
