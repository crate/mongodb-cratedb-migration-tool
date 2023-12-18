import io
import os
import re

from setuptools import find_packages, setup


def read(path):
    path = os.path.join(os.path.dirname(__file__), path)
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


versionf_content = read(os.path.join("crate", "migr8", "__init__.py"))
version_rex = r'^__version__ = [\'"]([^\'"]*)[\'"]$'
m = re.search(version_rex, versionf_content, re.M)
if m:
    version = m.group(1)
else:
    raise RuntimeError("Unable to find version string")


setup(
    name="migr8",
    version=version,
    url="https://github.com/crate/mongodb-cratedb-migration-tool",
    author="Crate.io",
    author_email="office@crate.io",
    description="MongoDB -> CrateDB Migration Tool",
    long_description=read("README.rst"),
    platforms=["any"],
    license="Apache License 2.0",
    packages=["crate.migr8"],
    namespace_packages=["crate"],
    entry_points={"console_scripts": ["migr8 = crate.migr8.__main__:main"]},
    install_requires=[
        "pymongo>=3.10.1,<5",
        "rich>=3.3.2,<4",
        "orjson>=3.3.1,<4",
        "python-bsonjs>=0.2,<0.3",
    ],
    extras_require={
        "testing": [
            "black==24.1.1",
            "flake8==6.1.0",
            "isort==5.13.2",
        ]
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
)
