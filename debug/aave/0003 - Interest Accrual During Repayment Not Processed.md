# Issue: Interest Accrual During Repayment Not Processed

**Date:** 2026-02-27

**Symptom:**
```
AssertionError: User 0xE873793b15e6bEc6c7118D8125E40C122D46714D: debt balance (54591071096) does not match scaled token contract (54591070997) @ 0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8 at block 16910244
```

**Root Cause:**
When a user repays a variable debt token, if the accrued interest is greater than the repayment amount, the Aave contract's `_burnScaled` function:
1. Burns the scaled repayment amount
2. Mints the net interest (balanceIncrease - amount) to the user

The emitted Mint event has:
- `value` = amountToMint = balanceIncrease - amount (net interest after repayment)
- `balanceIncrease` = total interest accrued

The TransactionOperationsParser was incorrectly skipping DEBT_MINT events during REPAY transactions (line 1272-1273 in aave_transaction_operations.py):
```python
if has_repay and not has_collateral_burn:
    continue
```

This logic assumed all DEBT_MINT events during REPAY should be handled by the REPAY operation, but interest accrual mints (where balance_increase > amount) need to be processed separately as INTEREST_ACCRUAL operations.

**Transaction Details:**
- **Hash:** 0x96b71f9698a072992a4e0a4ed1ade34c1872911dda9790d94946fa38360d302d
- **Block:** 16910244
- **Type:** REPAY (variable debt)
- **User:** 0xE873793b15e6bEc6c7118D8125E40C122D46714D
- **Asset:** USDT (reserve 0xdAC17F958D2ee523a2206206994597C13D831ec7)
- **vToken:** 0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8
- **Repayment:** 100 USDT
- **Interest Accrued:** 26,904 (scaled)
- **Net Minted:** 26,804 (scaled)

**Events in Transaction:**
1. Transfer(from=0x0000...0000, to=user, value=26804) - Mint transfer
2. Mint(caller=user, onBehalfOf=user, value=26804, balanceIncrease=26904, index=...)
3. Repay(reserve=USDT, user=user, repayer=user, amount=100, useATokens=false)
4. USDT Transfer (repayment to pool)

**Fix:**
File: `src/degenbot/cli/aave_transaction_operations.py` (lines 1272-1273)

Changed from:
```python
if has_repay and not has_collateral_burn:
    continue
```

To:
```python
# Skip DEBT_MINT during REPAY only if it's not interest accrual
# Interest accrual during repayment: balance_increase > amount
# This occurs in _burnScaled when interest > repayment amount
if has_repay and not has_collateral_burn and ev.balance_increase <= ev.amount:
    continue
```

This fix ensures that DEBT_MINT events representing interest accrual (balance_increase > amount) are processed as INTEREST_ACCRUAL operations, while DEBT_MINT events that are part of the normal repayment flow (balance_increase == amount) are still skipped and handled by the REPAY operation.

**Key Insight:**
The Aave v3 protocol has a nuanced behavior during variable debt repayment:
- When interest > repayment: The contract mints net interest (balanceIncrease - amount) to the user
- The Mint event's `value` field represents the net minted amount, not the total interest
- The actual interest is in `balanceIncrease`
- The net balance change is: +interest_scaled - repayment_scaled

**Refactoring:**
The current logic in `_create_interest_accrual_operations` has grown complex over time. A cleaner approach would be:
1. Always categorize Mint events based on their properties (value vs balance_increase)
2. Let the operation matching logic determine which operation a Mint belongs to
3. Remove special-case handling for REPAY transactions
4. Create INTEREST_ACCRUAL operations for all unassigned Mint events with balance_increase > 0

This would simplify the code and reduce the risk of similar bugs in the future.

**Additional Fixes:**
- Fixed debt processor v1.py, v4.py, v5.py to correctly calculate balance delta during interest accrual
- Fixed GHO debt processors (v1, v2, v4, v5) similarly
- Added check to skip Transfer events from zero address (mints) in `_process_debt_transfer_with_match`
- Updated test `test_repay_with_zero_debt_burns_validates` to expect 2 operations (REPAY + INTEREST_ACCRUAL)

**Verification:**
- Full AAVE update completes successfully to block 16911070
- All 180 AAVE-related tests pass
- Verified transaction 0x96b71f... now processes correctly with balance 54591070997 (matches on-chain)
