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
```

Or create a `.env` file (see `.env.example`).

### Examples

```python
from dns_services_gateway import DNSServicesClient, DNSServicesConfig

# Create client
config = DNSServicesConfig.from_env()
client = DNSServicesClient(config)

# List domains
domains = client.get("/domains")

# Create DNS record
response = client.post("/domains/example.com/records", json={
    "type": "A",
    "name": "www",
    "content": "192.0.2.1",
    "ttl": 3600
})
```

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
- Windsurf Editor & Claude 3.5 Sonnet
