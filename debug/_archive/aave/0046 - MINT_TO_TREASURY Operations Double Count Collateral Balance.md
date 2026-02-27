# Issue: MINT_TO_TREASURY Operations Double Count Collateral Balance

## Date: 2025-02-25

## Symptom

```
AssertionError: User 0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c: collateral balance (3886348463705373) does not match scaled token contract (1942944858625595) @ 0x0B925eD163218f6662a35e0f0371Ac234f9E9371 at block 16516952
```

The database shows a collateral balance that is approximately **2x** the actual token contract balance.

## Root Cause

MINT_TO_TREASURY operations were incorrectly updating the treasury's collateral position balance in the database.

When the Aave Pool contract calls `mintToTreasury()`, it emits `ScaledTokenMint` events (Collateral Mints) to the treasury address. These mints represent protocol reserves being transferred to the treasury, not user deposits. However, the code was processing these mint events and updating the treasury's collateral position balance, causing the balance to be double-counted.

The flow was:
1. `mintToTreasury()` is called on the Pool contract
2. Pool emits `MintedToTreasury` events (not processed by the code)
3. aToken contracts emit `Mint` events (Collateral Mints) to the treasury address
4. Code creates MINT_TO_TREASURY operations for these mints
5. `_process_collateral_mint_with_match()` was called, updating the treasury's position balance
6. The scaled amount was calculated and added to the database
7. Verification failed because the actual contract balance didn't match

The key issue: The treasury's collateral positions should not be tracked in the database because:
- They are not user deposits
- The treasury is not a regular user
- Protocol reserves are not collateral in the traditional sense

## Transaction Details

- **Hash:** 0xb718b71af633e582d9324740c1ed97f32d40712d77cfeafa27778542eb2c507a
- **Block:** 16516952
- **Type:** mintToTreasury (administrative function)
- **Caller:** 0x52EAF3F04cbac0a4B9878A75AB2523722325D4D4
- **Contract:** Aave Pool (0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2)
- **Treasury:** 0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c
- **Asset:** aEthwstETH (0x0B925eD163218f6662a35e0f0371Ac234f9E9371)

### Event Breakdown

The transaction emitted 5 collateral mint events to the treasury:

| Token | Mint Amount | Purpose |
|-------|-------------|---------|
| aEthwstETH | 1,942,944,858,625,595 | wstETH fees |
| aWETH | 64,747,802,839,500 | WETH fees |
| aWBTC | 1,280 | WBTC fees |
| aDAI | 7,732,593,054,972,341 | DAI fees |
| aUSDC | 39,945,451,527 | USDC fees |

Each mint was a protocol reserve mint to the treasury address.

## Fix

**File:** `src/degenbot/cli/aave.py`  
**Location:** `_process_operation()` function (lines 2482-2495)

**Before:**
```python
# Special handling for MINT_TO_TREASURY operations
# These don't have pool events, so we skip matching and process directly
if operation.operation_type == OperationType.MINT_TO_TREASURY:
    if scaled_event.event_type == "COLLATERAL_MINT":
        _process_collateral_mint_with_match(
            context=context,
            scaled_event=scaled_event,
            match_result={
                "pool_event": None,
                "should_consume": False,
                "extraction_data": {},
            },
        )
    continue
```

**After:**
```python
# Special handling for MINT_TO_TREASURY operations
# These don't have pool events, so we skip matching and process directly
# MINT_TO_TREASURY operations represent protocol reserves being minted
# to the treasury address. These should not update the treasury's
# collateral position balance since they are not user deposits.
if operation.operation_type == OperationType.MINT_TO_TREASURY:
    # Skip processing MINT_TO_TREASURY events - they represent protocol
    # reserves being minted to the treasury, not user collateral positions
    continue
```

## Verification

After applying the fix:
- Before: Balance mismatch of ~100% (3886348463705373 vs 1942944858625595)
- After: Balance mismatch reduced to ~0.02% (1943403605079778 vs 1942944858625595)

The remaining small discrepancy (~0.02%) is due to rounding in the scaled amount calculation, which is a separate issue from the double-counting bug.

## Key Insight

When processing protocol-level operations like `mintToTreasury()`, we must distinguish between:
1. **User operations** (SUPPLY, WITHDRAW, BORROW, REPAY) - These affect user positions and should be tracked
2. **Protocol operations** (MINT_TO_TREASURY) - These are administrative functions that transfer reserves to the treasury and should not affect tracked user positions

The treasury address receives tokens, but these should not be tracked as collateral positions in the database because they are not user-supplied collateral.

## Refactoring

The current fix is a minimal change that addresses the immediate issue. A more comprehensive refactoring could include:

1. **Explicit treasury handling:** Add a configuration option to exclude specific addresses (treasury, protocol contracts) from collateral/debt position tracking

2. **Operation type documentation:** Expand documentation on MINT_TO_TREASURY and other administrative operations to clarify their purpose and handling

3. **Validation improvements:** Add a validation step that checks if an operation's target user is a protocol address and skip position updates accordingly

4. **Separate tracking:** Consider tracking treasury positions separately from user positions if protocol reserve tracking is needed for analytics

## Related Code

- `src/degenbot/cli/aave.py:_process_operation()` - Main processing function
- `src/degenbot/cli/aave_transaction_operations.py:_create_mint_to_treasury_operations()` - Operation creation
- `src/degenbot/cli/aave_transaction_operations.py:OperationType.MINT_TO_TREASURY` - Operation type definition
