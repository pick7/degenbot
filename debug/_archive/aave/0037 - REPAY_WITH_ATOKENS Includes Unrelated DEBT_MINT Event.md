# Issue: REPAY_WITH_ATOKENS Includes Unrelated DEBT_MINT Event

**Date:** 2026-02-22

## Symptom

```
Transaction validation failed:
Operation 1 (REPAY_WITH_ATOKENS): Expected 1 debt event for REPAY_WITH_ATOKENS, got 2
```

## Root Cause

In `_create_repay_operation` method in `aave_transaction_operations.py`, when `use_a_tokens=True`, the code was incorrectly including `DEBT_MINT` events in the `REPAY_WITH_ATOKENS` operation along with `DEBT_BURN` and `COLLATERAL_BURN` events.

The issue is that `DEBT_MINT` events represent interest accrual or borrow operations, not repayments. In the failing transaction, the `DEBT_MINT` at logIndex 328 was GHO interest accrual for a different asset (VUSDC), while the `REPAY` at logIndex 332 was for USDC repayment. These are unrelated operations that were incorrectly grouped together.

The validation in `_validate_repay_with_atokens` correctly expects exactly 1 debt event per `REPAY_WITH_ATOKENS` operation (either a burn or mint, but not both), but the operation creation logic was including both.

## Transaction Details

- **Hash:** 0x87c148f1379489e24b38a86aed0b4fab5409c5f8859622aa4899feb51fd497e5
- **Block:** 20233465
- **Type:** Deleveraging transaction with multiple repayWithATokens operations
- **User:** 0x7F6f31e0603a459CC740E8e5a6F79dbb3304354b

### Event Sequence

```
Operation 0: REPAY_WITH_ATOKENS (WETH)
  Pool Event: logIndex=325 (REPAY for WETH)
  Scaled Token Events (2):
    logIndex 321: DEBT_BURN (VWETH - debt repayment) ✓
    logIndex 331: COLLATERAL_BURN (AUSDC - collateral burn) ✓
  Status: OK Valid

Operation 1: REPAY_WITH_ATOKENS (USDC) - FAILED VALIDATION
  Pool Event: logIndex=332 (REPAY for USDC)
  Scaled Token Events (3):
    logIndex 328: DEBT_MINT (VUSDC - GHO interest accrual) ✗ (incorrectly included)
    logIndex 338: DEBT_BURN (VUSDC - debt repayment) ✓
    logIndex 348: COLLATERAL_BURN (AWETH - collateral burn) ✓
  Status: INVALID - Expected 1 debt event, got 2
```

The `DEBT_MINT` at logIndex 328 was incorrectly matched to Operation 1 even though:
1. It occurs BEFORE the REPAY event at logIndex 332 (chronologically impossible for a repayment)
2. It represents interest accrual on a different operation, not part of the repayWithATokens flow

## Fix

**File:** `src/degenbot/cli/aave_transaction_operations.py`

**Location:** `_create_repay_operation` method (lines 759-779)

**Change:** Remove the code that includes `debt_mint` in the `REPAY_WITH_ATOKENS` operation:

```python
# Before:
if collateral_burn:
    scaled_token_events.append(collateral_burn)
    # For repayWithATokens, also include debt mint if present (interest > repayment case)
    if debt_mint:
        scaled_token_events.append(debt_mint)
    op_type = OperationType.REPAY_WITH_ATOKENS

# After:
if collateral_burn:
    scaled_token_events.append(collateral_burn)
    # Note: We intentionally do NOT include debt_mint here.
    # The debt_mint is for interest accrual and should be a separate
    # operation or handled as unassigned, not grouped with this
    # repayWithATokens operation which should only have 1 debt event.
    op_type = OperationType.REPAY_WITH_ATOKENS
```

## Key Insight

When parsing `repayWithATokens` operations:
- The operation should only include: 1 DEBT_BURN + 1 COLLATERAL_BURN
- Or in edge cases: 1 DEBT_MINT (when interest exceeds repayment) + 1 COLLATERAL_BURN
- But NEVER: 1 DEBT_BURN + 1 DEBT_MINT + 1 COLLATERAL_BURN

The debt mint found while searching for collateral burns is likely from a different context (e.g., interest accrual on a different asset) and should not be included in this operation.

## Refactoring

1. Consider reviewing the event matching logic to ensure `DEBT_MINT` events are properly matched to their corresponding pool events before being considered for inclusion in operations.

2. The `_create_repay_operation` method should only include the `debt_burn` it found earlier, not any `debt_mint` that happens to be in the scaled events list.

3. Add unit test for this specific case: multi-operation transaction where one operation's debt mint could be incorrectly matched to another operation.

## Validation

After fix applied:
```bash
$ uv run degenbot aave update --no-progress-bar --one-chunk --chunk 1
Updating market 1: chain 1, block range 20,233,465 - 20,233,465
Update successful
```

## Related Issues

- **0035** - REPAY_WITH_ATOKENS Validation Counts Debt Mint as Burn (similar but different issue)
- **0036** - REPAY_WITH_ATOKENS Validation Regression for Interest Exceeding Repayment (interest-only repayment case)
