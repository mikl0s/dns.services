"""Setup script for DNS Services Gateway."""
from setuptools import setup, find_packages

setup(
    name="dns-services-gateway",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests",
        "python-dotenv",
        "pydantic",
        "typing-extensions",
        "click>=8.0.0",
        "PyJWT>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "dns-services=dns_services_gateway.cli:cli",
        ],
    },
    python_requires=">=3.7",
    author="DNS Services Gateway Team",
    description="A Python gateway for DNS.services API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
