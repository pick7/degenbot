# Issue 0007: GHO Debt Burn Discount Not Applied in Operation-Based Processing

## Issue: GHO Debt Burn Discount Not Applied in Operation-Based Processing

**Date:** 2025-02-27

**Symptom:**
```
AssertionError: User 0x84aC9de807CEFa7205b53108c705744dA523f901: debt balance (1381274738396731) does not match scaled token contract (1170492213317390) @ 0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B at block 17699741
```

**Root Cause:**
The operation-based event processing path (`_process_debt_burn_with_match`) was using the standard debt token processor (`_process_scaled_token_operation`) instead of the GHO-specific processor for GHO debt burn events. The standard processor does not handle GHO-specific logic like the discount mechanism.

When a user has a GHO discount (e.g., 15.26% for holding stkAAVE), the GHO variable debt token contract applies this discount to the interest accrual before burning debt tokens. The standard processor was not aware of this discount and was calculating the burn amount without the discount adjustment, resulting in a balance that was approximately 210,782,525,079,341 wei higher than the actual contract balance.

**Transaction Details:**
- **Hash:** 0x0d0e00b842438e904d1c538a2667dfe2edfdc985ffdf9174abcf4323498b0fb6
- **Block:** 17699741
- **Type:** REPAY (repayWithPermit)
- **User:** 0x84aC9de807CEFa7205b53108c705744dA523f901
- **Asset:** GHO (0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f)
- **Debt Token:** 0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B
- **Implementation:** GhoVariableDebtToken rev 1
- **Amount Repaid:** 5,500 GHO
- **Discount Before:** 15.26% (1526 basis points)
- **Discount After:** 0% (reset during transaction)

**Smart Contract Behavior:**
The GHO Variable Debt Token uses a discount mechanism where users who hold stkAAVE receive a discount on their borrowing interest. The contract calculates the discount in `_accrueDebtOnAction`:

```solidity
function _accrueDebtOnAction(
  address user,
  uint256 previousScaledBalance,
  uint256 discountPercent,
  uint256 index
) internal returns (uint256, uint256) {
  uint256 balanceIncrease = previousScaledBalance.rayMul(index) -
    previousScaledBalance.rayMul(_userState[user].additionalData);

  uint256 discountScaled = 0;
  if (balanceIncrease != 0 && discountPercent != 0) {
    uint256 discount = balanceIncrease.percentMul(discountPercent);
    discountScaled = discount.rayDiv(index);
    balanceIncrease = balanceIncrease - discount;
  }
  // ...
  return (balanceIncrease, discountScaled);
}
```

Then in `_burnScaled`:
```solidity
(uint256 balanceIncrease, uint256 discountScaled) = _accrueDebtOnAction(
  user, previousScaledBalance, discountPercent, index
);

// uint256 amountToBurn = amount - balanceIncrease;
uint256 amountScaled = amountToBurn.rayDiv(index);

// Matches Solidity: _burn(user, (amountScaled + discountScaled).toUint128())
```

**Key Event:**
The `DiscountPercentUpdated` event was emitted during this transaction, resetting the user's discount from 15.26% to 0%. This event is processed BEFORE the burn event, so the database correctly records the new discount. However, the OLD discount (15.26%) must be used for the burn calculation because that's what was in effect when the debt was accrued.

**Fix:**
Modified `_process_debt_burn_with_match` in `src/degenbot/cli/aave.py` to check if the token is GHO and use the GHO-specific processor instead of the standard debt processor.

**Code Location:** `src/degenbot/cli/aave.py`, function `_process_debt_burn_with_match`

**Changes:**
Added GHO-specific processing logic that:
1. Checks if the token is the GHO variable debt token
2. Retrieves the effective discount from transaction context or user record
3. Uses the GHO processor (`GhoV1Processor`) to calculate the balance delta with discount
4. Applies the balance delta and updates the index
5. Refreshes the discount rate if needed

For non-GHO tokens, it continues to use the standard `_process_scaled_token_operation`.

**Key Insight:**
The codebase has two event processing paths:
1. **Legacy path** (`_process_scaled_token_burn_event`): Handles GHO tokens by calling `_process_gho_debt_burn_event` which uses the GHO processor
2. **Operation-based path** (`_process_transaction_with_operations`): Routes events through `_process_debt_burn_with_match` which was NOT using the GHO processor

The operation-based path is enabled by default (`USE_OPERATION_BASED_PROCESSING=true`), so GHO burns were being processed without discount calculation. This explains why the bug only appeared when operation-based processing was enabled.

This is analogous to issue #0005, which fixed the same problem for GHO debt mint events.

**Refactoring:**
Consider consolidating the GHO debt burn processing logic to ensure both the legacy and operation-based paths use the same discount-aware processing. The current fix duplicates some logic from `_process_gho_debt_burn_event` in `_process_debt_burn_with_match`. A better long-term solution would be to:

1. Extract the discount-aware burn calculation into a shared function
2. Ensure all code paths (legacy and operation-based) call this shared function for GHO tokens
3. Add better test coverage for GHO operations in both processing modes

**Test:**
Added `tests/aave/test_gho_debt_burn_discount.py` with 4 test cases:
1. `test_gho_burn_with_discount_calculation`: Verifies correct balance with discount
2. `test_gho_burn_without_discount`: Verifies the bug case (balance too high without discount)
3. `test_discount_accrual_calculation`: Verifies interest accrual math
4. `test_gho_burn_discount_reset_scenario`: Verifies correct handling when discount is reset

**Verification:**
The fix was verified by:
1. Running the update command at the failing block (17699741) - SUCCESS
2. Running all Aave tests (55 tests) - ALL PASS
3. Running the new unit tests (4 tests) - ALL PASS

**Related Issues:**
- Issue #0005: GHO Debt Mint Discount Not Applied in Operation-Based Processing (similar bug for mint operations)
