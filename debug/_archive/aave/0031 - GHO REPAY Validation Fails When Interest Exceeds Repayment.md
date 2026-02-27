# Issue: GHO REPAY Validation Fails When Interest Exceeds Repayment

## Date
2025-02-21

## Symptom
```
Transaction validation failed:
Operation 0 (GHO_REPAY): Expected 1 GHO debt burn for GHO_REPAY, got 0
```

## Root Cause
The `_validate_gho_repay()` method in `aave_transaction_operations.py` expected exactly 1 `GHO_DEBT_BURN` event for every GHO_REPAY operation. However, when the accrued interest exceeds the repayment amount, Aave's debt token emits a `Mint` event instead of a `Burn` event.

In Aave's `ScaledBalanceTokenBase._burnScaled()` function:
```solidity
if (nextBalance > previousBalance) {
    // Interest accrued > repayment amount
    // User's debt actually INCREASED
    emit Mint(user, user, amountToMint, balanceIncrease, index);
} else {
    // Normal case: debt decreases
    emit Burn(user, target, amountToBurn, balanceIncrease, index);
}
```

In this transaction:
- User repaid GHO
- Accrued interest was 4,634.83 GHO
- Since interest exceeded repayment, the debt token MINTED 14,779.63 GHO instead of burning
- The event at logIndex 222 is `SCALED_TOKEN_MINT`, not `SCALED_TOKEN_BURN`
- Validation failed expecting 1 burn, found 0

## Transaction Details

- **Hash**: `0xd08a1044fed4f8e998a2a97bed37362713803a64e1b56c4ef2e29a0057cf08f2`
- **Block**: 18240233
- **Chain**: Ethereum mainnet (chain_id: 1)
- **Function**: `repay(address,uint256,uint256)`
- **User**: `0x5b85B47670778b204041D6457dB8b5F5D36fa97a`
- **Asset (Reserve)**: GHO (`0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f`)
- **GHO Variable Debt Token**: `0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B`

### Event Flow

| LogIndex | Event | Contract | Description |
|----------|-------|----------|-------------|
| 220 | Approval | GHO Token | Approval for Pool |
| 221 | Transfer | GHO Debt | address(0) → user (mint 14,779.63 GHO) |
| **222** | **ScaledTokenMint** | **GHO Debt** | **Mint 14,779.63 GHO (interest > repayment)** |
| 223 | ReserveDataUpdated | Aave Pool | Reserve rate update |
| 224 | Transfer | GHO Token | User repays |
| 225 | Repay | Aave Pool | REPAY event emitted |

**Missing**: No `SCALED_TOKEN_BURN` event - instead got `SCALED_TOKEN_MINT`

## Fix

**File**: `src/degenbot/cli/aave_transaction_operations.py`

```python
def _validate_gho_repay(self, op: Operation) -> list[str]:
    """Validate GHO REPAY operation."""
    errors = self._validate_repay(op)

    # GHO repay can emit either BURN (debt reduction) or MINT (interest > repayment)
    # When interest accrued exceeds repayment amount, the debt token mints instead of burns
    gho_events = [
        e for e in op.scaled_token_events
        if e.event_type in {"GHO_DEBT_BURN", "GHO_DEBT_MINT"}
    ]
    if len(gho_events) > 1:
        errors.append(f"Expected 0 or 1 GHO debt event for GHO_REPAY, got {len(gho_events)}")

    return errors
```

**Change**: Modified validation to accept either GHO_DEBT_BURN or GHO_DEBT_MINT events (0 or 1), allowing for the case where interest exceeds repayment.

## Key Insight

GHO V3 REPAY operations have two valid scenarios:
1. **Normal repayment**: Emits 1 `GHO_DEBT_BURN` event (debt reduction)
2. **Interest > repayment**: Emits 1 `GHO_DEBT_MINT` event (debt actually increases due to accrued interest exceeding repayment)

The second scenario occurs when:
- User repays less than total accrued interest
- Interest accrual happens in same transaction before repayment
- Net result is debt increase (mint) rather than decrease (burn)

This is the GHO equivalent of the standard debt token behavior fixed in debug report #0029.

## Refactoring

1. **Consider consolidating validation logic** between standard REPAY and GHO_REPAY to ensure fixes apply to both
2. **Add test coverage** for edge cases:
   - GHO repayment where interest > repayment (1 mint)
   - GHO normal repayment (1 burn)
   - GHO interest-only repayment (0 events)

## References

- Transaction: [0xd08a1044fed4f8e998a2a97bed37362713803a64e1b56c4ef2e29a0057cf08f2](https://etherscan.io/tx/0xd08a1044fed4f8e998a2a97bed37362713803a64e1b56c4ef2e29a0057cf08f2)
- Block: [18240233](https://etherscan.io/block/18240233)
- Aave V3 Pool Contract: `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`
- Related Issue: debug/aave/0029 - REPAY Validation Fails for Interest-Only Repayments
