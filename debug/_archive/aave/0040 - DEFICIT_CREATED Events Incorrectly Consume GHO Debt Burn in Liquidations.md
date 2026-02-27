# Issue: DEFICIT_CREATED Events Incorrectly Consume GHO Debt Burn in Liquidations

**Date:** 2026-02-22

**Symptom:**
Transaction validation failed with error:
```
Operation 1 (GHO_LIQUIDATION): Expected 1 GHO debt burn for GHO_LIQUIDATION, got 0. DEBUG NOTE: Verify GHO token address matching.
```

**Root Cause:**
During GHO liquidations, the Aave V3 protocol emits a `DEFICIT_CREATED` event as part of the bad debt write-off mechanism. This event is emitted before the `LIQUIDATION_CALL` event in the transaction logs. The `_create_deficit_operation` function was incorrectly treating all GHO `DEFICIT_CREATED` events as standalone flash loan operations, consuming the GHO debt burn event that should be matched to the liquidation operation.

In the failing transaction (0x7be807b4b43c60b00b84a7449d5ff6113ad42eab45affe3b837a2d71623c827a):
- LogIndex 156: GHO debt burn (variableDebtEthGHO)
- LogIndex 157: DEFICIT_CREATED for GHO (incorrectly treated as GHO_FLASH_LOAN)
- LogIndex 161: WETH collateral burn (aEthWETH)
- LogIndex 170: LIQUIDATION_CALL

The GHO debt burn at logIndex 156 was consumed by the GHO_FLASH_LOAN operation created from the DEFICIT_CREATED event at logIndex 157, leaving no debt burn for the GHO_LIQUIDATION operation.

**Transaction Details:**
- Hash: 0x7be807b4b43c60b00b84a7449d5ff6113ad42eab45affe3b837a2d71623c827a
- Block: 21993896
- Chain: Ethereum Mainnet (1)
- Operation Type: GHO Liquidation
- User Being Liquidated: 0xf5715961C550FC497832063a98eA34673ad7C816
- Debt Asset: GHO (0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f)
- Collateral Asset: WETH (0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2)

**Events in Transaction:**
- Log 156: SCALED_TOKEN_BURN (GHO debt) for user 0xf5715961C550FC497832063a98eA34673ad7C816, amount ~58.25 GHO
- Log 157: DEFICIT_CREATED for user 0xf5715961C550FC497832063a98eA34673ad7C816, asset GHO
- Log 161: SCALED_TOKEN_BURN (WETH collateral) for user 0xf5715961C550FC497832063a98eA34673ad7C816
- Log 170: LIQUIDATION_CALL for user 0xf5715961C550FC497832063a98eA34673ad7C816

**Fix:**
Modified `_create_deficit_operation` in `src/degenbot/cli/aave_transaction_operations.py` (lines 850-900):

Before:
```python
def _create_deficit_operation(...):
    """Create DEFICIT_CREATED operation."""
    user = self._decode_address(deficit_event["topics"][1])
    asset = self._decode_address(deficit_event["topics"][2])

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

After:
```python
def _create_deficit_operation(...):
    """Create DEFICIT_CREATED operation.

    Note: DEFICIT_CREATED can also be emitted during GHO liquidations as
    part of the bad debt write-off mechanism. In such cases, the GHO debt
    burn should be matched to the LIQUIDATION_CALL operation, not a
    separate flash loan operation.
    """
    user = self._decode_address(deficit_event["topics"][1])
    asset = self._decode_address(deficit_event["topics"][2])

    is_gho_deficit = asset == GHO_TOKEN_ADDRESS

    # Check if there's a LIQUIDATION_CALL for the same user in this transaction
    has_liquidation_for_user = False
    for ev in all_events:
        if ev["topics"][0] == AaveV3Event.LIQUIDATION_CALL.value:
            liquidation_user = self._decode_address(ev["topics"][3])
            if liquidation_user == user:
                has_liquidation_for_user = True
                break

    scaled_token_events = []
    if is_gho_deficit and not has_liquidation_for_user:
        # Find GHO debt burn for GHO flash loans only if not part of liquidation
        for ev in scaled_events:
            if ev.event["logIndex"] in assigned_indices:
                continue
            if ev.event_type == "GHO_DEBT_BURN" and ev.user_address == user:
                scaled_token_events.append(ev)
                break

    # If this DEFICIT_CREATED is part of a liquidation, mark it as UNKNOWN
    if is_gho_deficit and has_liquidation_for_user:
        operation_type = OperationType.UNKNOWN
    elif is_gho_deficit:
        operation_type = OperationType.GHO_FLASH_LOAN
    else:
        operation_type = OperationType.UNKNOWN

    return Operation(
        operation_id=operation_id,
        operation_type=operation_type,
        ...
    )
```

**Key Insight:**
DEFICIT_CREATED events during liquidations indicate bad debt write-off and should not consume the debt burn events that belong to the liquidation operation. The fix checks if there's a corresponding LIQUIDATION_CALL event for the same user before creating a GHO_FLASH_LOAN operation.

**Refactoring:**
Consider creating a dedicated `DEFICIT` operation type for bad debt write-offs that are not part of liquidations. This would provide better visibility into when and why deficits are created. Additionally, the operation creation logic could be refactored to process LIQUIDATION_CALL events before DEFICIT_CREATED events to avoid this type of ordering issue.

**Related Debug Reports:**
- 0039 - Non-GHO DEFICIT_CREATED Events Incorrectly Classified as GHO Flash Loans
- 0016 - DEFICIT_CREATED handling in GHO liquidations
- 0010 - GHO Debt Burn Consumes LiquidationCall Event Blocking Collateral Burn
