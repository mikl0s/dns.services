# Instructions

This project connects to a 3rd party API we do not control. Template functionality is a local feature we control the entire pipeline.
**Following the steps is paramount, do not do ANYTHING outside what the steps command.**

## Step 1

Read @guidelines.md

## Step 2

Describe what you learned from @guidelines.md

## Step 3

Read @currentTask.md and see if it has been completed, if is has not been completed, complete the tasks before proceeding with the steps below

## Step 4

Run the unit tests for the entire codebase
Use this to run the initial unit tests: .venv/bin/pytest --cov=src tests/ --cov-report=term-missing -v

## Step 5

If there are test failures - follow these substeps:

5.1 - Select and focus on the file with the most failures/errors in the template codebase. Do not start fixing anything - proceed with the steps.
5.2 - **Read @templates.md ** - this is your reference documentation for the template system - do NOT summarize, read in detail.
5.3 - Describe the errors in the selected test file in markdown format in @currentTask.md together with your plan to fix these errors.
5.4 - For template functionality you do not need the API reference as templating is a local feature.
5.5 - Work on fixing all the failures in that specific unit test file. Update @currentTask.md after each change to a test or source code with descriptions of changes and expected outcome.
5.6 - If a fix does not accomplish its intended fix, update @currentTask.md with the lessons learned.
5.6 - Run the unit tests again, **but only the unites tests on the file we are working on for a faster workflow**, to ensure there are no more failures.
5.7 - Continue to work on the unit tests, fixing any remaining failures or warnings. **Keep updating @currentTask.md **
5.8 - Go back to step 5.6 and continue by executing step 5.6 again and progessing so we loop until all errors are fixed.

**NOTE: Sometimes running a single unit test can provide additional context on how to fix the issue.**
