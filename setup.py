import re

from setuptools import setup

version = re.search(
    '^__version__\\s*=\\s*"(.*)"',
    open('aspy/__init__.py').read(),
    re.M
).group(1)

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name="aspy",
    version=version,
    author="Eduardo Nunes & Fernando Dantas",
    author_email="diofanto.nunes@gmail.com",
    description="Educational Power System Analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dioph/aspy",
    packages=["aspy"],
    entry_points={"console_scripts": ['aspy=aspy.interface:main']},
    install_requires=["networkx", "numpy", "scipy"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Intended Audience :: Education",
    ],
)
