# DNS.Services Gateway

[![PyPI version](https://badge.fury.io/py/dns-services-gateway.svg)](https://badge.fury.io/py/dns-services-gateway)
[![Python Versions](https://img.shields.io/pypi/pyversions/dns-services-gateway.svg)](https://pypi.org/project/dns-services-gateway/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Python client library and CLI tool for managing DNS records through the DNS.services API. This tool provides a simple and intuitive interface for managing domains and DNS records programmatically or via command line.

## Features

- 🔐 Secure JWT token-based authentication
- 🌍 Comprehensive domain management
- 📝 Full DNS record CRUD operations (Create, Read, Update, Delete)
- 🎨 Beautiful CLI with colored output and progress indicators
- 🔄 Automatic token refresh handling
- ⚡ Efficient bulk operations support
- 🛡️ Built-in error handling and validation

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

## Quick Start

### CLI Usage

1. Set up your credentials in a `.env` file:
```bash
DNS_SERVICES_BASE_URL="https://dns.services"
DNS_SERVICES_USERNAME="your-username"
DNS_SERVICES_PASSWORD="your-password"
```

2. List DNS records for a domain:
```bash
python dsg.py example.com -v
```

3. Create a new DNS record:
```bash
python dsg.py example.com --create --type A --name www --content "192.0.2.1"
```

### Programmatic Usage

```python
from dns_services_gateway import DNSServicesClient

# Initialize the client
client = DNSServicesClient()

# List all domains
domains = client.list_domains()

# Create a new DNS record
record = client.create_record(
    domain="example.com",
    record_type="A",
    name="www",
    content="192.0.2.1"
)

# Update a DNS record
client.update_record(
    domain="example.com",
    record_id="record_id",
    content="192.0.2.2"
)
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable verbose output |
| `--no-color` | Disable colored output and icons |
| `--create` | Create a new DNS record |
| `--update` | Update an existing DNS record |
| `--delete` | Delete a DNS record |
| `--type` | Specify record type (A, AAAA, CNAME, TXT, etc.) |
| `--name` | Record name/hostname |
| `--content` | Record content/value |

## API Documentation

For detailed API documentation and examples, please see:
- [API Reference](docs/DNS_services_API_Reference.md)
- [Authentication Guide](docs/doc-api.md)

## Development

### Prerequisites

- Python 3.8+
- pip
- virtualenv (recommended)

### Setting up Development Environment

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

3. Install pre-commit hooks:
```bash
pre-commit install
```

### Running Tests

```bash
pytest tests/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- DNS.services for providing the API
- All contributors who have helped with the project
