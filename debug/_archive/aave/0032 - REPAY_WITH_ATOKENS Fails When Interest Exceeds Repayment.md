# Issue: REPAY_WITH_ATOKENS Validation Fails When Interest Exceeds Repayment

## Date: 2026-02-21

## Symptom
```
Transaction validation failed:
Operation 0 (REPAY_WITH_ATOKENS): Expected 1 debt burn for REPAY_WITH_ATOKENS, got 0
```

## Root Cause
Aave V3's scaled balance token architecture can emit **DEBT_MINT** events instead of **DEBT_BURN** events during `repayWithATokens` operations when accrued interest exceeds the repayment amount.

In the `_burnScaled` function of Aave's VariableDebtToken:
```solidity
if (nextBalance > previousBalance) {
    // Balance INCREASED - emit Mint events (interest > repayment)
    emit Mint(...);
} else {
    // Balance DECREASED - emit Burn events
    emit Burn(...);
}
```

The code in `_create_repay_operation` only searched for `DEBT_BURN` events, causing it to miss `DEBT_MINT` events in this edge case.

## Transaction Details
- **Hash:** 0x3482a0ec0f3c09935b365130e3a48eaae3850dc9898d13887f8c3ce555a6407b
- **Block:** 18894861
- **Type:** REPAY_WITH_ATOKENS
- **User:** 0x6FfFE084F6413FA400bdB93b951e71e190d5D18a
- **Asset:** USDC (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48)
- **Repayment:** ~1,906 USDC
- **Interest Accrued:** ~2,978 USDC
- **Net Result:** Debt **increased** by ~1,072 USDC

## Events in Transaction
| logIndex | Contract | Event | Amount | Notes |
|----------|----------|-------|--------|-------|
| 447 | VariableDebtUSDC | Mint | +2,978.27 | Interest accrual |
| 448 | VariableDebtUSDC | Mint | +2,978.27 | Duplicate (index change) |
| 449 | Pool | ReserveDataUpdated | - | Reserve update |
| 450 | AUSDC | Transfer (Burn) | -1,905.75 | Collateral burn |
| 451 | AUSDC | Burn | -1,905.75 | Collateral burn |
| 452 | Pool | Repay | 1,919.97 | Pool repay event |

## Fix
**File:** `src/degenbot/cli/aave_transaction_operations.py`

**Location:** `_create_repay_operation` method (lines 687-700)

**Change:** Modified debt event detection to accept both `DEBT_BURN` and `DEBT_MINT` events:

```python
# Before: Only looked for DEBT_BURN
debt_burn = None
for ev in scaled_events:
    if ev.event["logIndex"] in assigned_indices:
        continue
    if (is_gho and ev.event_type == "GHO_DEBT_BURN") or (
        not is_gho and ev.event_type == "DEBT_BURN"
    ):
        if ev.user_address == user:
            debt_burn = ev
            break

scaled_token_events = [debt_burn] if debt_burn else []

# After: Accepts both BURN and MINT events
debt_event = None
for ev in scaled_events:
    if ev.event["logIndex"] in assigned_indices:
        continue
    if is_gho:
        if ev.event_type in ("GHO_DEBT_BURN", "GHO_DEBT_MINT"):
            if ev.user_address == user:
                debt_event = ev
                break
    else:
        if ev.event_type in ("DEBT_BURN", "DEBT_MINT"):
            if ev.user_address == user:
                debt_event = ev
                break

scaled_token_events = [debt_event] if debt_event else []
```

## Key Insight
Aave's scaled token architecture means debt balance changes can be **non-monotonic** during repayments:
- **Normal case:** Repayment > Interest → Debt decreases → BURN event
- **Edge case:** Interest > Repayment → Debt increases → MINT event

This is not a bug in Aave, but rather a documented edge case that transaction processors must handle. The validation logic in `_validate_repay_with_atokens` already correctly accepted any debt event (via `is_debt` property), but the operation creation logic was too restrictive.

## Refactoring
1. Consider extracting the debt event detection logic into a shared helper method to ensure consistency between `_create_repay_operation` and `_create_borrow_operation`
2. Add explicit test cases for edge cases where interest exceeds repayment
3. Document the interest-accrual-during-repayment behavior in the code comments

## Related Issues
- Similar logic already exists for GHO in `_validate_gho_repay` (lines 950-954)
- The `is_debt` property in `ScaledTokenEvent` already correctly identifies both BURN and MINT as debt events

## Validation
After fix applied:
```bash
$ uv run degenbot aave update --no-progress-bar --one-chunk --chunk 1
Updating market 1: chain 1, block range 18,894,861 - 18,894,861
Update successful
```
