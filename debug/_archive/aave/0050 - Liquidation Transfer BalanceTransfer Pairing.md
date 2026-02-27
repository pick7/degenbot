# Issue: Liquidation Transfer-BalanceTransfer Pairing

## Date
2026-02-26

## Symptom
```
AssertionError: User 0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D: collateral balance (2211164113880254579) does not match scaled token contract (2215267461796176200) @ 0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8 at block 16521648
```

## Root Cause
During Aave V3 liquidations, multiple transfer events occur that represent the same underlying balance movement:

1. **ERC20 Transfer event** (index=0): Records the actual token amount transferred
2. **BalanceTransfer event** (index>0): Records the scaled amount and liquidity index

These two events represent the SAME transfer (e.g., liquidation fee to treasury), but they were being processed separately, causing double-counting of the balance reduction.

Additionally, transfers to the treasury address (0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c) were incorrectly creating/increasing collateral positions for the treasury, when the treasury receiving liquidation fees should not affect its position balance.

## Transaction Details
- **Hash:** 0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec
- **Block:** 16521648
- **Type:** LIQUIDATION_CALL
- **User:** 0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D
- **Asset:** aWETH (0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8)

### Key Events
| LogIndex | Event Type | From | To | Amount | Index |
|----------|-----------|------|-----|---------|-------|
| 146 | Burn | User | Zero | 857,051,950,632,003,076 | > 0 |
| 151 | Transfer | User | Treasury | 4,102,696,351,289,535 | 0 |
| 152 | BalanceTransfer | User | Treasury | 4,102,044,786,657,449 | > 0 |

## Fix Location
**File:** `src/degenbot/cli/aave_transaction_operations.py`
**Function:** `_create_liquidation_operation`

### Changes Made

1. **Populate balance_transfer_events in liquidation operations:**
   ```python
   for transfer in collateral_transfers:
       scaled_token_events.append(transfer)
       # Track BalanceTransfer events separately so ERC20 Transfers can use
       # them for proper scaling during processing
       if transfer.index > 0:
           balance_transfer_events.append(transfer.event)
   ```

2. **Deduplicate events in get_all_events():**
   Modified `get_all_events()` to track seen log indices and avoid duplicates when an event is in both `scaled_token_events` and `balance_transfer_events`.

3. **Skip BalanceTransfer events when paired:**
   Added logic in `_process_collateral_transfer_with_match` to skip processing BalanceTransfer events when they're tracked in `balance_transfer_events` (meaning they'll be handled by their paired ERC20 Transfer).

4. **Skip treasury position updates:**
   Modified the recipient handling in `_process_collateral_transfer_with_match` to skip creating/updating collateral positions for the treasury address (0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c).

## Key Insight
The ERC20 Transfer and BalanceTransfer events are two views of the same underlying transfer:
- ERC20 Transfer shows the actual amount (what users see)
- BalanceTransfer shows the scaled amount and index (what the contract stores)

During processing, the ERC20 Transfer should use the BalanceTransfer for accurate scaling, but only ONE of them should actually modify the balance (the ERC20 Transfer).

## Refactoring
Consider consolidating transfer event handling to automatically detect and pair ERC20 Transfers with BalanceTransfers across all operation types, not just liquidations. This would simplify the logic and prevent similar issues in other scenarios.

## Test Results
All 122 existing Aave tests pass with these changes.
