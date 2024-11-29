# DNS.Services Gateway

[![PyPI version](https://badge.fury.io/py/dns-services-gateway.svg)](https://badge.fury.io/py/dns-services-gateway)
[![Python Versions](https://img.shields.io/pypi/pyversions/dns-services-gateway.svg)](https://pypi.org/project/dns-services-gateway/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Python client library and CLI tool for managing DNS records through the DNS.services API. This tool provides a simple and intuitive interface for managing domains and DNS records programmatically or via command line.

## Features

- 🔐 Flexible Authentication
  - JWT token-based authentication
  - Basic Authentication support
  - Automatic token refresh handling
- 🌍 Comprehensive domain management
  - List domains
  - Fetch domain details
  - Verify domain configuration
  - Retrieve domain metadata
- 📝 Full DNS record CRUD operations
  - Support for A, AAAA, CNAME, MX, and TXT records
  - Batch operations for multiple records
  - Record validation and verification
  - TTL management
- 🎨 Beautiful CLI with colored output and progress indicators
- ⚡ Efficient bulk operations support
- 🛡️ Built-in error handling and validation
- 📘 Comprehensive documentation with docstrings
- ✨ Full type safety with mypy support
- 📊 High test coverage with pytest

## Installation

### Using pip

```bash
pip install dns-services-gateway
```

### From source

```bash
git clone https://github.com/yourusername/dns-services-gateway.git
cd dns-services-gateway
pip install -r requirements.txt
```

## Usage

### Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install package
pip install -r requirements.txt
```

### Configuration

Set up your environment variables:

```bash
# Required
export DNS_SERVICES_USERNAME="your_username"
export DNS_SERVICES_PASSWORD="your_password"

# Optional
export DNS_SERVICES_BASE_URL="https://dns.services"  # Default
export DNS_SERVICES_TOKEN_PATH="~/.dns-services/token"  # JWT token storage
export DNS_SERVICES_VERIFY_SSL="true"  # Enable/disable SSL verification
export DNS_SERVICES_TIMEOUT="30"  # API timeout in seconds
export DNS_SERVICES_DEBUG="false"  # Enable debug logging
export DNS_SERVICES_AUTH_TYPE="JWT"  # Authentication type: JWT or BASIC
```

Or create a `.env` file (see `.env.example`).

### Examples

```python
from dns_services_gateway import DNSServicesClient, DNSServicesConfig, AuthType
from dns_services_gateway.records import ARecord, MXRecord, RecordAction

# Create client with JWT authentication (default)
config = DNSServicesConfig.from_env()
client = DNSServicesClient(config)

# Or use Basic Authentication
basic_config = DNSServicesConfig(
    username="your_username",
    password="your_password",
    auth_type=AuthType.BASIC
)
basic_client = DNSServicesClient(basic_config)

# List domains
response = await client.list_domains()

# Get domain details
response = await client.get_domain_details("example.com")

# Verify domain
response = await client.verify_domain("example.com")

# Get domain metadata
response = await client.get_domain_metadata("example.com")

# Manage DNS records
records_manager = client.records

# Create an A record
a_record = ARecord(name="www", value="192.168.1.1", ttl=3600)
response = await records_manager.manage_record(
    action=RecordAction.CREATE,
    domain="example.com",
    record=a_record
)

# Create an MX record with priority
mx_record = MXRecord(
    name="@",
    value="mail.example.com",
    priority=10,
    ttl=3600
)
response = await records_manager.manage_record(
    action=RecordAction.CREATE,
    domain="example.com",
    record=mx_record
)

# Verify record propagation
verified = await records_manager.verify_record(
    domain="example.com",
    record=a_record,
    timeout=60  # Wait up to 60 seconds
)
```

## API Documentation

For detailed API documentation and examples, please see:
- [API Reference](docs/DNS_services_API_Reference.md)
- [Authentication Guide](docs/doc-api.md)

## Known Issues

### Test Coverage Reporting

When running tests with pytest-cov (coverage.py 6.0.0), you may see the following warning:

```
/venv/lib/python3.12/site-packages/coverage/inorout.py:508: CoverageWarning: Module src/dns_services_gateway/domain.py was never imported. (module-not-imported)
```

This is a known issue with coverage.py when using Python 3.12.3. The warning is a false positive and does not affect the actual test coverage or functionality. The module is properly imported and tested, but coverage.py sometimes fails to detect imports in certain Python module structures.

For more information, see:
- Coverage.py version: 6.0.0
- Python version: 3.12.3
- Affected module: `src/dns_services_gateway/domain.py`

This issue will be resolved when coverage.py releases an update that better handles Python 3.12's module system.

## Development

### Prerequisites

- Python 3.12.3
- Virtual environment setup

### Testing

Run tests with:

```bash
venv/bin/pytest tests/
```

Check coverage with:

```bash
venv/bin/pytest --cov=dns_services_gateway tests/
```

### Linting and Formatting

```bash
venv/bin/flake8 src/ tests/
venv/bin/black src/ tests/
```

### Type Checking

```bash
venv/bin/mypy src/
```

### Contributing

Please follow the guidelines in `docs/guidelines.md` for contributing to this project.
