# Issue 0008: Stale Debt Index from Burn/Mint Events

**Date:** 2026-02-27

## Symptom

```
AssertionError: User 0x0fd3E4B5FcaC38ba6E48e9c7703805679eDFCcC4: debt last_index (1000919640646688461729030319) does not match contract (1000919954862378321350351390) @ 0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B at block 17859071
```

## Root Cause

The Aave V3 smart contract emits `Burn` and `Mint` events with a **stale index value** - specifically, the user's cached `lastIndex` at the time of the operation, not the current global borrow index.

### Event Order Problem

In a typical repay transaction, events are emitted in this order:
1. `Discount` (GHO discount event)
2. `Transfer` (GHO token transfer)
3. **`Burn`** (debt token burn) ← Contains stale index
4. **`ReserveDataUpdated`** ← Contains current global index
5. Other events...

The `Burn` event (log index 2) contains the user's cached index from their last interaction, but the `ReserveDataUpdated` event (log index 3) contains the actual current global index that should be used.

### Technical Details

When decoding the Burn event from the repay transaction at block 17859016:

```
Burn event values:
  value: 4000000000000000000000 (4000 GHO)
  balanceIncrease: 431506882462117 (interest accrued)
  index: 1000919640646688461729030319 ← STALE INDEX

Expected current global index: 1000919954862378321350351390
```

The contract's internal state is correct (verified via `getPreviousIndex()`), but the event data is stale.

## Transaction Details

**Failing Block:** 17859071
**Failing User:** 0x0fd3E4B5FcaC38ba6E48e9c7703805679eDFCcC4
**Debt Token:** 0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B (GHO VariableDebtToken)

**Sequence of Events:**
1. **Block 17858989:** User borrows 4000 GHO (index: 1000919486395385900994413978)
2. **Block 17859016:** User repays GHO (Burn event has stale index: 1000919640646688461729030319)
3. **Block 17859071:** User transfers stkAAVE, triggering `updateDiscountDistribution()` which validates debt position and detects the stale index

## Fix

### Solution Overview

The fix is to **always fetch the current global index from the Aave Pool contract** when processing debt Burn/Mint events, rather than using either:
1. The stale index from the event (user's cached lastIndex)
2. The cached borrow_index from the asset (may be from a previous block)

### Why Always Fetch?

The asset's cached `borrow_index` field is updated by `ReserveDataUpdated` events, but:
- On a fresh sync, the first transactions for an asset may not have a `ReserveDataUpdated` event
- Even when `ReserveDataUpdated` has been processed, the cached value is from a specific block and may be stale for the current transaction
- The only way to get the correct current global index is to query the contract at the specific block being processed

### Code Changes

**File:** `src/degenbot/cli/aave.py`

1. **Added helper function** `_get_current_borrow_index_from_pool` (around line 1815):
   - Fetches the current borrow index from the Pool contract via `getReserveNormalizedVariableDebt()`
   - Returns None if the call fails

2. **Modified event processing order** (around line 2437):
   - Added two-pass event processing in legacy path
   - First pass: Process all `ReserveDataUpdated` events
   - Second pass: Process all other events

3. **Updated all debt processing functions** to always fetch current index:
   - `_process_debt_burn_with_match`
   - `_process_debt_mint_with_match`  
   - `_process_gho_debt_mint_event`
   - `_process_gho_debt_burn_event`

   ```python
   # Always fetch the current global index from the contract.
   # The asset's cached borrow_index may be stale (from a previous block).
   # The event's index is the user's cached lastIndex, not the current global index.
   pool_contract = _get_contract(market=context.market, contract_name="POOL")
   fetched_index = _get_current_borrow_index_from_pool(
       w3=context.w3,
       pool_address=get_checksum_address(pool_contract.address),
       underlying_asset_address=get_checksum_address(debt_asset.underlying_token.address),
       block_number=scaled_event.event["blockNumber"],
   )
   # Use fetched index if available, otherwise fall back to event index
   current_index = fetched_index if fetched_index is not None else scaled_event.index
   debt_position.last_index = current_index
   ```

## Key Insight

**The Aave smart contract emits Burn/Mint events with the user's cached `lastIndex`, not the current global index.** This means:
- The event's `index` parameter shows what the user's index WAS before the operation
- After the operation, the contract updates the user's `lastIndex` to the current global index
- But the event doesn't include the current global index!

**The only reliable way to get the current global index is to query the Pool contract directly** via `getReserveNormalizedVariableDebt()` at the specific block being processed.

**Why not use the cached `borrow_index` from the asset?**
The asset's `borrow_index` field is updated by `ReserveDataUpdated` events, but these events are specific to blocks. If a user borrows in block N, but the last `ReserveDataUpdated` for that asset was in block N-1, the cached `borrow_index` will be stale.

This issue affects:
- All debt burn/mint operations (both GHO and non-GHO tokens)
- Both fresh syncs and continued syncs
- Any time the global borrow index has changed since the last `ReserveDataUpdated` event

## Refactoring Recommendations

1. **Index Source Validation** - Add assertions to verify that the index being used is >= the previous index, catching stale index usage during development.

2. **Event Processing Pipeline** - Consider restructuring the event processing to always process state-updating events (ReserveDataUpdated) before dependent events (Burn/Mint).

3. **Documentation** - Add explicit comments in the code warning about stale index values in Burn/Mint events.

4. **Testing** - Create unit tests that simulate transactions with stale index values to ensure the fix continues to work.

## References

- Transaction investigation report: `/tmp/0008-transaction-investigation.md`
- Aave V3 VariableDebtToken contract: `0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B`
- Related issues: This is a new category of issue - stale event data from smart contracts.
