"""Setup script for DNS Services Gateway."""

from setuptools import setup, find_packages

setup(
    name="dns-services-gateway",
    version="0.9.6",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "typing-extensions>=4.8.0",
        "click>=8.0.0",
        "PyJWT>=2.0.0",
        "python-dateutil>=2.8.2",
    ],
    extras_require={
        "cli": ["rich>=13.7.0"],
    },
    entry_points={
        "console_scripts": [
            "dns-services=dns_services_gateway.cli:cli",
        ],
    },
    python_requires=">=3.12",
    author="DNS Services Gateway Team",
    description="A Python gateway for DNS.services API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/mikl0s/dns.services",
    project_urls={
        "Bug Tracker": "https://github.com/mikl0s/dns.services/issues",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
    ],
)
