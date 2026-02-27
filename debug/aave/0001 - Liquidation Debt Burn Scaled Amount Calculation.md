# Issue: Liquidation Debt Burn Scaled Amount Calculation

**Date:** 2025-02-27

**Symptom:**
```
AssertionError: User 0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D: debt balance (426152596537775759) does not match scaled token contract (1265122824104596191104) @ 0xcF8d0c70c850859266f5C338b38F9D663181C314 at block 16521648
```

**Root Cause:**
When processing liquidation debt burns, the code was calculating the scaled burn amount from the `debt_to_cover` value in the LIQUIDATION_CALL event. However, the actual Burn event contains different values that account for interest accrual between the liquidation call and the burn:

- `debt_to_cover` from LIQUIDATION_CALL: 1265883725747618387045
- Burn event `value`: 1264696671508058415345  
- Burn event `balance_increase`: 1187054239559971700
- Actual amount to burn: `value` + `balance_increase` = 1265883725747618387045

The discrepancy arises because:
1. `debt_to_cover` represents the amount the liquidator intends to repay
2. By the time the Burn event is emitted, interest has accrued (balance_increase)
3. The actual scaled amount must be calculated from the Burn event values, not from `debt_to_cover`

**Transaction Details:**
- **Hash:** 0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec
- **Block:** 16521648
- **Type:** LIQUIDATION_CALL
- **User:** 0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D
- **Asset:** DAI (Variable Debt Token: 0xcF8d0c70c850859266f5C338b38F9D663181C314)
- **Debt Token Revision:** 1

**Fix:**
Modified `_process_debt_burn_with_match` in `src/degenbot/cli/aave.py`:

```python
# For liquidations, use the debt_to_cover amount ONLY for pre-v4 tokens
# For v4+, let the processor calculate from the actual Burn event values
# to avoid discrepancies between debt_to_cover and actual burned amount
is_liquidation = context.operation is not None and context.operation.operation_type in {
    OperationType.LIQUIDATION,
    OperationType.GHO_LIQUIDATION,
    OperationType.SELF_LIQUIDATION,
}

if raw_amount is None and not is_liquidation:
    raw_amount = extraction_data.get("debt_to_cover")

if raw_amount is not None and debt_asset.v_token_revision >= 4:
    # Calculate scaled amount from raw_amount
    ...
```

For liquidations (and revision 1 tokens), `raw_amount` remains `None`, which causes `scaled_amount` to remain `None`. When the processor receives `scaled_amount=None`, it calculates the scaled amount from the actual Burn event values (`value` + `balance_increase`) using the appropriate ray_div method for the token revision.

Same fix applied to `_process_debt_mint_with_match` for consistency.

**Key Insight:**
The `debt_to_cover` value in LIQUIDATION_CALL represents the liquidator's intent at the time of the call, while the Burn event contains the actual values after interest accrual. For accurate balance tracking, the scaled amount must be calculated from the Burn event values, not from the liquidation intent.

**Refactoring:**
1. Consider adding a dedicated liquidation processor that handles the complex logic of matching liquidation events to burn/mint events
2. Add comprehensive unit tests for liquidation scenarios across all token revisions
3. Add debug logging to track the decision path for scaled amount calculation
4. Document the relationship between Pool events and ScaledToken events for liquidations

**Files Modified:**
- `src/degenbot/cli/aave.py` (lines ~2885-2902 and ~2970-2995)
