# DNS.Services Gateway

[![PyPI version](https://badge.fury.io/py/dns-services-gateway.svg)](https://badge.fury.io/py/dns-services-gateway)
[![Python Versions](https://img.shields.io/pypi/pyversions/dns-services-gateway.svg)](https://pypi.org/project/dns-services-gateway/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Development Status](https://img.shields.io/badge/status-alpha-yellow.svg)](https://pypi.org/project/dns-services-gateway/)
[![PyPI Downloads](https://static.pepy.tech/badge/dns-services-gateway)](https://pepy.tech/projects/dns-services-gateway)

> **Built with various AI coding tools**
>
> This entire production-ready module was created in just two weeks during the evenings using Windsurf Editor. From initial planning to comprehensive testing, Windsurf's AI-powered capabilities enabled rapid development while maintaining exceptional code quality:
>
> - **>70% test coverage**
> - **Full type safety**
> - **Async-first architecture**
> - **Production-ready error handling**
>
> It was fun learning/using Windsurf, and I'm excited to share the results with the community.

## Description

**<ins>No affiliation with DNS.services, made by users of DNS.services</ins>**

Although no affiliation with DNS.services, I did present the module to them for approval before making it available.

A Python client library and CLI tool for managing Domains and DNS records through the DNS.services API. This tool provides a simple and intuitive interface for managing domains and DNS records programmatically or via command line, single entry, batch entries or use our template system.

For this module, the DNS.Services API endpoints have been descoped, to only implement domains, DNS and Clientarea endpoints.

The scope of this module is to securely manage domains and DNS entries programatically.

## Features

- **Flexible Authentication**
  - JWT token-based authentication
  - Basic Authentication support
  - Automatic token refresh handling
- **Comprehensive domain management**
  - Bulk domain listing with metadata
  - Pagination and filtering support
  - Domain details with expiration dates
  - Configuration verification
  - Nameserver management
  - Domain availability checking
  - TLD listing with pricing
  - DNSSEC key management
- **Full DNS record management**
  - Support for A, AAAA, CNAME, MX, and TXT records
  - Type-specific validation for all record types
  - Record verification system
  - TTL management
  - Batch operations support
- **Performance features**
  - Async/await for non-blocking operations
  - Efficient bulk operations
  - Parallel processing for batch operations
  - Comprehensive error handling
- **Quality assurance**
  - Full type hints with mypy
  - 97% test coverage
  - Black code formatting
  - Flake8 compliance

## DNS Templates

The DNS Services Gateway supports a powerful templating system for managing DNS configurations across multiple domains and environments. Templates allow you to define reusable DNS configurations with variable substitution, environment-specific overrides, and comprehensive validation.

### Template Features

- **YAML-based configuration**
- **Variable substitution**
- **Environment-specific overrides**
- **Pre-application validation**
- **Safety features (backup, rollback)**
- **Version tracking**
- **Multiple application modes**
- **Change notifications (Email/Slack)**
- **Change tracking and history**

### Template Structure

```yaml
# Template metadata
metadata:
  version: "1.0.0"
  description: "Common web and mail configuration"
  author: "DNS Services Gateway"

# Variables for substitution
variables:
  domain: "example.com"
  ttl: 3600

# Record groups by purpose
records:
  web:
    - type: A
      name: "@"
      value: "203.0.113.10"
      ttl: ${ttl}
  mail:
    - type: MX
      name: "@"
      value: "mail.${domain}"
      priority: 10
      ttl: ${ttl}

# Environment overrides
environments:
  production:
    variables:
      ttl: 3600
  staging:
    variables:
      ttl: 300
      domain: "staging.example.com"

# Safety settings
settings:
  backup:
    enabled: true
    retention: 30

  rollback:
    enabled: true
    automatic: true

  change_management:
    require_approval: true
    notify:
      email: ["admin@example.com"]
      slack: ["#dns-changes"]
```

### Using Templates

#### CLI Usage

1. Create a new template:
```bash
dns-services template create example-com -d "Example.com DNS template" -a "John Doe"
```

2. Validate a template:
```bash
dns-services template validate ~/.dns-services/templates/example-com.yaml
```

3. Apply template with different modes:
```bash
# Force mode (update/create all records)
dns-services template apply template.yaml -d example.com -e production

# Create only missing records
dns-services template apply template.yaml -d example.com -e production -m create-missing

# Update only existing records
dns-services template apply template.yaml -d example.com -e production -m update-existing

# Dry run to see changes
dns-services template apply template.yaml -d example.com -e production --dry-run
```

4. View change history:
```bash
# List all changes
dns-services template changes

# Filter by status
dns-services template changes --status pending

# Show specific change
dns-services template show-change CHG_20230615_123456
```

#### Python API Usage

```python
from dns_services_gateway import DNSServicesClient

async with DNSServicesClient() as client:
    # Load and validate template
    template = await client.load_template("my-domain-template.yaml")

    # Apply template with dry-run
    result = await client.apply_template(
        template,
        domain="example.com",
        environment="production",
        mode="force",  # or "create-missing", "update-existing"
        dry_run=True
    )

    # Apply template if dry-run looks good
    if result.is_valid:
        await client.apply_template(
            template,
            domain="example.com",
            environment="production",
            mode="force",
            dry_run=False
        )
```

### Template Best Practices

1. **Version Your Templates**: Always include version information in template metadata
2. **Use Variables**: Make templates reusable by using variables for common values
3. **Group Records**: Organize records by purpose (web, mail, security, etc.)
4. **Include Documentation**: Add descriptions to records and document template purpose
5. **Test Changes**: Always use dry-run before applying templates
6. **Back Up Records**: Enable backup feature in template settings
7. **Environment Separation**: Use environment-specific overrides for different stages
8. **Change Management**: Enable approval workflow for production changes
9. **Notifications**: Configure email/Slack notifications for important changes
10. **Use Appropriate Modes**: Choose the right application mode for your use case

### Safety Features

Templates include several safety features:
- Pre-application validation
- Automatic backup of existing records
- Automatic rollback on failure
- Change approval workflow
- Email and Slack notifications
- Detailed change logging
- Change tracking with unique IDs
- Multiple application modes
- Dry-run capability
- Conflict detection
- Version compatibility checking

For more details and examples, see the [Template Documentation](docs/templates.md).

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
from dns_services_gateway.dnssec import DNSSECManager

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

# List domains with pagination and metadata
response = await client.list_domains(
    page=1,
    per_page=20,
    include_metadata=True,
    filters={"status": "active", "expiring_within_days": 30}
)

# Access bulk domain information
for domain in response.domains:
    print(f"Domain: {domain.name}")
    print(f"Status: {domain.status}")
    print(f"Expires: {domain.expiration_date}")
    print(f"Nameservers: {', '.join(domain.nameservers)}")

# Get domain details with full metadata
response = await client.get_domain_details("example.com")

# Verify domain
response = await client.verify_domain("example.com")

# Get domain metadata
response = await client.get_domain_metadata("example.com")

# Check domain availability
response = await client.check_domain_availability(
    domain="example.com",
    check_premium=True  # Optional: check if domain is premium
)

# List available TLDs
response = await client.list_available_tlds()
for tld in response.tlds:
    print(f"{tld.name}: {tld.price} {tld.currency}")

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

# Manage DNSSEC keys
dnssec_manager = client.dnssec

# List DNSSEC keys
response = await dnssec_manager.list_keys("example.com")
for key in response.keys:
    print(f"Key tag: {key.key_tag}, Algorithm: {key.algorithm}")

# Add a DNSSEC key
response = await dnssec_manager.add_key(
    domain="example.com",
    algorithm=13,  # ECDSAP256SHA256
    public_key="your_public_key_data",
    flags=256  # Optional flags
)

# Remove a DNSSEC key
response = await dnssec_manager.remove_key(
    domain="example.com",
    key_tag=12345
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
- [API Reference](docs/reduced-scope-swagger.json)
- [DNS.Services API page](https://dns.services/userapi?python#)

## Known Issues

### Test Coverage Reporting

When running tests with pytest-cov (coverage.py 6.0.0), you may see the following warning:

```
/venv/lib/python3.12/site-packages/coverage/inorout.py:508: CoverageWarning: Module src/dns_services_gateway/domain.py was never imported. (module-not-imported)
```

This is a known issue with coverage.py when using Python 3.12.3. The warning is a false positive and does not affect the actual test coverage (currently at 97%) or functionality. The module is properly imported and tested, but coverage.py sometimes fails to detect imports in certain Python module structures.

For more information, see:
- Coverage.py version: 6.0.0
- Python version: 3.12.3

This issue will be resolved when coverage.py releases an update that better handles Python 3.12's module system.

## Contributing

Please follow the guidelines in `docs/guidelines.md` for contributing to this project.
