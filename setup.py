from numpy.distutils.core import Extension, setup
import builtins

with open("README.md", 'r') as f:
    long_description = f.read()

extension = Extension(name="_methods", sources=["aspy/methods.cpp"])
builtins.__ASPY_SETUP__ = True
import aspy
version = aspy.__version__

setup(
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
    ext_modules=[extension],
    install_requires=["numpy"],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
    ),
)
