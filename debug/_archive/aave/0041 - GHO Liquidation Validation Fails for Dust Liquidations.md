## Issue: GHO Liquidation Validation Fails for Dust Liquidations

**Date:** 2026-02-22

**Symptom:**
```
Transaction validation failed:
Operation 8 (GHO_LIQUIDATION): Expected 1 GHO debt burn for GHO_LIQUIDATION, got 0. DEBUG NOTE: Verify GHO token address matching.
Operation 9 (GHO_LIQUIDATION): Expected 1 GHO debt burn for GHO_LIQUIDATION, got 0. DEBUG NOTE: Verify GHO token address matching.
```

**Root Cause:**
The `_validate_gho_liquidation()` function at `src/degenbot/cli/aave_transaction_operations.py:1095` incorrectly requires exactly 1 GHO debt burn event (`if len(gho_burns) != 1`). This assumption fails for "dust liquidations" where the `debtToCover` parameter is so small (effectively zero) that no actual GHO debt principal is burned. In these cases, the liquidation only:
- Transfers collateral (aTokens) to the liquidator
- Accrues interest (GHO_DEBT_MINT events)
- Does NOT burn any GHO debt principal

**Transaction Details:**
- **Hash:** 0x0ad468f0bd8e9b63a3cb464f27e686d28be9c3c54a7aee2791716388908cf769
- **Block:** 22126946
- **Chain:** Ethereum mainnet
- **Pool:** 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2 (Aave V3 Pool)
- **Type:** GHO_LIQUIDATION (dust liquidation)
- **Users:** 0xCd705deE3dB92533Fffa2bdd47b97ab573E8Ed14, 0xc94Db5Bb27d0951F8BeBE277619B45805DB62E69
- **Collateral:** wstETH (0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0)
- **Debt:** GHO (0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f)

**Fix:**
- **File:** `src/degenbot/cli/aave_transaction_operations.py`
- **Line:** 1095
- **Change:** Modified validation to allow 0 or 1 GHO debt burns instead of requiring exactly 1

```python
# Before:
if len(gho_burns) != 1:
    errors.append(
        f"Expected 1 GHO debt burn for GHO_LIQUIDATION, got {len(gho_burns)}. "
        f"DEBUG NOTE: Verify GHO token address matching."
    )

# After:
if len(gho_burns) > 1:
    errors.append(
        f"Expected 0 or 1 GHO debt burn for GHO_LIQUIDATION, got {len(gho_burns)}. "
        f"DEBUG NOTE: Dust liquidations may have 0 burns (zero debt to cover)."
    )
```

**Key Insight:**
Dust liquidations are a valid edge case in Aave where the liquidation is initiated but the debt amount to cover rounds to zero. The validation logic must accommodate both standard liquidations (with debt burn) and dust liquidations (without debt burn). This mirrors how standard liquidations already handle flash loan liquidations with `if len(debt_burns) > 1`.

**Refactoring:**
Consider standardizing validation patterns across liquidation types to consistently allow optional debt burn events. Add explicit handling for dust liquidations in the operation classification logic to distinguish them from regular liquidations for analytics purposes.
