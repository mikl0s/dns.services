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
  domain: "example.com"  # Base domain for records
  ttl: 3600             # Default TTL for records
  custom_vars:          # Custom variables
    ip_web: 
      value: "203.0.113.10"
      description: "Web server IP"
    ip_mail:
      value: "203.0.113.20"
      description: "Mail server IP"
```

### Records Section
```yaml
records:
  A:
    - name: "@"
      value: ${ip_web}
      ttl: ${ttl}
      description: "Main website"
  
  CNAME:
    - name: "www"
      value: "@"
      ttl: ${ttl}
      description: "WWW alias"
  
  MX:
    - name: "@"
      value: "mail.${domain}"
      priority: 10
      ttl: ${ttl}
      description: "Primary mail server"
```

### Environments Section
```yaml
environments:
  production:
    variables:
      ttl: 3600
    records:
      TXT:
        - name: "_dmarc"
          value: "v=DMARC1; p=reject;"
          ttl: ${ttl}

  staging:
    variables:
      ttl: 300
    records:
      TXT:
        - name: "_dmarc"
          value: "v=DMARC1; p=none;"
          ttl: ${ttl}
```

## CLI Commands

### Template Management
- `template create NAME [--description DESC] [--author AUTHOR]` - Create a new template
- `template init TEMPLATE_FILE` - Initialize template with basic structure
- `template list` - List available templates
- `template show TEMPLATE_FILE` - Display template contents
- `template validate TEMPLATE_FILE` - Validate template structure and records
- `template export TEMPLATE_FILE` - Export template to stdout
- `template diff TEMPLATE_FILE OTHER_FILE` - Show differences between templates

### Variable Management
- `template set-variable TEMPLATE_FILE KEY=VALUE [--description DESC]` - Set template variable
- `template get-variable TEMPLATE_FILE KEY` - Get variable value
- `template remove-variable TEMPLATE_FILE KEY` - Remove variable
- `template list-variables TEMPLATE_FILE` - List all variables

### Template Application
- `template apply TEMPLATE_FILE --domain DOMAIN --env ENV [--dry-run] [--force] [--mode MODE]`
  - Modes:
    - `force` - Create new records and update existing ones (default)
    - `create-missing` - Only create records that don't exist
    - `update-existing` - Only update records that already exist

### Backup and Recovery
- `template backup TEMPLATE_FILE` - Create template backup
- `template restore TEMPLATE_FILE` - Restore from backup

## Features

### Variable Substitution
- Use `${variable_name}` syntax in any string field
- Environment variables override global variables
- Built-in variables: `domain`, `ttl`
- Custom variables with descriptions

### Record Validation
- Type-specific validation (A, AAAA, MX, TXT, SRV, etc.)
- Value format checking
- Required field validation
- TTL range validation

### Environment Support
- Environment-specific variables
- Environment-specific records
- Inheritance from base configuration
- Multiple environment support (production, staging, etc.)

### Safety Features
- Backup and restore functionality
- Change tracking
- Dry-run mode
- Validation before apply
- Rollback capability

## Best Practices

1. Use descriptive variable names
2. Add descriptions to records
3. Group related records
4. Test in staging environment first
5. Use dry-run before applying changes
6. Keep templates version controlled
7. Document template purpose and usage
8. Validate templates before deployment
9. Use environment-specific configurations
10. Implement proper security records

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
  A:
    - name: "@"
      value: ${ip_web}
      condition: ${environment} == "production"
```

### Custom Validation Rules
```yaml
validation:
  rules:
    - name: "require-www"
      condition: "any(r.name == 'www' for r in records.A)"
      message: "Missing www CNAME record"
```

### Record Dependencies
```yaml
records:
  A:
    - name: "@"
      value: ${ip_web}
      id: main-a

    - name: "www"
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
