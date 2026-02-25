# Collateral Mint Event Matching Fails for swapAndRepay Operations

**Issue:** Collateral mint events fail to match pool events in swapAndRepay transactions

**Date:** 2026-02-25

**Symptom:**
```
ValueError: No matching Pool event for collateral mint in tx f1a2cc8ddc3846f93151df903fe63a6603909b468b918185f9b4a6adf0e02e21. User: 0x6CD71d6Cb7824add7c277F2CA99635D98F8b9248, Reserve: 0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0. Available: ['3115d1449a', '2b627736bc', 'a534c8dbe7']
```

**Root Cause:**

In `swapAndRepay` operations (executed via ParaSwap), multiple collateral mints occur in a single transaction:

1. **Mint at logIndex 0x11f (287):** Interest accrual during withdrawal (value == balanceIncrease)
2. **Mint at logIndex 0x13d (317):** Supply of excess tokens after swap (value > balanceIncrease)

The first mint was incorrectly matching the SUPPLY event at 0x13e (318) instead of the WITHDRAW event at 0x128 (296) because:

- When `value == balanceIncrease`, the code tried SUPPLY first
- The SUPPLY event matched due to the caller_address (Paraswap contract) being in check_users
- The SUPPLY event was consumed, leaving no matching event for the second mint
- The Burn at 0x126 (294) then consumed the WITHDRAW event

**Transaction Details:**
- **Hash:** `f1a2cc8ddc3846f93151df903fe63a6603909b468b918185f9b4a6adf0e02e21`
- **Block:** 16502006
- **Type:** swapAndRepay (via ParaSwap Augustus Router)
- **User:** `0x6CD71d6Cb7824add7c277F2CA99635D98F8b9248`
- **Asset:** wstETH (`0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0`)
- **Operation:** Withdraw 107.375 wstETH, swap to USDC, repay 30,000 USDC debt, re-supply 0.654 wstETH excess

**Fix:**

Two changes were made:

1. **src/degenbot/cli/aave.py** (line ~3935): Modified the event matching logic to try WITHDRAW first when `event_amount == balance_increase` (pure interest accrual) instead of SUPPLY.

2. **src/degenbot/cli/aave_event_matching.py**: Added a `try_event_type_first` parameter to `find_matching_pool_event()` that allows overriding the default event type order from the MatchConfig.

```python
# When event_amount == balance_increase (pure interest accrual)
# Try WITHDRAW first to avoid incorrectly matching SUPPLY events
result = matcher.find_matching_pool_event(
    event_type=ScaledTokenEventType.COLLATERAL_MINT,
    user_address=caller_address,
    reserve_address=reserve_address,
    check_users=[user.address],
    try_event_type_first=AaveV3Event.WITHDRAW,  # Try WITHDRAW before SUPPLY
)
```

**Key Insight:**

Interest accrual mints (where value == balanceIncrease) typically occur during withdrawals, not deposits. The event matching order should reflect this context. The fix ensures that interest accrual mints during withdrawals match WITHDRAW events before trying SUPPLY, preventing them from consuming SUPPLY events that belong to other mints in the same transaction.

**Refactoring:**

The fix adds a `try_event_type_first` parameter to the EventMatcher, making it more flexible for handling edge cases where the default event type order isn't appropriate. This is a cleaner approach than creating specialized matching functions for each edge case.

**Tests:**

A unit test should verify that:
1. When `value == balanceIncrease`, the EventMatcher tries WITHDRAW before SUPPLY
2. The first mint in a swapAndRepay operation matches the WITHDRAW event
3. The second mint matches the SUPPLY event
4. Event consumption works correctly when multiple mints exist in one transaction
