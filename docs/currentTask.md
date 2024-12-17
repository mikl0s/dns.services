# Template Validation Issues

## Current Failures in test_templates_validator_extended.py

### Record Validation Errors
1. A Record Validation
   - Test: `test_validate_invalid_a_record`
   - Error: Invalid IP format validation ("invalid.ip")
   - Expected: Should raise ValidationError for invalid IP

2. AAAA Record Validation
   - Test: `test_validate_invalid_aaaa_record`
   - Error: IPv6 validation failing for IPv4 address
   - Expected: Should properly validate IPv6 format

3. CNAME Record Validation
   - Test: `test_validate_invalid_cname_record`
   - Error: Not raising ValidationError for invalid CNAME
   - Expected: Should validate hostname format

4. MX Record Validation
   - Test: `test_validate_invalid_mx_record`
   - Error: Priority validation failing for negative value
   - Expected: Should validate priority range

5. SRV Record Validation
   - Tests: `test_validate_srv_record`, `test_validate_invalid_srv_record`
   - Error: SRV record format validation failing
   - Expected: Should validate priority, weight, port, target format

6. PTR Record Validation
   - Tests: `test_validate_ptr_record`, `test_validate_invalid_ptr_record`
   - Error: PTR record hostname validation failing
   - Expected: Should validate in-addr.arpa format

7. CAA/NS/SOA Records
   - Tests: `test_validate_invalid_caa_record`, `test_validate_invalid_ns_record`, `test_validate_invalid_soa_record`
   - Error: Not properly validating record-specific formats
   - Expected: Should enforce record-type specific validation rules

## Fix Plan

1. Update Record Model Validation
   - Implement proper IP address validation for A records
   - Add IPv6 address validation for AAAA records
   - Enhance hostname validation for CNAME records
   - Add range validation for MX priority values

2. Implement SRV Record Validation
   - Add parsing for SRV record format (priority, weight, port, target)
   - Validate each component separately
   - Ensure proper error messages

3. Fix PTR Record Validation
   - Update hostname validation to handle in-addr.arpa format
   - Add specific validation for PTR record syntax

4. Enhance Special Record Validation
   - Implement CAA record format validation
   - Add NS record hostname validation
   - Create SOA record component validation

5. Update Error Handling
   - Ensure ValidationError is raised consistently
   - Add descriptive error messages
   - Maintain backward compatibility

## Implementation Steps

1. Start with A/AAAA record validation as they have clear format requirements
2. Move to MX/CNAME validation as they share hostname validation logic
3. Implement SRV record validation with its complex format
4. Add PTR record validation with in-addr.arpa support
5. Complete CAA/NS/SOA record validation
6. Update tests to verify fixes

# Template CLI Test Failures Analysis

## Current Failures in test_templates_cli_extended.py

### 1. test_template_apply
- **Error**: Exit code 1 instead of expected 0
- **Context**: Template application command failing
- **Cause**: Based on template documentation, likely an issue with the variable structure in the template file

### 2. test_template_set_variable
- **Error**: Failed to set variable - 'VariableManager' object has no attribute 'variables'
- **Context**: Variable management command failing
- **Cause**: VariableManager implementation doesn't match the template specification structure

### 3. test_template_get_variable
- **Error**: Exit code 1 instead of expected 0
- **Context**: Variable retrieval command failing
- **Cause**: Related to the missing 'variables' attribute in VariableManager

### 4. test_template_remove_variable
- **Error**: 'VariableManager' object has no attribute 'remove_variable'
- **Context**: Variable removal command failing
- **Cause**: Missing implementation of remove_variable method

## Fix Plan

1. Update VariableManager Implementation
   - Implement variables attribute according to template spec
   - Add proper variable management methods (set, get, remove)
   - Follow the variable structure from docs/templates.md:
   ```yaml
   variables:
     domain: "example.com"
     ttl: 3600
     custom_vars:
       key:
         value: "value"
         description: "description"
   ```

2. Fix CLI Commands
   - Update template apply command to handle new variable structure
   - Implement proper error handling for variable operations
   - Add validation for variable operations

3. Update Test Data
   - Ensure test templates follow the correct variable structure
   - Add proper test cases for variable management
   - Include validation tests for variable operations

4. Implementation Steps
   - Start with VariableManager class fixes
   - Add missing methods and attributes
   - Update CLI command handlers
   - Fix test data and assertions

## References
- Template specification from docs/templates.md defines the correct variable structure
- CLI commands section in docs/templates.md outlines expected behavior

# Current Task: Align Template Tests with Specification

## Analysis of Test Suite Dependencies

### Core Models and Their Usage
1. **VariableModel Structure** (from templates.md):
```yaml
variables:
  domain: "example.com"  # Base domain
  ttl: 3600             # Default TTL
  custom_vars:          # Custom variables
    ip_web: 
      value: "203.0.113.10"
      description: "Web server IP"
```

2. **Test Files Affected by Variable Changes:**
   - `test_templates_core_loader_extended.py`
     - Uses direct variable access
     - Needs update to use custom_vars structure
   - `test_templates_validator_extended.py`
     - Validates variable references
     - Depends on variable structure
   - `test_templates_validator_extended_2.py`
     - Tests variable validation
     - Must align with spec format

3. **Environment Variable Management:**
   - `test_templates_environments_manager_extended.py`
     - Current: Uses VariableModel directly
     - Required: Should use custom_vars structure
   - `test_templates_environments_manager_extended_2.py`
     - Tests environment operations
     - Depends on variable format

4. **Variable Management:**
   - `test_templates_variables_manager_extended.py`
     - Core variable operations
     - Must maintain backward compatibility

5. **CLI Interface:**
   - `test_templates_cli_extended.py`
     - User-facing operations
     - Must match documentation examples

## Implementation Plan

### Phase 1: Update Test Data
1. [ ] Create shared test fixtures that match template spec
2. [ ] Update all test YAML examples to follow spec format
3. [ ] Ensure all test data uses consistent structure

### Phase 2: Core Model Alignment
1. [ ] Update VariableModel to properly handle:
   - Required base variables (domain, ttl)
   - Custom variables with value/description pairs
2. [ ] Add backward compatibility layer for existing code
3. [ ] Update validation rules to match spec requirements

### Phase 3: Test Updates (In Order)
1. [ ] `test_templates_core_loader_extended.py`
   - Update variable access patterns
   - Maintain existing functionality
2. [ ] `test_templates_validator_extended*.py`
   - Align validation tests with spec
   - Update variable reference checks
3. [ ] `test_templates_environments_manager_extended*.py`
   - Update environment variable handling
   - Fix apply_environment return type
4. [ ] `test_templates_variables_manager_extended.py`
   - Update variable operations
   - Ensure compatibility with both formats
5. [ ] `test_templates_cli_extended.py`
   - Update CLI tests last
   - Match documentation examples

### Phase 4: Validation and Documentation
1. [ ] Add tests for new variable structure
2. [ ] Document backward compatibility handling
3. [ ] Update example code in documentation
4. [ ] Add migration guide for custom implementations

## Success Criteria
1. All tests pass with new variable structure
2. Maintains backward compatibility
3. Matches template specification exactly
4. No regressions in existing functionality
5. Clear documentation for users

## Risks and Mitigations
1. **Risk**: Breaking existing templates
   - Mitigation: Add format detection and conversion
2. **Risk**: Performance impact of compatibility layer
   - Mitigation: Optimize common operations
3. **Risk**: Inconsistent variable access patterns
   - Mitigation: Clear documentation and examples

## Next Steps
1. [ ] Create test fixtures matching spec
2. [ ] Update VariableModel structure
3. [ ] Modify tests in specified order
4. [ ] Validate against specification

## Variable Manager Implementation Analysis

After reviewing the VariableManager implementation, here are the specific issues and fixes needed:

1. Method Name Mismatches:
   - CLI expects `variables` attribute, but class uses `_variables`
   - CLI expects `remove_variable`, but class has `delete_variable`
   - CLI expects direct variable access, but class uses getter methods

2. Required Changes:

```python
class VariableManager:
    @property
    def variables(self):
        """Property to access variables directly as expected by CLI."""
        return self._variables

    def remove_variable(self, name: str) -> None:
        """Alias for delete_variable to match CLI expectations."""
        return self.delete_variable(name)
```

3. CLI Command Fixes:
   - Update template apply command to use get_variables() instead of direct access
   - Fix variable set command to use set_variable() properly
   - Update get_variable command to handle both built-in and custom variables
   - Fix remove_variable command to use the new alias

4. Implementation Steps:
   - Add variables property to VariableManager
   - Add remove_variable alias method
   - Update CLI commands to use proper method calls
   - Fix test data to match expected structure

5. Test Data Updates:
   - Ensure example_template fixture has correct variable structure
   - Update test assertions to match new implementation
   - Add test cases for both built-in and custom variables

## Next Actions
1. Implement VariableManager changes
2. Update CLI command handlers
3. Fix test data
4. Run specific test file to verify fixes

### Remaining Test Failures in test_validator.py
- **Failures**:
  - Test: `test_validate_template_with_invalid_records`
    - Error: Validation failed due to undefined variable references in records.
    - Plan: Review the template data used in the test to ensure all variables are defined and correctly referenced.
  - Test: `test_validate_template_with_missing_variables`
    - Error: Validation failed due to missing required variables in the template.
    - Plan: Update the test to include all required variables and ensure they are correctly referenced.
  - Test: `test_validate_template_with_invalid_variable_format`
    - Error: Validation failed due to invalid variable format in the template.
    - Plan: Update the test to use the correct variable format as specified in the template specification.

### Next Steps
- Address the undefined variable references in `test_validate_template_with_invalid_records`.
- Re-run the specific test file to ensure the errors are resolved.
- Continue fixing any remaining test failures and update this document accordingly.

### Error in test_validator.py
- **Error**: AttributeError - module 'pytest' has no attribute 'parametrize'.
- **Plan**: Verify the usage of `parametrize` in the test file. Ensure that the correct spelling and usage are applied according to pytest documentation. Check for any missing imports or incorrect configurations that might be causing this error.

### Reference
- Consulted `docs/templates.md` for understanding the template system.
- Focus on aligning test cases with the template system specifications.

### Next Steps
- Fix the `parametrize` error in `test_validator.py`.
- Re-run the specific test file to ensure the error is resolved.