## Issue: DEBT_MINT Event Matching Fails Due to max_log_index Constraint

**Date:** 2026-02-25

## Symptom

```
AssertionError: User 0x310a2c115d3d45a89b59640FfF859BE0f54a08E2: debt balance (336455331017897785935) does not match scaled token contract (362884658273797549684) @ 0xC96113eED8cAB59cD8A66813bCB0cEb29F06D2e4 at block 16574551
```

## Root Cause

In `_process_standard_debt_mint_event` (src/degenbot/cli/aave.py:4282), the `max_log_index=event["logIndex"]` constraint prevented the EventMatcher from finding BORROW events that occur after the debt mint event in the transaction logs.

In complex transactions with multiple operations (like leveraged yield farming strategies), the event ordering can be interleaved:
1. Pool.SUPPLY (collateral deposit)
2. AToken.Mint (collateral token mint)
3. Pool.BORROW (debt borrow) ← This event can appear AFTER the debt mint
4. VariableDebtToken.Mint (debt token mint)

The `max_log_index` parameter was intended to ensure we only match pool events that precede the token event, but in Aave V3's architecture, the Pool BORROW event and VariableDebtToken Mint event ordering is not strictly guaranteed when multiple operations are batched in a single transaction.

## Transaction Details

- **Hash:** 0x406c6bff8ec8a76b8b5946d583ca8dabff846e716b5745211dfcc62e9529d0c3
- **Block:** 16574551
- **Type:** DSProxy.execute() - Automated leveraged borrowing strategy
- **User:** 0x310a2c115d3d45a89b59640FfF859BE0f54a08E2
- **Asset:** variableDebtEthwstETH (0xC96113eED8cAB59cD8A66813bCB0cEb29F06D2e4)

The transaction performed 5 separate borrow operations, but only 4 were correctly matched due to the `max_log_index` constraint filtering out one BORROW event.

## Fix

**File:** src/degenbot/cli/aave.py
**Location:** Line 4282

**Before:**
```python
result = matcher.find_matching_pool_event(
    event_type=ScaledTokenEventType.DEBT_MINT,
    user_address=user.address,
    reserve_address=reserve_address,
    check_users=[caller_address],
    max_log_index=event["logIndex"],
)
```

**After:**
```python
result = matcher.find_matching_pool_event(
    event_type=ScaledTokenEventType.DEBT_MINT,
    user_address=user.address,
    reserve_address=reserve_address,
    check_users=[caller_address],
    # Don't restrict by max_log_index - BORROW events can appear after Mint events
    # in complex transactions with multiple operations
    max_log_index=None,
)
```

## Key Insight

The assumption that Pool events always precede their corresponding Token events is valid for simple transactions, but breaks down in complex transactions where multiple operations are batched. The EventMatcher already handles event consumption correctly (marking matched BORROW events as consumed), so removing the `max_log_index` constraint is safe and allows proper matching regardless of event ordering.

## Refactoring

The `max_log_index` parameter has been completely removed from the codebase:

**Files Modified:**
1. **src/degenbot/cli/aave_event_matching.py**
   - Removed `max_log_index` parameter from `find_matching_pool_event()` signature
   - Removed filtering logic that skipped events based on log index
   - Updated docstring to explain event matching without temporal constraints

2. **src/degenbot/cli/aave.py**
   - Removed `max_log_index` from all 6 call sites:
     - `_process_collateral_mint_event` (withdrawal branch)
     - `_process_gho_debt_mint_event`
     - `_process_standard_debt_mint_event`
     - `_process_collateral_burn_event`
     - `_process_gho_debt_burn_event`
     - `_process_standard_debt_burn_event`

3. **tests/cli/test_aave_event_matching.py**
   - Removed `max_log_index` parameter from test calls

4. **tests/cli/test_aave_supply_zero_address_matching.py**
   - Removed `max_log_index` parameter from test calls

**Rationale:**
The consumption tracking mechanism (`_is_consumed`, `_mark_consumed`) already prevents events from being matched multiple times, making the `max_log_index` constraint redundant. The constraint was causing bugs in complex transactions where event ordering wasn't strictly sequential. Removing it simplifies the code and allows proper matching regardless of event ordering within a transaction.
