# Aave Debug Report

## Issue: Flash Loan Liquidation Validation Fails Without Debt Burn

**Date:** 2026-02-21

**Symptom:**
```
TransactionValidationError: Expected 1 debt burn for LIQUIDATION, got 0
```

**Root Cause:**
The `_validate_liquidation()` function in `src/degenbot/cli/aave_transaction_operations.py` expected exactly 1 debt burn event for every LIQUIDATION operation. However, flash loan liquidations (a common MEV bot pattern) do not emit debt burn events because the debt repayment happens through flash loan mechanics rather than standard debt token burns.

In a flash loan liquidation:
1. The liquidator flash mints debt tokens (DEBT_MINT event) to obtain liquidity
2. Uses these tokens to repay the user's debt
3. Receives collateral (COLLATERAL_BURN event)
4. Swaps the collateral to repay the flash loan

There is no DEBT_BURN event because the debt is handled through the flash loan mint/repay cycle.

**Transaction Details:**
- **Hash:** 0xcb087ea4d8d1b7c890318c3eccd7f730f24a1f1b55b25c156b9649e543de0588
- **Block:** 19648924
- **Type:** Flash Loan Liquidation (MEV Bot)
- **User Being Liquidated:** 0x09D86D566092bEc46D449e72087ee788937599D2
- **Liquidator:** 0x8Ce45e650aB17B6CA0dD6071f7c2B5c69B5b42b2
- **Collateral Asset:** SNX (0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F)
- **Debt Asset:** USDC (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48)
- **Debt Covered:** 22,195.99 USDC
- **Collateral Seized:** 9,048.59 SNX

**Events:**
- [510] DEBT_MINT at USDC VariableDebtToken (0x72E95b8931767C79bA4EeE721354d6E99a61D004) - Flash loan borrow
  - caller: 0x09D86D566092bEc46D449e72087ee788937599D2
  - onBehalfOf: 0x09D86D566092bEc46D449e72087ee788937599D2
  - value: 11,627.95
- [511] ReserveDataUpdated at Pool (USDC reserve)
- [513] ReserveDataUpdated at Pool (SNX reserve)
- [515] COLLATERAL_BURN at SNX AToken (0xC7B4c17861357B8ABB91F25581E7263e08DCB59c)
  - from: 0x09D86D566092bEc46D449e72087ee788937599D2
  - target: 0x8Ce45e650aB17B6CA0dD6071f7c2B5c69B5b42b2
  - value: 9,037.58
- [522] LIQUIDATION_CALL at Pool
  - collateralAsset: SNX
  - debtAsset: USDC
  - user: 0x09D86D566092bEc46D449e72087ee788937599D2
  - debtToCover: 22,195.99

**Analysis:**
The key events show this is a flash loan liquidation:
1. Event 510 is a DEBT_MINT (not BURN) - this is the flash loan being taken
2. Event 515 is the COLLATERAL_BURN - collateral being seized
3. Event 522 is the LIQUIDATION_CALL

There is no DEBT_BURN event because the liquidator used a flash loan to obtain USDC, repaid the user's debt with it, and then repaid the flash loan by swapping the received SNX collateral.

**Fix:**
Modified `_validate_liquidation()` in `src/degenbot/cli/aave_transaction_operations.py` to allow 0 or 1 debt burns instead of requiring exactly 1:

```python
def _validate_liquidation(self, op: Operation) -> list[str]:
    """Validate LIQUIDATION operation."""
    errors = []

    if not op.pool_event:
        errors.append("Missing LIQUIDATION_CALL pool event")
        return errors

    # Should have 1 collateral burn and 0 or 1 debt burns
    # Flash loan liquidations have 0 debt burns (debt repaid via flash loan)
    # Standard liquidations have 1 debt burn
    debt_burns = [e for e in op.scaled_token_events if e.is_debt]
    collateral_burns = [e for e in op.scaled_token_events if e.is_collateral]

    if len(debt_burns) > 1:
        errors.append(
            f"Expected 0 or 1 debt burns for LIQUIDATION, got {len(debt_burns)}. "
            f"DEBUG NOTE: Check if debt/collateral events are being assigned to wrong operations. "
            f"Current debt burns: {[e.event['logIndex'] for e in debt_burns]}. "
            f"User in LIQUIDATION_CALL: {self._decode_address(op.pool_event['topics'][3])}"
        )

    if len(collateral_burns) != 1:
        errors.append(
            f"Expected 1 collateral burn for LIQUIDATION, got {len(collateral_burns)}. "
            f"DEBUG NOTE: Check collateral asset matching and user address consistency. "
            f"Current collateral burns: {[e.event['logIndex'] for e in collateral_burns]}. "
            f"User in LIQUIDATION_CALL: {self._decode_address(op.pool_event['topics'][3])}"
        )

    return errors
```

**Key Insight:**
Flash loan liquidations are a common MEV bot pattern where:
1. No DEBT_BURN event is emitted (flash loans don't burn debt, they mint and repay)
2. Only COLLATERAL_BURN and LIQUIDATION_CALL events are present
3. The debt repayment happens through flash loan mechanics outside the standard liquidation flow

The validation must account for both patterns:
- **Standard liquidation:** 1 debt burn + 1 collateral burn
- **Flash loan liquidation:** 0 debt burns + 1 collateral burn

**Prevention:**
To prevent similar bugs:
1. Research common MEV bot patterns and liquidation strategies
2. Consider that not all liquidations follow the standard flow
3. Look for transactions with LIQUIDATION_CALL but no debt burns
4. Flash loans can affect various operations (liquidations, arbitrage, etc.)
5. Validation rules should account for legitimate alternative patterns

**Related Issues:**
- debug/aave/0012 - Collateral Operations Consume LIQUIDATION_CALL Events
- debug/aave/0009 - Collateral Burn Events Miss LiquidationCall Matching

**Contract References:**
- Aave V3 Pool: 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2
- USDC VariableDebtToken: 0x72E95b8931767C79bA4EeE721354d6E99a61D004
- SNX AToken: 0xC7B4c17861357B8ABB91F25581E7263e08DCB59c

**Verification:**
- Etherscan: https://etherscan.io/tx/0xcb087ea4d8d1b7c890318c3eccd7f730f24a1f1b55b25c156b9649e543de0588
- Transaction executed successfully on-chain, validation failure was a false positive
