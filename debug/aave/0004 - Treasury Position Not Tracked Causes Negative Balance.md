# Issue: Treasury Position Not Tracked Causes Negative Balance

**Date:** 2025-02-27

**Symptom:**
```
AssertionError: User 0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c: collateral balance (-94613241909783456751) does not match scaled token contract (196874479847795043325) @ 0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8 at block 17663526
```

**Root Cause:**
The Aave Treasury Collector (0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c) was explicitly excluded from position tracking in multiple places:

1. **MINT_TO_TREASURY operations were skipped** - When the Pool contract minted aTokens to the treasury via `mintToTreasury()`, these events were not updating the treasury's position

2. **Treasury transfers were skipped** - When the treasury was the recipient of aTokens (e.g., liquidation fees), the position update was skipped

3. **Position initialization assumed 0 balance** - When the treasury position was first created, it was initialized with balance=0 instead of the actual on-chain balance

This caused a discrepancy where:
- On-chain balance at block 17663525: ~294 tokens
- Database balance after processing block 17663526: -94.6 tokens
- The treasury had sent ~95 tokens but the database thought it had 0

**Transaction Details:**
- **Hash:** 0x77bb0557d1d96838beb61fc945a06d976c179e898a70b48d21f0adfd15008687
- **Block:** 17663526
- **Type:** MINT_TO_TREASURY + Transfer
- **User:** 0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c (Aave Treasury Collector V2)
- **Asset:** aEthWETH (0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8)
- **Token Revision:** 4

**Fix:**
Removed all special handling that excluded the treasury from tracking:

1. **Modified `_get_or_create_collateral_position`** in `src/degenbot/cli/aave.py`:
   - Now fetches on-chain balance via `scaledBalanceOf()` when creating new positions
   - Also fetches `getPreviousIndex()` for proper interest accrual tracking
   - Initializes position with actual on-chain state

2. **Removed treasury exclusion from `_process_scaled_token_balance_transfer_event`**:
   - Deleted code that skipped transfers to/from treasury address

3. **Removed treasury exclusion from `_process_collateral_transfer_with_match`**:
   - Deleted special cases for liquidation fee transfers to treasury
   - Treasury now receives position updates like any other user

4. **Enabled MINT_TO_TREASURY processing** in `_process_operation`:
   - Removed the `continue` statement that skipped these operations
   - Added handling for MINT_TO_TREASURY without pool event matches

```python
# Before: Treasury events were skipped
if operation.operation_type == OperationType.MINT_TO_TREASURY:
    continue  # Skip processing

# After: Treasury events are processed
if match_result is None and operation.operation_type == OperationType.MINT_TO_TREASURY:
    # Process without pool event match
    _process_collateral_mint_with_match(...)
```

**Key Insight:**
The treasury is a regular contract address that holds aToken positions like any other user. While it collects protocol fees rather than user deposits, it still needs accurate balance tracking for:
- Protocol accounting and analytics
- Accurate total supply calculations
- Preventing downstream issues when other contracts interact with treasury positions

The original exclusion was likely a premature optimization that didn't account for the complexity of Aave's position tracking.

**Refactoring:**
1. Consider removing all hardcoded addresses from the codebase and using configuration
2. Add a "system addresses" registry that can be configured per-market
3. Document the rationale for any address-specific special handling
4. Add integration tests that verify treasury positions are tracked correctly across multiple blocks

**Files Modified:**
- `src/degenbot/cli/aave.py`:
  - `_get_or_create_collateral_position` (lines ~1639-1710)
  - `_process_collateral_transfer_with_match` (lines ~3150-3245)
  - `_process_scaled_token_balance_transfer_event` (lines ~5362-5480)
  - `_process_operation` (lines ~2680-2720)

**Tests Added:**
- `tests/cli/test_aave_treasury_position_tracking.py` - Unit tests for treasury position math and initialization
