# Aave Debug Progress

## Issue: wstETH Debt Mint Events Misclassified as Collateral Mints

**Date:** 2026-02-25

**Symptom:**
```
AssertionError: User 0x310a2c115d3d45a89b59640FfF859BE0f54a08E2: debt balance (336455331017897785935) does not match scaled token contract (362884658273797549684) @ 0xC96113eED8cAB59cD8A66813bCB0cEb29F06D2e4 at block 16574551
```

## Root Cause

The root cause is a **two-part bug** in the Aave event processing:

### Part 1: Event Categorization Bug (FIXED)

In `_build_transaction_contexts()` in `src/degenbot/cli/aave.py`, the categorization logic at lines 5259-5268 incorrectly categorized all SCALED_TOKEN_MINT events that were NOT from the GHO token as `collateral_mints`:

```python
elif topic == AaveV3Event.SCALED_TOKEN_MINT.value:
    if event_address == GHO_VARIABLE_DEBT_TOKEN_ADDRESS:
        ctx.gho_mints.append(event)
    else:
        ctx.collateral_mints.append(event)  # BUG: All non-GHO mints categorized as collateral!
```

This meant that standard VariableDebtToken mint events (like wstETH) were being tracked as `collateral_mints` instead of `debt_mints`, which affected debug logging but not the actual processing.

### Part 2: Event Matching Bug (INVESTIGATED)

The EventMatcher in `src/degenbot/cli/aave_event_matching.py` may be matching debt mint events to incorrect BORROW pool events. The tracked balance is 336.455... when it should be 362.884..., a difference of 26.429...

Notably: **68.434033 - 42.0 = 26.434033**

This suggests the first debt mint (42.0 wstETH) is being subtracted from the last debt mint (68.434033 wstETH), or the wrong BORROW event is being matched to the Mint events.

## Transaction Details

- **Hash:** 0x406c6bff8ec8a76b8b5946d583ca8dabff846e716b5745211dfcc62e9529d0c3
- **Block:** 16574551
- **Type:** Multi-collateral borrow via recipe executor
- **User:** 0x310a2c115d3d45a89b59640FfF859BE0f54a08E2
- **Asset:** variableDebtEthwstETH (0xC96113eED8cAB59cD8A66813bCB0cEb29F06D2e4)

### Event Sequence

The transaction contains **6 debt mint events** (1 WETH + 5 wstETH):

| Asset | Mint # | LogIndex | Amount |
|-------|----------|----------|--------|
| WETH | 1 | 367 | 153.0 WETH |
| wstETH | 1 | 376 | 42.0 wstETH |
| wstETH | 2 | 395 | 92.0 wstETH |
| wstETH | 3 | 415 | 84.505239 wstETH |
| wstETH | 4 | 435 | 76.01 wstETH |
| wstETH | 5 | 455 | 68.434033 wstETH |

**Total wstETH minted:** 362.949272 wstETH  
**Expected scaled balance:** 362.884658...  
**Tracked scaled balance:** 336.455331...  
**Missing:** 26.429327... (approximately 68.434033 - 42.0)

## Fix Applied

### Part 1: Event Categorization

**Files Modified:**
1. `src/degenbot/cli/aave.py`
2. `src/degenbot/cli/aave_debug_logger.py`

**Changes:**

1. Added `debt_mints` and `debt_burns` lists to TransactionContext (lines 159-160)
2. Added `_get_debt_token_addresses()` helper function to get all vToken addresses
3. Updated `_build_transaction_contexts()` to accept `known_debt_token_addresses` parameter
4. Updated categorization logic to check if token is a vToken:

```python
elif topic == AaveV3Event.SCALED_TOKEN_MINT.value:
    if event_address == GHO_VARIABLE_DEBT_TOKEN_ADDRESS:
        ctx.gho_mints.append(event)
    elif event_address in known_debt_token_addresses:
        ctx.debt_mints.append(event)
    else:
        ctx.collateral_mints.append(event)
```

5. Updated debug logger to track debt mint/burn counts

**Verification:**
- Debug log now correctly shows: `"debt_mints_count": 6`
- Previously showed: `"collateral_mints_count": 12` (incorrectly included debt mints)

### Part 2: Event Matching (TODO)

Further investigation needed to determine if EventMatcher is matching debt mints to wrong BORROW events. The pattern of 68.434033 - 42.0 = 26.434033 suggests:

1. The EventMatcher may be matching Mint events to BORROW events with different amounts
2. The scaled_amount calculation from BORROW events may be incorrect
3. There may be an issue with event consumption tracking

## Key Insight

The event categorization bug was masked because the legacy processing path doesn't use the categorized lists - it iterates through all events. However, the miscategorization affected:
1. Debug logging accuracy
2. Future migration to operation-based processing (which uses categorized lists)

The balance discrepancy suggests the EventMatcher or the debt mint processing logic has a bug in how it matches Mint events to BORROW pool events.

## Transaction Processing Flow

1. **Event Fetching:** All events fetched from blockchain
2. **Categorization:** Events categorized by type (BORROW, Mint, Burn, etc.)
3. **Context Building:** Events grouped by transaction
4. **Processing:** Legacy path iterates events and dispatches to handlers
5. **Matching:** EventMatcher matches Mint events to BORROW events
6. **Balance Update:** Position balance updated with calculated delta

The bug occurs at step 5-6, where incorrect matching or calculation leads to wrong balance.

## Refactoring

Consider:
1. Adding stricter validation in EventMatcher for amount matching
2. Adding debug logging to trace which BORROW event matches which Mint event
3. Validating that matched BORROW amounts correspond to Mint event values
4. Adding unit tests for multi-mint transactions

## Related Issues

- Issue 0024: Pure Interest Mint Incorrectly Matches SUPPLY Event
- Issue 0011: Collateral Mint Events Miss LiquidationCall Matching
- Issue 0012: Collateral Operations Consume LIQUIDATION_CALL Events

## Test Case

```python
# Test transaction with multiple debt mints
tx_hash = "0x406c6bff8ec8a76b8b5946d583ca8dabff846e716b5745211dfcc62e9529d0c3"
user = "0x310a2c115d3d45a89b59640FfF859BE0f54a08E2"
token = "0xC96113eED8cAB59cD8A66813bCB0cEb29F06D2e4"
block = 16574551

# Expected: 5 wstETH mints totaling 362.949 wstETH
# Expected scaled balance: 362.884658...
```
