# DNS Template System Documentation

## Overview

The DNS Template System provides a powerful way to manage DNS configurations across multiple domains and environments. It allows you to define reusable DNS configurations with variable substitution, environment-specific overrides, and comprehensive validation.

## Template Structure

A DNS template is a YAML file with the following main sections:

### Metadata Section
```yaml
metadata:
  version: "1.0.0"
  description: "Web and mail configuration for example.com"
  author: "DNS Services Gateway"
  created: "2024-03-20"
  updated: "2024-03-21"
  tags:
    - web
    - mail
    - security
```

### Variables Section
```yaml
variables:
  domain: "example.com"
  ttl: 3600
  ip_web: "203.0.113.10"
  ip_mail: "203.0.113.20"
  hostmaster: "hostmaster@example.com"
```

### Records Section
```yaml
records:
  # Web hosting records
  web:
    - type: A
      name: "@"
      value: ${ip_web}
      ttl: ${ttl}
      description: "Main website"

    - type: CNAME
      name: "www"
      value: "@"
      ttl: ${ttl}
      description: "WWW alias"

  # Mail server records
  mail:
    - type: MX
      name: "@"
      value: "mail.${domain}"
      priority: 10
      ttl: ${ttl}
      description: "Primary mail server"

    - type: TXT
      name: "@"
      value: "v=spf1 mx -all"
      ttl: ${ttl}
      description: "SPF record"

  # Security records
  security:
    - type: CAA
      name: "@"
      value: "0 issue \"letsencrypt.org\""
      ttl: ${ttl}
      description: "CAA record for Let's Encrypt"
```

### Environments Section
```yaml
environments:
  production:
    variables:
      ttl: 3600
    records:
      security:
        - type: TXT
          name: "_dmarc"
          value: "v=DMARC1; p=reject; rua=mailto:dmarc@${domain}"
          ttl: ${ttl}

  staging:
    variables:
      ttl: 300
      domain: "staging.example.com"
    records:
      security:
        - type: TXT
          name: "_dmarc"
          value: "v=DMARC1; p=none; rua=mailto:dmarc-staging@${domain}"
          ttl: ${ttl}
```

## Template Features

### Variable Substitution
- Use `${variable_name}` syntax to reference variables
- Variables can be used in any string field
- Environment-specific variables override global variables
- Supports nested variable references

### Record Groups
- Group records by purpose (web, mail, security, etc.)
- Improves template organization and maintainability
- Makes it easier to enable/disable specific functionality

### Environment Overrides
- Define different configurations for production, staging, development
- Override variables per environment
- Add or modify records per environment
- Inherit from base configuration

### Safety Features

#### Validation
- Schema validation of template structure
- Record type-specific validation
- Variable reference validation
- Circular dependency detection

#### Backup and Rollback
```yaml
settings:
  backup:
    enabled: true
    retention: 30  # days
  rollback:
    enabled: true
    automatic: true  # auto-rollback on error
```

#### Change Management
```yaml
settings:
  changes:
    require_approval: true
    notify:
      - email: "dns-admin@example.com"
      - slack: "#dns-changes"
```

## Best Practices

### 1. Version Control
- Always include version information in metadata
- Use semantic versioning
- Document changes in template

### 2. Documentation
- Add descriptions to records
- Document template purpose
- Include usage examples
- Document dependencies

### 3. Variables
- Use descriptive variable names
- Group related variables
- Set sensible defaults
- Document expected values

### 4. Testing
- Test templates in staging first
- Use dry-run feature
- Validate DNS propagation
- Monitor for errors

### 5. Security
- Use DNSSEC where possible
- Implement SPF, DKIM, DMARC
- Regular security reviews
- Limit access to templates

## CLI Usage

### Creating Templates
```bash
dns-services template create --name web-mail-template
```

### Validating Templates
```bash
dns-services template validate my-template.yaml
```

### Applying Templates
```bash
dns-services template apply my-template.yaml --domain example.com --env production
```

### Dry Run
```bash
dns-services template apply my-template.yaml --domain example.com --env production --dry-run
```

### Backup and Restore
```bash
# Create backup
dns-services template backup example.com

# List backups
dns-services template backups list example.com

# Restore from backup
dns-services template restore example.com --backup 2024-03-21-143022
```

## API Usage

### Loading Templates
```python
from dns_services_gateway import DNSServicesClient

async with DNSServicesClient() as client:
    # Load template
    template = await client.load_template("my-template.yaml")

    # Validate template
    validation = await template.validate()
    if not validation.is_valid:
        print("Template errors:", validation.errors)
```

### Applying Templates
```python
# With dry run
result = await client.apply_template(
    template,
    domain="example.com",
    environment="production",
    dry_run=True
)

# Check dry run results
if result.is_valid:
    changes = result.get_changes()
    print("Planned changes:", changes)

    # Apply if changes look good
    await client.apply_template(
        template,
        domain="example.com",
        environment="production"
    )
```

### Managing Backups
```python
# Create backup
backup = await client.create_backup("example.com")

# List backups
backups = await client.list_backups("example.com")

# Restore from backup
await client.restore_backup("example.com", backup_id=backup.id)
```

## Error Handling

### Common Template Errors
1. Invalid variable references
2. Missing required fields
3. Invalid record values
4. Circular dependencies
5. Environment conflicts

### Error Response Example
```python
try:
    await client.apply_template(template, domain="example.com")
except TemplateValidationError as e:
    print("Template validation failed:", e.errors)
except TemplateApplicationError as e:
    print("Template application failed:", e.message)
    if e.has_rollback:
        print("Rolled back to previous state")
```

## Advanced Features

### Template Inheritance
```yaml
inherit:
  - base-template.yaml
  - security-template.yaml
```

### Conditional Records
```yaml
records:
  web:
    - type: A
      name: "@"
      value: ${ip_web}
      condition: ${environment} == "production"
```

### Custom Validation Rules
```yaml
validation:
  rules:
    - name: "require-www"
      condition: "any(r.name == 'www' for r in records.web)"
      message: "Missing www CNAME record"
```

### Record Dependencies
```yaml
records:
  web:
    - type: A
      name: "@"
      value: ${ip_web}
      id: main-a

    - type: CNAME
      name: "www"
      value: "@"
      depends_on: main-a
```

## Migration Guide

### From Manual DNS to Templates
1. Export current DNS records
2. Create template structure
3. Add variables for common values
4. Group records by purpose
5. Add environment configurations
6. Validate and test template
7. Apply template with monitoring

### Version Upgrade Path
1. v0.9.0: Initial template support
2. v0.9.1: Added environment overrides
3. v1.0.0: Full template system with validation
4. v1.1.0: Added backup and rollback
5. v1.2.0: Advanced features (inheritance, conditions)
