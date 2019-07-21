import setuptools
import aspy

version = aspy.__version__

with open("README.md", 'r') as f:
    long_description = f.read()

setuptools.setup(
    name="aspy",
    version=version,
    author="Eduardo Nunes & Fernando Dantas",
    author_email="diofanto.nunes@gmail.com",
    license="MIT",
    description="Power Flow Solutions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dioph/aspy",
    packages=["aspy"],
    scripts=["bin/aspy"],
    install_requires=["matplotlib", "networkx", "numpy", "scipy"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
    ],
)
