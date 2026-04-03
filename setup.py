import re

import setuptools

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

with open("pyyorkshirewater/_version.py", "r", encoding="utf8") as version_file:
    version_groups = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file.read(), re.M)
    if version_groups:
        version = version_groups.group(1)
    else:
        raise RuntimeError("Unable to find version string!")

REQUIREMENTS = [
    "pyjwt >= 2.6, < 3",
    "aiohttp >= 3",
]

DEV_REQUIREMENTS = [
    "black >= 24, < 27",
    "flake8 == 7.*",
    "isort >= 5, < 9",
    "mypy >= 1.9, < 1.20",
    "pytest >= 8, < 10",
    "pytest-cov >= 4, < 8",
]

setuptools.setup(
    name="pyyorkshirewater",
    version=version,
    description="A package to interact with Yorkshire Water smart meters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    package_data={
        "pyyorkshirewater": [
            "py.typed",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=REQUIREMENTS,
    extras_require={
        "dev": DEV_REQUIREMENTS,
    },
    python_requires=">=3.10, <4",
    packages=["pyyorkshirewater"],
)
