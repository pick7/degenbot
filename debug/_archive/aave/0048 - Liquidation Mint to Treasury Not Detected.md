# Aave Debug Progress

## Issue: Liquidation Mint to Treasury Not Detected as MINT_TO_TREASURY

**Date:** 2026-02-26

**Symptom:**
```
AssertionError: User 0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D: collateral balance (2211163464781983434) does not match scaled token contract (2215267461796176200) @ 0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8 at block 16521648
```

**Root Cause Analysis:**

During a liquidation transaction (0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec), the following events occurred:

1. **Event 147**: Burn - User's collateral burned (857,051,950,632,003,076 wei)
2. **Event 150**: Mint - Protocol fee minted to treasury (2,239,091,028,604 wei)
3. **Event 151**: Transfer - Liquidation bonus transferred to treasury (4,102,696,351,289,535 wei)
4. **Event 152**: BalanceTransfer - Scaled balance transfer to treasury (4,102,044,786,657,449 wei)
5. **Event 154**: LiquidationCall - The liquidation pool event

The Mint event at logIndex 150 has:
- **Caller**: 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2 (Aave Pool V3)
- **User/onBehalfOf**: 0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c (Aave Treasury)
- **Amount**: 2,239,091,028,604 wei

This Mint event SHOULD be detected as a MINT_TO_TREASURY operation because:
1. It's a COLLATERAL_MINT event type
2. The caller is the Pool contract
3. The user is the Treasury address

However, the balance verification shows a discrepancy of 4,103,997,014,192,766 wei, suggesting that either:
1. The Mint event is being processed as a SUPPLY operation instead of MINT_TO_TREASURY
2. The Transfer event (event 151) from user to treasury is not being processed correctly

The Transfer event at logIndex 151 shows 4,102,696,351,289,535 wei being transferred from the liquidated user to the treasury, which is very close to the balance discrepancy.

**Transaction Details:**
- **Hash:** 0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec
- **Block:** 16521648
- **Type:** Liquidation
- **Liquidator:** 0x3697E949A4d9a507A6Ce2f6ff6bB99Bcc8EaCb81 (MEV Bot)
- **Liquidated User:** 0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D
- **Treasury:** 0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c
- **Collateral Asset:** WETH (aWETH token: 0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8)
- **Debt Asset:** DAI

**Expected Behavior:**
1. Mint event with caller=Pool should be detected as MINT_TO_TREASURY
2. MINT_TO_TREASURY operations should be skipped (not update any user balance)
3. Transfer from user to treasury should reduce the user's balance
4. Burn event should reduce the user's balance

**Actual Behavior:**
The database balance is 4,103,997,014,192,766 wei LESS than the contract balance, suggesting that:
- Either a deduction was recorded that shouldn't have been
- Or a balance reduction was recorded with a larger amount than actual

**Investigation Notes:**

1. The `_create_mint_to_treasury_operations` function SHOULD detect this Mint event because:
   - `ev.event_type == "COLLATERAL_MINT"` is True
   - `ev.caller_address == self.pool_address` is True (both are 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2)

2. The Mint event is NOT being assigned to the LIQUIDATION operation because `_create_liquidation_operation` only looks for:
   - DEBT_BURN / GHO_DEBT_BURN
   - COLLATERAL_BURN
   - COLLATERAL_TRANSFER
   - UNKNOWN_TRANSFER

3. The transaction was processed successfully (transaction_end with success=true), but the balance verification at the next block failed.

**Next Steps:**
1. Verify that `_create_mint_to_treasury_operations` is being called correctly
2. Check if the pool_address comparison is working as expected
3. Add debug logging to trace the operation creation flow
4. Verify the transfer processing logic for liquidation bonus transfers

**Key Insight:**
The Mint event appears BEFORE the LiquidationCall event in the transaction log order (logIndex 150 vs 154). This ordering might affect how events are assigned to operations.

**Test Case:**
A test case has been added to `tests/cli/test_aave_mint_to_treasury.py::test_mint_to_treasury_in_liquidation_transaction` that reproduces the exact scenario.
