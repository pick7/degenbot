# Issue: BORROW Event Data Decoding Bug - User Address Stored as Debt Balance

**Date:** 2026-02-25

**Symptom:**
```
AssertionError: User 0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91: debt balance 
(728723657782835145989002569680229537482291866257) does not match scaled token 
contract (1000000000000000000) @ 0xcF8d0c70c850859266f5C338b38F9D663181C314 at block 16496939
```

## Root Cause

The `_extract_borrow_data` method in `aave_event_matching.py` was incorrectly decoding the BORROW event data. The BORROW event data format is:
```
(address caller, uint256 amount, uint8 interestRateMode, uint256 borrowRate, uint16 referralCode)
```

But the code was decoding only `["uint256"]` from the beginning of the data, which decoded the **address** field (padded to 32 bytes) as a uint256 instead of the actual amount field.

### Code Location

**File:** `src/degenbot/cli/aave_event_matching.py`  
**Method:** `_extract_borrow_data` (lines 1061-1072)

**Before (buggy):**
```python
def _extract_borrow_data(self) -> dict[str, int]:
    """Extract data from BORROW event."""
    # BORROW: data=(address caller, uint256 amount, ...)
    if self.operation.pool_event is None:
        return {"raw_amount": 0}
    raw_amount = decode(
        types=["uint256"],
        data=self.operation.pool_event["data"],  # Decodes first 32 bytes (address!)
    )[0]
    return {"raw_amount": raw_amount}
```

**After (fixed):**
```python
def _extract_borrow_data(self) -> dict[str, int]:
    """Extract data from BORROW event."""
    # BORROW: data=(address caller, uint256 amount, uint8 interestRateMode, uint256 borrowRate, uint16 referralCode)
    # Skip the first 32 bytes (address caller) and decode the amount
    if self.operation.pool_event is None:
        return {"raw_amount": 0}
    raw_amount = decode(
        types=["uint256"],
        data=self.operation.pool_event["data"][32:],  # Skip first 32 bytes (address)
    )[0]
    return {"raw_amount": raw_amount}
```

### Why This Caused the Bug

1. The BORROW event data layout is:
   - Bytes 0-31: `address caller` (padded to 32 bytes)
   - Bytes 32-63: `uint256 amount`
   - Bytes 64-95: `uint8 interestRateMode` (padded)
   - etc.

2. The buggy code decoded `["uint256"]` starting at byte 0, which decoded the caller address as a uint256

3. The caller address `0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91` as a uint256 is `728723657782835145989002569680229537482291866257`

4. This value was used as `raw_amount` to calculate `scaled_amount`, which was then stored as the user's debt balance

## Transaction Details

| Field | Value |
|-------|-------|
| **Transaction Hash** | `0xa7b2a6f0161a0f7003261a8a05bcea5cc476ce30a446ab1b98b155197c9f739e` |
| **Block** | 16496939 |
| **User** | `0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91` |
| **Operation** | BORROW (1 DAI) |
| **Token** | VariableDebtDAI (Revision 5) |
| **Contract** | `0xcF8d0c70c850859266f5C338b38F9D663181C314` |

### BORROW Event Data

```
Data: 0x0000000000000000000000007fa5195595efe0dfbc79f03303448af3fbe4ea91
      0000000000000000000000000000000000000000000000000de0b6b3a7640000
      0000000000000000000000000000000000000000000000000000000000000002
      000000000000000000000000000000000000000001a190d52882f539e2ded8a
```

**Decoded:**
- `caller`: `0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91` (user address)
- `amount`: `1000000000000000000` (1 DAI) ✓
- `interestRateMode`: `2` (Variable)
- `borrowRate`: `22444632134052383655225162`

**Buggy decoding:** `728723657782835145989002569680229537482291866257` (user address as int) ✗

## Additional Bug Found: SUPPLY Event

During investigation, the same bug was found in `_extract_supply_data`:

**SUPPLY event data:** `(address caller, uint256 amount, uint16 referralCode)`

The code was decoding from byte 0 instead of skipping the caller address.

**Before (buggy):**
```python
def _extract_supply_data(self) -> dict[str, int]:
    """Extract data from SUPPLY event."""
    # SUPPLY: data=(address caller, uint256 amount, uint16 referralCode)
    if self.operation.pool_event is None:
        return {"raw_amount": 0}
    raw_amount = decode(
        types=["uint256"],
        data=self.operation.pool_event["data"],  # Bug: decodes caller address!
    )[0]
    return {"raw_amount": raw_amount}
```

**After (fixed):**
```python
def _extract_supply_data(self) -> dict[str, int]:
    """Extract data from SUPPLY event."""
    # SUPPLY: data=(address caller, uint256 amount, uint16 referralCode)
    # Skip the first 32 bytes (address caller) and decode the amount
    if self.operation.pool_event is None:
        return {"raw_amount": 0}
    raw_amount = decode(
        types=["uint256"],
        data=self.operation.pool_event["data"][32:],  # Skip first 32 bytes (address)
    )[0]
    return {"raw_amount": raw_amount}
```

## Fix

### Changes Made

**File:** `src/degenbot/cli/aave_event_matching.py`

1. Updated `_extract_supply_data` to skip the first 32 bytes (address caller)
2. Updated `_extract_borrow_data` to skip the first 32 bytes (address caller)

**Also fixed:** `src/degenbot/cli/aave.py`

Added `scaled_delta` parameter to all processor calls in `_process_scaled_token_operation` to ensure pre-calculated scaled amounts are used when available.

### Test Coverage

Created test files:

1. **`tests/cli/test_aave_scaled_amount_passing.py`** - Tests that processors correctly use `scaled_amount` when provided

2. **`tests/cli/test_aave_event_data_extraction.py`** - Tests ALL event data extraction functions:
   - `_extract_supply_data` - Tests that caller address is skipped
   - `_extract_withdraw_data` - Tests direct decoding (no address prefix)
   - `_extract_borrow_data` - Tests that caller address is skipped
   - `_extract_repay_data` - Tests direct decoding (no address prefix)
   - `_extract_liquidation_data` - Tests direct decoding (no address prefix)
   - `_extract_deficit_data` - Tests direct decoding (no address prefix)
   - Edge case tests to ensure amounts are not accidentally decoded as addresses

## Key Insight

Event data decoding must account for the actual event structure. The BORROW event includes an `address caller` field in the data (not in topics), which must be skipped to reach the `uint256 amount` field.

**Important:** Solidity event data encoding:
- Indexed parameters go in `topics[]`
- Non-indexed parameters go in `data`
- Dynamic types are encoded specially
- All fields are padded to 32-byte boundaries

Always verify event data layout against contract ABI before decoding.

## Refactoring

### Recommendation: Event Data Decoding Helper

Create a helper function for extracting event data that accounts for the full event structure:

```python
def extract_event_amount(pool_event: LogReceipt, skip_bytes: int = 0) -> int:
    """Extract amount from event data, optionally skipping prefix bytes.
    
    Args:
        pool_event: The pool event LogReceipt
        skip_bytes: Number of bytes to skip before decoding (e.g., 32 for address)
    
    Returns:
        The decoded uint256 amount
    """
    return decode(["uint256"], pool_event["data"][skip_bytes:])[0]


# Usage:
# SUPPLY/BORROW: extract_event_amount(pool_event, skip_bytes=32)  # Skip caller address
# WITHDRAW/REPAY: extract_event_amount(pool_event, skip_bytes=0)   # No prefix
```

**Event Data Layout Reference:**

| Event | Data Format | Skip Bytes |
|-------|-------------|------------|
| SUPPLY | `(address caller, uint256 amount, uint16 referralCode)` | 32 |
| WITHDRAW | `(uint256 amount)` | 0 |
| BORROW | `(address caller, uint256 amount, uint8 interestRateMode, uint256 borrowRate, uint16 referralCode)` | 32 |
| REPAY | `(uint256 amount, bool useATokens)` | 0 |
| LIQUIDATION_CALL | `(uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)` | 0 |
| DEFICIT_CREATED | `(uint256 amountCreated)` | 0 |

**Key Rule:** Events that include `msg.sender` or `caller` in their data (not in topics) require skipping 32 bytes.

## Verification

After applying the fix:
```bash
uv run degenbot aave update --to-block=16496940
```

The update completes successfully, and the user's debt balance is correctly recorded as `1000000000000000000` (1 DAI scaled).

## Related Issues

This bug also prompted fixes for:
1. **0045** - `scaled_amount` not passed to processors (ensures pre-calculated amounts are used)
2. Added `scaled_delta` parameter to all scaled token event processing

Both fixes were necessary for correct balance tracking.
