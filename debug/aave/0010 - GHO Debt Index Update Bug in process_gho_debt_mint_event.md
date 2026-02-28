# Issue 0010: GHO Debt Index Update Bug in _process_gho_debt_mint_event

**Issue ID:** 0010  
**Date:** 2026-02-28  
**Status:** Fixed

## Issue: GHO Debt Index Not Updated from Mint Event

**Symptom:**
```
AssertionError: User 0x0fd3E4B5FcaC38ba6E48e9c7703805679eDFCcC4: debt last_index (1000919640646688461729030319) does not match contract (1000919954862378321350351390) @ 0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B at block 17859071
```

## Root Cause

The `_process_gho_debt_mint_event` function in `src/degenbot/cli/aave.py` was fetching the debt index from the Pool contract via RPC call instead of using the index already provided by the GHO debt token processor's result.

The processor's `process_mint_event()` method correctly extracts the index from the Mint event (which contains the current global index at the time the Mint was executed), but this value was being ignored. Instead, the code made a separate RPC call to `_get_current_borrow_index_from_pool()` which could fail or return incorrect/stale data.

### Affected Code Location

**File:** `src/degenbot/cli/aave.py`  
**Function:** `_process_gho_debt_mint_event()`  
**Lines:** 4843-4855 (before fix)

### Original Buggy Code

```python
# Apply the calculated balance delta
debt_position.balance += gho_result.balance_delta
# Always fetch the current global index from the contract.
# The asset's cached borrow_index may be stale (from a previous block).
# The event's index is the user's cached lastIndex, not the current global index.
pool_contract = _get_contract(market=context.market, contract_name="POOL")
fetched_index = _get_current_borrow_index_from_pool(
    w3=context.w3,
    pool_address=get_checksum_address(pool_contract.address),
    underlying_asset_address=get_checksum_address(debt_asset.underlying_token.address),
    block_number=context.event["blockNumber"],
)
# Use fetched index if available, otherwise fall back to event index
current_index = fetched_index if fetched_index is not None else index
debt_position.last_index = current_index
```

### Fixed Code

```python
# Apply the calculated balance delta
debt_position.balance += gho_result.balance_delta
# Use the new_index from the processor result, which is the event's index.
# The processor already extracts the correct index from the Mint event.
# The event's index is the current global index at the time of the Mint.
debt_position.last_index = gho_result.new_index
```

## Transaction Details

- **Hash:** 0x7120d824085292eafa6d540a17386f4a09168c658d17ea47d2705cd002a81636
- **Block:** 17859071
- **Type:** Uniswap Universal Router swap with stkAAVE staking
- **User:** 0x0fd3E4B5FcaC38ba6E48e9c7703805679eDFCcC4
- **Asset:** GHO Variable Debt Token (0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B)

### Event Analysis

The transaction triggered a Mint event on the GHO Variable Debt Token with:
- `value`: 0
- `balanceIncrease`: 0
- `index`: 1000919954862378321350351390 (correct current global index)

This Mint event was triggered by stkAAVE staking activity in the same transaction, which calls `updateDiscountDistribution()` and results in a zero-value Mint to update the user's index.

### Index Values

| Source | Value |
|--------|-------|
| Database (wrong) | 1000919640646688461729030319 |
| Contract getPreviousIndex | 1000919954862378321350351390 |
| Mint Event | 1000919954862378321350351390 |

Difference: 314,215,689,859,621,321,071

## Fix Applied

Updated `_process_gho_debt_mint_event` to use `gho_result.new_index` directly instead of fetching from the Pool contract:

1. Removed the redundant `_get_current_borrow_index_from_pool` call
2. Changed `debt_position.last_index = current_index` to `debt_position.last_index = gho_result.new_index`
3. Updated `_refresh_discount_rate` call to use `gho_result.new_index` instead of `current_index`

**Files Modified:**
- `src/degenbot/cli/aave.py` (lines 4841-4855, 4872)

**Additional Files Created:**
- `tests/cli/test_aave_gho_debt_index_update.py` - Unit tests for the fix

## Key Insight

The GHO debt token processor already extracts the correct index from the Mint event. Making an additional RPC call to fetch the same value is:
1. **Unnecessary** - The event already contains the correct index
2. **Error-prone** - RPC calls can fail or return stale/incorrect data
3. **Inefficient** - Adds unnecessary latency and RPC usage

**Trust the processor result** - it's designed to extract correct values from events.

## Refactoring Recommendations

1. **Remove redundant RPC calls:** The processor already extracts all necessary data from events. Avoid making additional contract calls when the data is already available in the processor result.

2. **Trust processor results:** The processor pattern is designed to extract and calculate values from events. Use these results directly instead of re-fetching from contracts.

3. **Event data validation:** Add assertions to verify that processor results match expected values from event data, catching discrepancies early.

4. **Documentation:** Clarify in docstrings that processor results contain the authoritative values extracted from events, and additional RPC calls are unnecessary.

## Testing

All existing tests pass:
- 149 CLI tests: ✅ PASSED
- 62 Aave processor tests: ✅ PASSED
- 5 new tests for this fix: ✅ PASSED

### New Test Coverage

Created `tests/cli/test_aave_gho_debt_index_update.py` with tests that verify:
1. The processor correctly extracts the index from Mint events
2. The extracted index matches the expected value from the transaction
3. Zero-value Mint events (index updates) are processed correctly
4. The processor uses the event index exactly as provided

## Verification

The fix ensures that:
1. ✅ The index from Mint events is used directly
2. ✅ No redundant RPC calls are made to fetch the index
3. ✅ The database is updated with the correct index value
4. ✅ All existing functionality continues to work
