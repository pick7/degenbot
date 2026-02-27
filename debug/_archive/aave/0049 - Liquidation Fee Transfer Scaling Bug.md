# Issue: Liquidation Fee Transfer Scaling Bug

## Date
2026-02-26

## Symptom
```
AssertionError: User 0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D: collateral balance (2211163464781983434) does not match scaled token contract (2215267461796176200) @ 0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8 at block 16521648
```

## Root Cause
During AAVE V3 liquidations, there are two deductions from the liquidated user's collateral balance:
1. **Main collateral seized**: An ERC20 Transfer event to the zero address (burn)
2. **Liquidation fee to treasury**: An ERC20 Transfer event to the treasury address

The liquidation fee transfer is currently being **scaled** using the liquidity index, but it should use the **raw amount** directly. This causes the fee to be over-subtracted from the user's balance.

## Transaction Details
- **Hash**: `0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec`
- **Block**: 16521648
- **User**: `0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D`
- **Asset**: aWETH (`0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8`)
- **Treasury**: `0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c`

### Key Events

| LogIndex | Event Type | From | To | Amount (raw) | Index |
|----------|-----------|------|-----|--------------|-------|
| 146 | Transfer | User | Zero | 857,051,950,632,003,076 | 0 |
| 151 | Transfer | User | Treasury | 4,102,696,351,289,535 | 0 |
| 152 | BalanceTransfer | User | Treasury | 4,102,044,786,657,449 | > 0 |

## Balance Analysis

### Expected Calculation
- **Initial balance**: 3,077,185,547,692,502,276
- **Main collateral**: -857,051,950,632,003,076
- **Liquidation fee**: -4,102,696,351,289,535
- **Expected final**: 2,216,030,900,709,209,665

### Actual Results
- **Database balance**: 2,211,163,464,781,983,434
- **Contract balance**: 2,215,267,461,796,176,200
- **Difference**: ~4,103,997,014,192,766 (approximately the liquidation fee)

## Fix Location
**File**: `src/degenbot/cli/aave.py`
**Function**: `_process_collateral_transfer_with_match`
**Lines**: 2935-2952

The fix should detect when a transfer is:
1. To the treasury address (`0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c`)
2. Part of a LIQUIDATION operation

In these cases, use the raw transfer amount directly instead of scaling it.

## Current Fix Attempt
Added special case handling for treasury transfers during liquidations:

```python
# Special case: liquidation fee transfers to treasury should use raw amount
treasury_address = get_checksum_address("0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c")
if (
    scaled_event.target_address == treasury_address
    and context.operation
    and context.operation.operation_type == OperationType.LIQUIDATION
):
    # Use raw amount for liquidation fee transfers to treasury
    transfer_amount = scaled_event.amount
    transfer_index = int(collateral_asset.liquidity_index)
else:
    # Normal scaling logic...
```

## Status
**Partial fix applied** - The balance changed from 2,211,163,464,781,983,434 to 2,211,164,113,880,254,579 after the fix, but still doesn't match the expected 2,215,267,461,796,176,200.

## Further Investigation Needed
There may be additional issues:
1. The BalanceTransfer event (LogIndex 152) might also be processed separately
2. The main collateral Transfer (LogIndex 146) might be getting double-counted
3. There could be interaction with existing skip logic that matches transfers to burns

## Key Insight
The AAVE liquidation event structure is complex:
- Transfer to zero (LogIndex 146): represents collateral being burned
- Transfer to treasury (LogIndex 151): represents liquidation fee
- BalanceTransfer to treasury (LogIndex 152): represents the scaled version of the fee

The Transfer and BalanceTransfer to treasury represent the SAME deduction, so both should not be subtracted. The Transfer should use the raw amount, while the BalanceTransfer should be scaled to match the Transfer amount.
