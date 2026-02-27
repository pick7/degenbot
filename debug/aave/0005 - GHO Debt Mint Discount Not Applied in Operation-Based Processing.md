# Issue 0005: GHO Debt Mint Discount Not Applied in Operation-Based Processing

## Issue: GHO Debt Mint Discount Not Applied in Operation-Based Processing

**Date:** 2025-02-27

**Symptom:**
```
AssertionError: User 0x28B723a068e99520580bbfbe871cB5F56a658dB4: debt balance (3009999811358453450527) does not match scaled token contract (3009999811255713729216) @ 0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B at block 17699264
```

**Root Cause:**
The operation-based event processing path (`_process_debt_mint_with_match`) was using the standard debt token processor (`_process_scaled_token_operation`) instead of the GHO-specific processor for GHO debt mint events. The standard processor does not handle GHO-specific logic like the discount mechanism.

When a user has a GHO discount (e.g., 30% for holding stkAAVE), the GHO variable debt token contract applies this discount to the interest accrual, reducing the amount of debt that gets minted. The standard processor was not aware of this discount and was calculating the full mint amount, resulting in a balance that was exactly `discount_scaled` (102739721311) higher than the actual contract balance.

**Transaction Details:**
- **Hash:** 0xf514f3d041e74f25909bb31c5bb2c7b58b4f329f3485a3a054f648293d87579e
- **Block:** 17699264
- **Type:** BORROW
- **User:** 0x28B723a068e99520580bbfbe871cB5F56a658dB4
- **Asset:** GHO (0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f)
- **Debt Token:** 0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B
- **Implementation:** 0xc4bea6ff17879e27f266909397e5e0ad3d301946 (GhoVariableDebtToken rev 1)

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

Then in `_mintScaled`:
```solidity
(uint256 balanceIncrease, uint256 discountScaled) = _accrueDebtOnAction(
  onBehalfOf, previousScaledBalance, discountPercent, index
);

if (amountScaled > discountScaled) {
  _mint(onBehalfOf, (amountScaled - discountScaled).toUint128());
}
```

**Fix:**
Modified `_process_debt_mint_with_match` in `src/degenbot/cli/aave.py` to check if the token is GHO and use the GHO-specific processor instead of the standard debt processor.

**Code Location:** `src/degenbot/cli/aave.py`, function `_process_debt_mint_with_match`

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
1. **Legacy path** (`_process_scaled_token_mint_event`): Handles GHO tokens by calling `_process_gho_debt_mint_event` which uses the GHO processor
2. **Operation-based path** (`_process_transaction_with_operations`): Routes events through `_process_debt_mint_with_match` which was NOT using the GHO processor

The operation-based path is enabled by default (`USE_OPERATION_BASED_PROCESSING=true`), so GHO mints were being processed without discount calculation. This explains why the bug only appeared when operation-based processing was enabled.

**Refactoring:**
Consider consolidating the GHO debt mint processing logic to ensure both the legacy and operation-based paths use the same discount-aware processing. The current fix duplicates some logic from `_process_gho_debt_mint_event` in `_process_debt_mint_with_match`. A better long-term solution would be to:

1. Extract the discount-aware mint calculation into a shared function
2. Ensure all code paths (legacy and operation-based) call this shared function for GHO tokens
3. Add better test coverage for GHO operations in both processing modes

**Test:**
Added `tests/aave/test_gho_debt_mint_discount.py` with 4 test cases:
1. `test_gho_borrow_with_discount_calculation`: Verifies correct balance with discount
2. `test_gho_borrow_without_discount`: Verifies the bug case (balance too high without discount)
3. `test_balance_increase_calculation`: Verifies interest accrual math
4. `test_discount_calculation`: Verifies discount amount calculation

**Verification:**
The fix was verified by:
1. Running the update command at the failing block (17699264) - SUCCESS
2. Running all Aave tests (51 tests) - ALL PASS
3. Running the new unit tests (4 tests) - ALL PASS
4. Full database sync from block 17,699,264 to 17,709,263 - SUCCESS
