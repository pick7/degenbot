# Issue: Non-GHO DEFICIT_CREATED Events Incorrectly Classified as GHO Flash Loans

**Date:** 2026-02-22

**Symptom:**
Transaction validation failed with error:
```
Operation 1 (GHO_FLASH_LOAN): Expected 1 GHO debt burn for FLASH_LOAN, got 0. DEBUG NOTE: Flash loans should have exactly one debt burn.
```

**Root Cause:**
The code in `_create_deficit_operation` assumed that all DEFICIT_CREATED events indicate GHO flash loans. However, DEFICIT_CREATED is a general Aave V3 mechanism for writing off bad debt and can occur for any reserve asset, not just GHO.

In the failing transaction (0x09f27f2ee2a04a13a85e137007135593d848ffd5d590980783cfcb2d2571ab04), the DEFICIT_CREATED event at logIndex 377 was for WBTC (asset: 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599), not GHO. The code incorrectly searched for a GHO debt burn event that didn't exist.

**Transaction Details:**
- Hash: 0x09f27f2ee2a04a13a85e137007135593d848ffd5d590980783cfcb2d2571ab04
- Block: 21928936
- Chain: Ethereum Mainnet (1)
- Operation Type: DEFICIT_CREATED (bad debt write-off for WBTC)

**Events in Transaction:**
- Log 377: DEFICIT_CREATED for user 0x9913e51274235E071967BEb71A2236A13F597A78, asset WBTC, amount 0.00001160 WBTC
- Logs 378-379: ReserveDataUpdated events (not UNKNOWN as initially logged)

**Fix:**
Modified `_create_deficit_operation` in `src/degenbot/cli/aave_transaction_operations.py` (lines 850-882):

Before:
```python
def _create_deficit_operation(...):
    """Create DEFICIT_CREATED (flash loan) operation."""
    # DEFICIT_CREATED always indicates GHO flash loan  # WRONG!
    user = self._decode_address(deficit_event["topics"][1])
    asset = self._decode_address(deficit_event["topics"][2])

    # Find GHO debt burn
    gho_burn = None
    for ev in scaled_events:
        if ev.event["logIndex"] in assigned_indices:
            continue
        if ev.event_type == "GHO_DEBT_BURN" and ev.user_address == user:
            gho_burn = ev
            break

    scaled_token_events = [gho_burn] if gho_burn else []

    return Operation(
        operation_id=operation_id,
        operation_type=OperationType.GHO_FLASH_LOAN,
        ...
    )
```

After:
```python
def _create_deficit_operation(...):
    """Create DEFICIT_CREATED operation.

    DEFICIT_CREATED indicates bad debt write-off. When the asset is GHO,
    it's a GHO flash loan that requires a debt burn. For other assets,
    it's a standalone deficit event with no associated debt burn.
    """
    user = self._decode_address(deficit_event["topics"][1])
    asset = self._decode_address(deficit_event["topics"][2])

    # Check if this is a GHO deficit (flash loan) or non-GHO deficit
    is_gho_deficit = asset == GHO_TOKEN_ADDRESS

    scaled_token_events = []
    if is_gho_deficit:
        # Find GHO debt burn for GHO flash loans
        for ev in scaled_events:
            if ev.event["logIndex"] in assigned_indices:
                continue
            if ev.event_type == "GHO_DEBT_BURN" and ev.user_address == user:
                scaled_token_events.append(ev)
                break

    return Operation(
        operation_id=operation_id,
        operation_type=OperationType.GHO_FLASH_LOAN if is_gho_deficit else OperationType.UNKNOWN,
        ...
    )
```

**Key Insight:**
DEFICIT_CREATED is a general mechanism in Aave V3 for handling bad debt across all reserves, not just GHO. The event signature is:
- `DEFICIT_CREATED(user, asset, amountCreated)`

When `asset == GHO_TOKEN_ADDRESS`, it's a GHO flash loan requiring debt burn validation. For other assets, it's a bad debt write-off that doesn't require matching debt burns.

**Refactoring:**
Consider renaming `GHO_FLASH_LOAN` operation type to `GHO_DEFICIT` for clarity, as "flash loan" is a specific use case while "deficit" is the general mechanism. Also consider adding a dedicated `DEFICIT` operation type for non-GHO bad debt write-offs if these need to be tracked separately.

**Related Debug Reports:**
- 0013 - DEFICIT_CREATED handling in general
- 0016 - DEFICIT_CREATED handling in GHO liquidations
