---
description: Debug Aave update failures
agent: build
---

## DIRECTION: 
Execute `uv run degenbot aave update` with the option `--debug-output=./.opencode/tmp/{FILE}.log`, specifying a new log filename

## PROCESS:
### 1. Gather Information
- Grep the log for "exception" to identify the failure. Grep for relevant events, processes, and state logs leading up to the failure
- @evm-investigator Perform a thorough investigation of the transaction; use all known information about the blocks, transactions, and operations leading to the invalid state; Determine the implementation address and associated revision for proxy contracts involved in the transaction, e.g., AToken, VariableDebtToken, GHOVariableDebtToken, Pool, stkAAVE; use contract source code in @contract_reference/aave if available

### 2. Investigate Code
- Determine the execution path leading to the error
- Determine the revision of all versioned implementations, libraries, and processors that were used during processing. Check the reference contracts in @contract_reference/aave
- Make a failure hypothesis

### 3. Validate & Fix
- Determine the root cause, e.g., a processing function failed to determine the correct value from an event, the database had a stale value, a previous processing action set a value incorrectly which was used by another processing action
- Design the fix to resolve the bug. If a unique transaction requires adding sophistication to transaction matching and event validation, fix that. Do not accumulate hacks and special cases within general processors
- Apply the fix to resolve the bug
- Run a final update command to confirm the fix was successful
- Run the existing test suite to confirm it does not break any existing matching logic

### 4. Document Findings
Create a new report in @debug/aave. Follow this format:
- **Issue:** Brief title
- **Date:** Current date
- **Symptom:** Error message verbatim
- **Root Cause:** Technical explanation
- **Transaction Details:** Hash, block, type, user, asset
- **Fix:** Code location and changes
- **Key Insight:** Lesson learned for future debugging
- **Refactoring:** Concise summary of proposed improvements to code that processes these transactions
- **Filename:** {four digit ID} - {issue title}

### 5. Write Tests
- Use the investigation report and transaction details to write a stateless unit test to verify that the math operations, user operation determination, event matching logic, etc., match the expectations.
- Confirm the test suite passes

### 6. Clean Up
- Remove unneeded files in @.opencode/tmp