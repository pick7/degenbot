# Issue: Double Counting Debt Burns in Liquidations

**Date:** 2026-02-27

**Symptom:**
```
AssertionError: User 0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D: debt balance (426152596537775759) does not match scaled token contract (1265122824104596191104) @ 0xcF8d0c70c850859266f5C338b38F9D663181C314 at block 16521648
```

**Root Cause:**
During liquidations, both an ERC20 Transfer event (to the zero address) and a Burn event are emitted for debt tokens. The Transfer event to the zero address represents the same debt reduction as the Burn event. The code was processing both events, resulting in the debt balance being reduced twice (double-counting).

In the failing transaction:
1. **Transfer event** (logIndex 142): Transfer from user to 0x0000...0000 for 1,264,696,671,508,058,415,345
2. **Burn event** (logIndex 143): Burn of 1,264,696,671,508,058,415,345 principal + 1,187,054,239,559,971,700 interest

The Transfer event was being processed by `_process_debt_transfer_with_match()`, which reduced the sender's balance by the transfer amount. Then the Burn event was processed by `_process_debt_burn_with_match()`, which reduced the balance again by the full burn amount including interest.

Starting balance: 2,530,245,627,901,730,885,136
Expected ending balance: 1,265,122,824,104,596,191,104
Actual ending balance: 426,152,596,537,775,759 (wrong)

**Transaction Details:**
- **Hash:** 0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec
- **Block:** 16521648
- **Type:** LIQUIDATION_CALL
- **User:** 0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D
- **Asset:** DAI (Variable Debt Token: 0xcF8d0c70c850859266f5C338b38F9D663181C314)
- **Debt Token Revision:** 1

**Fix:**
Modified `_process_debt_transfer_with_match()` in `src/degenbot/cli/aave.py` to skip processing Transfer events where the target is the zero address:

```python
# Skip transfers to zero address (burns) - these are handled by Burn events
# Processing both Transfer(to=0) and Burn would result in double-counting
if scaled_event.target_address == ZERO_ADDRESS:
    return
```

**Key Insight:**
When a debt token burn occurs, the Aave protocol emits both:
1. An ERC20 Transfer event (from user to address(0)) for the principal amount
2. A Burn event (with value, balanceIncrease, and index) for the full amount including interest

The Transfer event is a side-effect of the ERC20 standard, but the actual balance change should only be processed from the Burn event, which has the complete information including interest accrual.

**Refactoring:**
1. Consider filtering out Transfer-to-zero events at the parsing level so they don't create separate operations
2. Add documentation explaining the relationship between Transfer and Burn events for debt tokens
3. Consider adding a warning log when Transfer-to-zero events are skipped for debugging purposes
4. Review collateral token processing to ensure similar issues don't exist there

**Files Modified:**
- `src/degenbot/cli/aave.py` (line ~3254-3258 in `_process_debt_transfer_with_match`)

**Verification:**
After the fix, running `uv run degenbot aave update --to-block=16521648 --verify` completes successfully with the correct ending balance of 1,265,122,824,104,596,191,104.
