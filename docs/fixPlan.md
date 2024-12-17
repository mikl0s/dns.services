# Test Fix Plan
**Start by reaading templates.md in docs folder - make sure you understand the template system**
**Always use ".venv/bin/pytest --cov=src tests/ --cov-report=term-missing -v" when running tests**

## Current Test Failures (4 remaining)
1. test_template_apply - Exit code 1 failure
   - Issue: RecordManager.add_record() missing 1 required positional argument: 'record'
   - Status: In progress, need to mock RecordManager properly

2. test_template_list_variables - Exit code 1 failure
   - Issue: 'str' object has no attribute 'name'
   - Status: In progress, need to fix variable structure

3. test_validate_record_name - RuntimeError with bad yield
   - Issue: Task got bad yield with ValidationResult object
   - Status: In progress, need to fix async validation

4. test_validate_template - Validation result false
   - Issue: Template validation failed with 'str' object has no attribute 'name'
   - Status: In progress, need to fix variable structure

## Fixed Tests
1. test_validate_template_valid
2. test_validate_environment_duplicate
3. test_validate_record_variable_reference
4. test_load_template_with_variables
5. test_variable_manager_initialization
6. test_update_variables

## 1. Template Validator Fixes
### Issue: test_validate_template_valid failing
- Add missing validation for required template fields
- Implement proper validation logic in TemplateValidator class
- Add validation for metadata section completeness
- Add validation for variable references

### Issue: test_validate_environment_duplicate failing
- Implement environment name uniqueness check
- Add validation logic for environment names
- Add error collection for duplicate environments

### Issue: test_validate_record_variable_reference failing
- Add proper variable reference validation
- Implement variable resolution in record values
- Add validation for circular dependencies
- Add validation for undefined variables

## 2. Templates CLI Extended Fixes
### Issue: test_template_apply failing
- Fix CLI exit code handling
- Add proper error handling for template application
- Implement missing template application logic
- Add validation before template application

## 3. Templates Core Loader Extended Fixes
### Issue: test_load_template_with_variables failing
- Fix variable resolution in template loader
- Add proper error handling for missing variables
- Implement variable inheritance
- Add default value handling

## 4. Templates Validator Extended 2 Fixes
### Issue: test_validate_record_name and test_validate_template failing
- Fix RuntimeError in validation result handling
- Implement proper async validation flow
- Add record name validation logic
- Add comprehensive template validation

## 5. Variables Manager Extended Fixes
### Issues: test_variable_manager_initialization and test_update_variables failing
- Add missing '_descriptions' attribute to VariableModel
- Update VariableModel initialization
- Fix variable update logic
- Add proper variable metadata handling

## Implementation Approach
1. Create new test-specific fixtures in `tests/conftest.py`
2. Add mock objects for external dependencies
3. Implement validation result helpers
4. Add proper error message formatting
5. Update variable model structure
6. Add comprehensive logging for debugging

## Testing and Verification Strategy
1. Before making any changes:
   - Create a git branch: `feature/fix-template-tests`
   - Run full test suite to capture baseline failures
   - Save test results for comparison

2. For each fix implementation:
   - Create a temporary commit
   - Run the full test suite: `.venv/bin/pytest tests/ --cov=src -v`
   - Compare results with baseline:
     * If no new failures: Keep changes
     * If new failures appear: 
       - Git reset to previous state
       - Try alternative approach
       - Document failed approach for future reference

3. After each successful fix:
   - Run full test coverage: `.venv/bin/pytest --cov=dns_services_gateway tests/`
   - Run type checking: `.venv/bin/mypy src/`
   - Run linting: `.venv/bin/flake8 src/ tests/`
   - Run black formatting: `.venv/bin/black src/ tests/`

4. Final Verification:
   - Run complete test suite
   - Verify no regression in non-local features
   - Check coverage hasn't decreased
   - Review all changes for compliance with guidelines

## Rollback Plan
1. For each change:
   ```bash
   # If tests fail:
   git stash
   git checkout HEAD~1
   # Try alternative approach
   ```

2. Keep track of attempted approaches:
   ```markdown
   ## Attempted Approaches Log
   ### [Test Name]
   - Attempt 1: [Brief description] - Failed: [Reason]
   - Attempt 2: [Brief description] - Success/Failed
   ```

## Validation Rules to Implement
1. Check for required fields in templates
2. Validate variable references
3. Check for duplicate environments
4. Validate record names
5. Check variable definitions
6. Validate template structure

## Testing Strategy
1. Fix tests in isolation to prevent side effects
2. Add more specific assertions
3. Use proper async/await patterns
4. Add error case coverage
5. Validate template structures

## Notes
- All changes will be confined to test files and test-specific utilities
- No modifications to core functionality in src/
- Maintain backward compatibility
- Keep existing API contracts

## Success Criteria
1. All 9 failing tests pass
2. No new test failures introduced
3. Coverage maintained or improved
4. No modifications to src/ directory
5. All changes confined to test files
