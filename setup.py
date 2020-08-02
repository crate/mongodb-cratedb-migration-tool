from setuptools import find_packages, setup

setup(
    name="rip",
    entry_points={"console_scripts": ["rip = rip.__main__:main"]},
    packages=find_packages(),
    install_requires=[
        "pymongo==3.10.1",
        "rich==3.3.2",
    ],
    extras_require={
        "testing": ["black==18.9b0", "flake8==3.7.7", "mypy==0.670", "isort==4.3.15"]
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
)
