---
description: Debug Aave update failures
agent: build
---

## DIRECTION: 
Execute `uv run degenbot aave update` with the option `--debug-output=/tmp/{FILE}`, specifying a new log filename. 

Discover and fix the bug that lead to the failure.

## PROCESS:
### Gather Information
- Grep the log for "exception" to identify the failure. Grep for related events, processes, and state logs leading up to the failure

### Investigate Transaction
- @evm-investigator Perform a thorough investigation of the transaction; use all known information about the blocks, transactions, and operations leading to the invalid state; Determine the implementation address **at the time of the transaction** for any proxy contract involved, e.g., AToken, VariableDebtToken, GHOVariableDebtToken, Pool, stkAAVE; review the specific revision of the Aave smart contract source code stored in `contract_reference/aave`; compile a detailed report in `/tmp` showing the smart contract control flow, events, account updates, and asset flow

### Investigate Code
- Determine the execution path and processing logic used that lead to the failure
- Determine differences between the smart contract logic and the processing code
- You may inspect the contents of the sqlite database at `~/.config/degenbot`
- Make a failure hypothesis

### Validate & Fix
- Determine the root cause, e.g., a processing function failed to determine the correct value from an event, the database had a stale value, a previous processing action set a value incorrectly which was used by another processing action
- Design the fix to resolve the bug. If a unique transaction requires adding sophistication to transaction matching and event validation, fix that. Do not accumulate hacks and special cases within general processors
- Apply the fix to resolve the bug
- Run a final update command with `--to-block` set to the failing block to confirm the fix was successful
- Run the existing test suite to confirm it does not break any existing matching logic

### Document Findings
Create a new report in `debug/aave` following this format:
- **Issue:** Brief title
- **Date:** Current date
- **Symptom:** Error message verbatim
- **Root Cause:** Technical explanation
- **Transaction Details:** Hash, block, type, user, asset
- **Fix:** Code location and changes
- **Key Insight:** Lesson learned for future debugging
- **Refactoring:** Concise summary of proposed improvements to code that processes these transactions
- **Filename:** {four digit ID} - {issue title}

### Write Tests
- Use the investigation report and transaction details to write a stateless unit test to verify that the math operations, user operation determination, event matching logic, etc., match the expectations.
- Confirm the test suite passes

### Clean Up
- Convert print statements used to diagnose the problem to a generalized `logging.debug()` call