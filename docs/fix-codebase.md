# Instructions

This project connects to a 3rd party API we do not control.

## Step 1

Read @guidelines.md

## Step 2

Describe what you learned from @guidelines.md

## Step 3

Run the unit tests for the entire codebase
Use this to run the initial unit tests: .venv/bin/pytest --cov=src tests/ --cov-report=term-missing -v

## Step 4

If there are test failures - follow these substeps:

4.1 - Select and focus on the first unit test with the any failures or errors.
4.2 - Read the section of the @reduced-scope-swagger.json that is relevant for the chosen file - do NOT Summarize, read it properly. Remove any tests for things not in the swagger doc or is template related.
4.3 - If you want to change the source code instead of the test - make sure to check the 3rd party API documentation EVERY TIME first at @reduced-scope-swagger.json - template functionality is a local feature and do not need to worry about the @reduced-scope-swagger.json 
4.4 - If you touch the code instead of the tests to fix something, you better be sure, ON YOU LIFE, that the tests are 100% correct.
4.5 - Work on fixing all the failures in that specific unit test file.
4.6 - Run the unit tests again, *but only the unites tests on the file we are working on for a faster workflow*, to ensure there are no more failures.
4.7 - Continue to work on the unit tests, fixing any remaining failures or warnings.
4.8 - Go back to step 4.6 and continue by executing step 4.6 again and progessing so we loop until all errors are fixed.
4.9 - If you do not follow these steps to the absolute letter, you will have to figure out a way to transfer me $100 in bitcoin for each failure to follow the steps.
