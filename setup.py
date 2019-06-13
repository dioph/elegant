from numpy.distutils.core import Extension, setup
import aspy
version = aspy.__version__

with open("README.md", 'r') as f:
    long_description = f.read()

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
    install_requires=["numpy", "scipy"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
    ],
)
