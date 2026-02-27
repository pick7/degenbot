# Issue: stkAAVE Transfer Event Not Processed in Operation-Based Path

**Issue ID:** 0006  
**Date:** 2026-02-27  
**Status:** Fixed  

---

## Symptom

```
AssertionError: User 0x360FA2900CB094688f5f9c0CE875df56CB8B0639: stkAAVE balance 0 does not match contract (6000000000000000000) @ 0x4da27a545c0c5B758a6BA100e3a049001de870f5 at block 17699521
```

The Aave update processor failed verification because a user's stkAAVE balance was recorded as 0 in the database, but the on-chain contract showed 6 stkAAVE (6000000000000000000 wei).

---

## Root Cause

The codebase has two event processing paths:
1. **Legacy path** (`_process_transaction_with_context`): Handles events individually in chronological order
2. **Operation-based path** (`_process_transaction_with_operations`): Groups events into logical operations first, then processes them

The stkAAVE Transfer event handler (`_process_stk_aave_transfer_event`) was only registered in the **legacy path** dispatch loop. When `USE_OPERATION_BASED_PROCESSING` is enabled (which is the default), the operation-based path is used, and this path did **not** have a handler for stkAAVE Transfer events.

The missing handler was in `_process_transaction_with_operations` at lines 2611-2623, where non-operation events are dispatched. The dispatch code only handled:
- `RESERVE_DATA_UPDATED`
- `USER_E_MODE_SET`
- `UPGRADED`
- `DISCOUNT_PERCENT_UPDATED`
- `DISCOUNT_TOKEN_UPDATED`
- `DISCOUNT_RATE_STRATEGY_UPDATED`

But it did **not** handle `ERC20_TRANSFER` events on the stkAAVE contract address.

---

## Transaction Details

- **Transaction Hash:** `0x9fe48a0a6454cc7a83b1ac4d3fc412f40792e2359709db4c1959170052a1d5a5`
- **Block:** 17699521
- **Type:** Stake operation (AAVE → stkAAVE)
- **User:** `0x360FA2900CB094688f5f9c0CE875df56CB8B0639`
- **Asset:** stkAAVE (6 tokens)
- **Contract:** `0x4da27a545c0c5B758a6BA100e3a049001de870f5`

**Events in Transaction:**
1. `DISCOUNT_PERCENT_UPDATED` - GHO discount percent changed
2. `ERC20_TRANSFER` - AAVE transferred from user to stkAAVE contract (6 AAVE)
3. `ScaledTokenMint` - GHO minted (~0.00035 GHO)
4. `ERC20_TRANSFER` - GHO transferred
5. `STAKED` - Semantic staking event
6. **`ERC20_TRANSFER`** - **stkAAVE minted to user (6 stkAAVE) - THIS WAS NOT PROCESSED**

---

## Fix

**File:** `src/degenbot/cli/aave.py`

**Change:** Added stkAAVE Transfer event handler to the operation-based processing path.

```python
# In _process_transaction_with_operations(), after line 2623:

        # Dispatch to appropriate handler for non-operation events
        if topic == AaveV3Event.RESERVE_DATA_UPDATED.value:
            _process_reserve_data_update_event(context)
        elif topic == AaveV3Event.USER_E_MODE_SET.value:
            _process_user_e_mode_set_event(context)
        elif topic == AaveV3Event.UPGRADED.value:
            _process_scaled_token_upgrade_event(context)
        elif topic == AaveV3Event.DISCOUNT_PERCENT_UPDATED.value:
            _process_discount_percent_updated_event(context)
        elif topic == AaveV3Event.DISCOUNT_TOKEN_UPDATED.value:
            _process_discount_token_updated_event(context)
        elif topic == AaveV3Event.DISCOUNT_RATE_STRATEGY_UPDATED.value:
            _process_discount_rate_strategy_updated_event(context)
        elif topic == AaveV3Event.ERC20_TRANSFER.value and event_address == (
            gho_asset.v_gho_discount_token if gho_asset else None
        ):
            _process_stk_aave_transfer_event(context)
```

**Lines Changed:** Added at line 2624 in `_process_transaction_with_operations()`

---

## Key Insight

When migrating from legacy event processing to operation-based processing, **all event handlers** must be duplicated or moved to the new path. The `_process_transaction_with_context` function (legacy path) had the stkAAVE Transfer handler, but `_process_transaction_with_operations` (operation-based path) did not.

This highlights the importance of:
1. Comprehensive test coverage for both processing paths
2. Code review checklists for event handler registration
3. Feature flags that allow quick rollback when issues are discovered

---

## Refactoring

**Proposed Improvements:**

1. **Unified Event Dispatch:** Create a single dispatch table/registry that both processing paths use, ensuring handlers are registered once and work in both paths.

2. **Handler Registration Decorator:** Use a decorator pattern to automatically register handlers:
   ```python
   @event_handler(AaveV3Event.ERC20_TRANSFER)
   def _process_stk_aave_transfer_event(context: EventHandlerContext) -> None:
       ...
   ```

3. **Validation:** Add a validation step that checks all `AaveV3Event` enum values have corresponding handlers registered.

4. **Documentation:** Document which events are handled in which paths and why certain events are classified as "operations" vs "non-operation events".

---

## Verification

- [x] Fix applied to `src/degenbot/cli/aave.py`
- [x] Update command runs successfully to block 17699525
- [x] All 192 existing Aave tests pass
- [x] User's stkAAVE balance correctly recorded as 6000000000000000000

---

## Related

- **Issue 0005:** GHO Debt Mint Discount Not Applied in Operation-Based Processing
- **Contract Reference:** `contract_reference/aave/StakedAaveV3.sol`
