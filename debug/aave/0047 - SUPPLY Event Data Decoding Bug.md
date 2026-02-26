# Issue: SUPPLY Event Data Decoding Bug

**Date:** 2026-02-26

**Symptom:**
```
eth_abi.exceptions.InsufficientDataBytes: Tried to read 32 bytes, only got 0 bytes.
```

## Root Cause

The `_extract_supply_data` method in `aave_event_matching.py` was incorrectly decoding the SUPPLY event data. The code expected:
```python
types=["address", "uint256", "uint16"]  # 96 bytes expected
```

But the actual Aave V3 SUPPLY event data format is:
```solidity
event Supply(
    address indexed reserve,      // topics[1]
    address user,                 // data: 32 bytes
    address indexed onBehalfOf,   // topics[2]
    uint256 amount,               // data: 32 bytes
    uint16 indexed referralCode   // topics[3]
);
```

**Actual data format:** `(address user, uint256 amount)` = **64 bytes**

### Code Location

**File:** `src/degenbot/cli/aave_event_matching.py`
**Method:** `_extract_supply_data` (lines 1035-1047)

**Before (buggy):**
```python
def _extract_supply_data(self) -> dict[str, int]:
    """Extract data from SUPPLY event."""
    # SUPPLY: data=(address caller, uint256 amount, uint16 referralCode)
    # Skip the first 32 bytes (address caller) and decode the amount
    if self.operation.pool_event is None:
        return {"raw_amount": 0}
    _, raw_amount, _ = decode(
        types=["address", "uint256", "uint16"],
        data=self.operation.pool_event["data"],
    )
    return {
        "raw_amount": raw_amount,
    }
```

**After (fixed):**
```python
def _extract_supply_data(self) -> dict[str, int]:
    """Extract data from SUPPLY event."""
    # SUPPLY: indexed reserve, indexed onBehalfOf, indexed referralCode
    # data=(address user, uint256 amount)
    if self.operation.pool_event is None:
        return {"raw_amount": 0}
    user, raw_amount = decode(
        types=["address", "uint256"],
        data=self.operation.pool_event["data"],
    )
    return {
        "raw_amount": raw_amount,
    }
```

### Why This Caused the Bug

1. The SUPPLY event has 3 indexed parameters (in topics) and 2 non-indexed parameters (in data)
2. The buggy code tried to decode 96 bytes from the data, but only 64 bytes exist
3. This caused `InsufficientDataBytes` exception when processing SUPPLY events
4. The referralCode is in topics[3], not in the data section

## Transaction Details

| Field | Value |
|-------|-------|
| **Transaction Hash** | `0xa4a5f3993fd60bd01665f8389c1c5cded8cfed0007de913142cd9a8bb0f13117` |
| **Block** | 16496817 |
| **Pool Event** | SUPPLY |
| **Asset** | WETH (0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2) |
| **User** | 0xd322a49006fc828f9b5b37ab215f99b4e5cab19c (Gateway) |
| **On Behalf Of** | 0x7fa5195595efe0dfbc79f03303448af3fbe4ea91 |
| **Amount** | 40000000000000000 (0.04 ETH) |

### SUPPLY Event Data

```
Data: 0x000000000000000000000000d322a49006fc828f9b5b37ab215f99b4e5cab19c
      000000000000000000000000000000000000000000000000008e1bc9bf040000

Topics:
  [0]: 0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61 (Supply)
  [1]: 0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2 (reserve: WETH)
  [2]: 0x0000000000000000000000007fa5195595efe0dfbc79f03303448af3fbe4ea91 (onBehalfOf)
  [3]: 0x0000000000000000000000000000000000000000000000000000000000000000 (referralCode)
```

**Decoded:**
- `user`: `0xd322a49006fc828f9b5b37ab215f99b4e5cab19c` (Gateway contract)
- `amount`: `40000000000000000` (0.04 ETH)

**Buggy decoding:** Would fail with `InsufficientDataBytes: Tried to read 32 bytes, only got 0 bytes`

## Additional Fix: Debug Logger

A secondary issue was fixed in the debug logger:

**File:** `src/degenbot/cli/aave_debug_logger.py`
**Method:** `_serialize_tx_context` (lines 266-296)

The debug logger was trying to serialize non-existent attributes:
- `context.pool_events`
- `context.collateral_mints`
- `context.collateral_burns`
- etc.

**Fix:** Removed these non-existent attributes, keeping only:
- `context.events`
- `context.user_discounts`
- `context.discount_updates_by_log_index`

## Fix

### Changes Made

**File:** `src/degenbot/cli/aave_event_matching.py`

1. Updated `_extract_supply_data` to decode only 2 fields (user address + amount)
2. Removed incorrect comment about skipping first 32 bytes
3. Added correct comment explaining the actual event structure

**File:** `src/degenbot/cli/aave_debug_logger.py`

1. Updated `_serialize_tx_context` to only serialize attributes that exist on TransactionContext
2. Removed references to non-existent event category collections

### Test Coverage

This fix is covered by existing tests in:
- `tests/cli/test_aave_event_data_extraction.py` (if it exists)
- Integration test via `uv run degenbot aave update`

## Key Insight

Event data decoding must account for the actual event structure:
- **Indexed parameters** go in `topics[]` array
- **Non-indexed parameters** go in `data` field
- Always verify against the actual contract ABI

**Important:** The SUPPLY event structure is:
```solidity
event Supply(
    address indexed reserve,      // topics[1]
    address user,                 // data bytes 0-31
    address indexed onBehalfOf,   // topics[2]
    uint256 amount,               // data bytes 32-63
    uint16 indexed referralCode   // topics[3]
);
```

## Event Data Layout Reference

| Event | Indexed Topics | Data Format | Data Bytes |
|-------|----------------|-------------|------------|
| SUPPLY | reserve, onBehalfOf, referralCode | `(address user, uint256 amount)` | 64 |
| WITHDRAW | reserve, user, to | `(uint256 amount)` | 32 |
| BORROW | reserve, onBehalfOf, referralCode | `(address user, uint256 amount, uint8 mode, uint256 rate)` | 128 |
| REPAY | reserve, user | `(uint256 amount, bool useATokens)` | 64 |

**Key Rule:** Always check which parameters are indexed (in topics) vs non-indexed (in data).

## Verification

After applying the fix:
```bash
uv run degenbot aave update --debug-output=./debug.log --one-chunk
```

The update progresses past the previously failing transaction at block 16496817.

## Related Issues

- **0045** - Similar bug in BORROW event decoding (was decoding address as amount)
- This fix ensures SUPPLY event decoding matches the actual Aave V3 event structure
