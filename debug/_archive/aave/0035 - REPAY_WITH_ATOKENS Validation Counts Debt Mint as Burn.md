# Issue: REPAY_WITH_ATOKENS Validation Counts Debt Mint as Burn

**Date:** 2025-02-21

## Symptom

```
Transaction validation failed:
Operation 1 (REPAY_WITH_ATOKENS): Expected 1 debt burn for REPAY_WITH_ATOKENS, got 2
```

## Root Cause

The `_validate_repay_with_atokens` method in `aave_transaction_operations.py` used `e.is_debt` to count debt burns. However, the `is_debt` property returns `True` for ANY event type starting with "DEBT" or "GHO", including:
- `DEBT_BURN` ✓ (should be counted)
- `DEBT_MINT` ✗ (should NOT be counted as a burn)
- `GHO_DEBT_BURN` ✓ (should be counted)
- `GHO_DEBT_MINT` ✗ (should NOT be counted as a burn)

When a `repayWithATokens` operation has both a debt burn (principal repayment) and a debt mint (interest accrual), the validator incorrectly counts both as "debt burns", resulting in the validation error.

## Transaction Details

- **Hash:** 0x87c148f1379489e24b38a86aed0b4fab5409c5f8859622aa4899feb51fd497e5
- **Block:** 20233465
- **Type:** Deleveraging transaction with multiple repayWithATokens operations
- **User:** 0x7F6f31e0603a459CC740E8e5a6F79dbb3304354b

### Event Sequence

The transaction contains two `repayWithATokens` operations. The second operation (logIndex 332) triggered the validation failure:

```
Operation 1: REPAY_WITH_ATOKENS
  Pool Event: logIndex=332 (REPAY for USDC)
  Scaled Token Events (3):
    logIndex 328: DEBT_MINT (GHO interest accrual) - counted as "debt burn" (BUG)
    logIndex 338: DEBT_BURN (GHO principal repayment) - correctly counted
    logIndex 348: COLLATERAL_BURN (USDC aToken)
```

The validator counted both logIndex 328 (DEBT_MINT) and logIndex 338 (DEBT_BURN) as "debt burns" because both have `is_debt = True`.

## Fix

**File:** `src/degenbot/cli/aave_transaction_operations.py`

**Change:** Filter for burns specifically using `e.is_burn` in addition to `e.is_debt`:

```python
# Before (line 1002):
debt_burns = [e for e in op.scaled_token_events if e.is_debt]

# After:
debt_burns = [e for e in op.scaled_token_events if e.is_debt and e.is_burn]
```

Also applied the same fix to collateral burn counting:

```python
# Before (line 1003):
collateral_burns = [e for e in op.scaled_token_events if e.is_collateral]

# After:
collateral_burns = [e for e in op.scaled_token_events if e.is_collateral and e.is_burn]
```

## Key Insight

When checking for "burns" in validation, always use both `is_debt`/`is_collateral` AND `is_burn` properties. The `is_debt` and `is_collateral` properties are too broad - they include both mints and burns.

## Refactoring

Consider reviewing other validation methods to ensure they don't have the same issue:
- `_validate_repay` (line ~987)
- `_validate_liquidation` (line ~1036)

These methods also use `e.is_debt` and may need the same fix if they should only count burns.
