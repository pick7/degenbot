# Issue 0009: Debt Swap Transaction Processing

## Date
2026-02-28

## Symptom
```
AssertionError: User 0xC5Ec4153F98729f4eaf61013B54B704Eb282ECF4: debt balance (961160985395385548453) does not match scaled token contract (962181849427417876866) @ 0x3D3efceb4Ff0966D34d9545D3A2fa2dcdBf451f2 at block 17996836
```

## Root Cause

**CRITICAL FINDING**: The discrepancy existed BEFORE the transaction at block 17996836 was processed.

### Balance Analysis

**At block 17996835 (before the failing tx):**
- Contract balance: ~961.162005239573392938 scaled units
- Database balance: ~961.160985395385548453 scaled units  
- Discrepancy: Already ~1.02 scaled units SHORT in database

**At block 17996836 (after the failing tx):**
- Contract balance: ~962.181849427417876866 scaled units
- Database balance: ~961.160985395385548453 scaled units
- Discrepancy: ~1.020864032032413 scaled units SHORT in database

**Key Insight**: The discrepancy of 1,020,864,032,032,413 scaled units was introduced in a **previous update**, not in this transaction. This transaction is just where the verification caught the existing error.

The failure occurs during verification of a **debt swap transaction** (tx: `0xa044d93a1aced198395d3293d4456fcb09a9a734d2949b5e2dff66338fa89625` at block 17996836).

### Transaction Overview

This is a complex debt swap operation where a user swaps USDC debt for BAL debt using a flash loan:

1. **Delegation**: User delegates borrowing power to swap contract `0x8f30adaa...`
2. **Flash Loan**: Borrow BAL tokens from Aave Pool
3. **DEX Swap**: Swap BAL for USDC via Paraswap
4. **Repay USDC Debt**: Repay 5,000,000 USDC (triggers interest accrual mint on USDC vToken)
5. **Borrow BAL**: Borrow BAL to repay flash loan (mints BAL vTokens)
6. **Repay Flash Loan**: Return BAL to complete flash loan

### Event Sequence for BAL Debt Token (0x3D3efceb...)

| LogIndex | Event | From | To | Amount/Value |
|----------|-------|------|-----|--------------|
| 0x124 | BorrowAllowanceDelegated | - | - | - |
| 0x125 | Transfer | 0x0 | borrower | 2165652418921690976 |
| 0x126 | Mint | borrower (onBehalfOf) | - | value=2165652418921690976, balanceIncrease=1074688878852248839 |
| 0x12a | Transfer | borrower | 0x0 | 175680808713436896 |
| 0x12b | Burn | borrower (from) | - | value=175680808713436896, balanceIncrease=0 |

### The Problem

The BAL debt mint event (log 0x126) has:
- `caller`: 0x8f30adaa6950b31f675bf8a709bc23f55aa24735 (swap contract)
- `onBehalfOf`: 0xC5Ec4153F98729f4eaf61013B54B704Eb282ECF4 (borrower)
- `value` (2165652418921690976) > `balanceIncrease` (1074688878852248839)

This indicates a **BORROW** operation where:
- `amountToMint = value - balanceIncrease = 1090963540069442137`
- The swapper is borrowing BAL on behalf of the borrower
- The tokens are minted to the swapper (caller), not the borrower

However, the processing code uses `on_behalf_of_address` as the user, attributing the mint to the borrower when it should be attributed to the swapper.

### Balance Mismatch Analysis

**Database Balance**: 961160985395385548453  
**Contract Balance**: 962181849427417876866  
**Difference**: 1,020,864,032,032,413 (approximately 1 scaled unit)

The discrepancy arises because:
1. The Mint event adds ~44,551,487 scaled units (interest component)
2. The Burn event removes ~175,680,808,713,436,896 scaled units
3. The net change should decrease the borrower's balance
4. But the code incorrectly attributes the Mint to the borrower

## Transaction Details

- **Hash**: 0xa044d93a1aced198395d3293d4456fcb09a9a734d2949b5e2dff66338fa89625
- **Block**: 17996836
- **Type**: Debt Swap (via swapDebt function)
- **User**: 0xC5Ec4153F98729f4eaf61013B54B704Eb282ECF4
- **Swapper**: 0x8f30adaa6950b31f675bf8a709bc23f55aa24735
- **Asset**: BAL (variableDebtEthBAL at 0x3D3efceb4Ff0966D34d9545D3A2fa2dcdBf451f2)
- **Debt Token Revision**: 5

## Fix

### Location
`src/degenbot/cli/aave.py` in `_process_scaled_token_mint_event` function around line 5075-5081

### Problem
The code uses `on_behalf_of_address` as the user for all debt mint events:
```python
user = _get_or_create_user(
    context=context,
    market=context.market,
    user_address=on_behalf_of_address,  # Wrong for delegated borrows
    ...
)
```

### Solution
For debt mint events where `caller != on_behalf_of`, the minted tokens go to the caller (the delegatee), not the onBehalfOf address. The fix should:

1. Check if this is a delegated borrow (caller != on_behalf_of)
2. For delegated borrows, attribute the mint to the caller (the swapper/liquidator)
3. The debt is still recorded against the onBehalfOf user, but the token balance goes to the caller

**Proposed Change**:
```python
# For debt mints, tokens go to the caller, not onBehalfOf
caller_address = _decode_address(context.event["topics"][1])
on_behalf_of_address = _decode_address(context.event["topics"][2])

# For delegated operations (caller != onBehalfOf), tokens are minted to caller
user_address = caller_address if caller_address != on_behalf_of_address else on_behalf_of_address

user = _get_or_create_user(
    context=context,
    market=context.market,
    user_address=user_address,
    ...
)
```

However, this needs careful consideration because:
- The debt is legally owed by `onBehalfOf`
- But the tokens are physically held by `caller`
- In most cases, the tokens are immediately burned/transferred

A better approach might be to check if the caller is a known liquidation/swap adapter contract and handle accordingly.

## Key Insight

**Debt delegation changes token ownership**: When a user delegates borrowing power via `delegationWithSig` or `approveDelegation`, subsequent borrows mint debt tokens to the delegatee (caller), not the delegator (onBehalfOf). This is different from regular borrows where the user borrows for themselves.

In debt swap transactions:
1. The swapper borrows on behalf of the user
2. The tokens go to the swapper
3. The swapper uses the tokens to repay the flash loan
4. The net effect is the user's debt changes from one asset to another

The current processing code doesn't account for this intermediate token ownership.

## Refactoring

1. **Add debt delegation tracking**: Track delegation approvals to understand when borrows are delegated
2. **Improve event matching**: Match debt mints with delegation events to properly attribute token ownership
3. **Consider net position changes**: For complex operations like debt swaps, consider processing the net effect rather than individual events
4. **Add contract detection**: Detect known swap/liquidation adapter contracts and handle them specially
5. **Documentation**: Document the token flow for delegated operations more clearly

## References

- Transaction: https://etherscan.io/tx/0xa044d93a1aced198395d3293d4456fcb09a9a734d2949b5e2dff66338fa89625
- Aave VariableDebtToken delegation: https://github.com/aave/aave-v3-core/blob/master/contracts/protocol/tokenization/VariableDebtToken.sol
