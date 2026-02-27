# Aave Debug Progress

## Issue: Liquidation Validation Fails Without Collateral Burn

**Date:** 2026-02-21

**Symptom:**
```
TRANSACTION VALIDATION FAILED

Transaction Hash: 0x621380dc92a951489f4717300d242ad2db640be2d2be5eb66e108b455cccaad2
Block: 19904828

----------------------------------------
PARSED OPERATIONS (1)
----------------------------------------

Operation 0: LIQUIDATION
  Pool Event: logIndex=14
  Scaled Token Events (0):
  VALIDATION ERRORS:
    X Expected 1 collateral burn for LIQUIDATION, got 0. DEBUG NOTE: Check collateral asset matching and user address consistency. Current collateral burns: []. User in LIQUIDATION_CALL: 0x4835C915243Ea1d094B17f5E4115e371e4880717
```

**Root Cause:**
The liquidation validation logic expected exactly 1 `COLLATERAL_BURN` event for all liquidation operations. However, during liquidations where the protocol takes a liquidation fee, the collateral aToken is transferred to the treasury/protocol via `SCALED_TOKEN_BALANCE_TRANSFER` instead of being burned.

In the failing transaction:
- logIndex 12: `SCALED_TOKEN_BALANCE_TRANSFER` on aUSDC from user 0x4835... to treasury 0x464C...
- logIndex 14: `LIQUIDATION_CALL` event

The `_extract_scaled_token_events()` method only decoded `SCALED_TOKEN_MINT` and `SCALED_TOKEN_BURN` events, completely ignoring `SCALED_TOKEN_BALANCE_TRANSFER` events. The `_create_liquidation_operation()` method only looked for `COLLATERAL_BURN` events, missing the collateral transfer that actually occurred.

**Transaction Details:**
- **Hash:** 0x621380dc92a951489f4717300d242ad2db640be2d2be5eb66e108b455cccaad2
- **Block:** 19904828
- **Type:** Liquidation (via 1inch router)
- **User:** 0x4835C915243Ea1d094B17f5E4115e371e4880717 (liquidated)
- **Liquidator:** 0x832bc12fD9889cd08f30e091f94aF4688061865A
- **Collateral Asset:** USDC (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48)
- **Debt Asset:** WETH (0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2)
- **aToken:** aUSDC (0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c)

**Key Events:**
1. logIndex 3: SCALED_TOKEN_MINT on aWETH (interest accrual)
2. logIndex 4: ReserveDataUpdated for WETH
3. logIndex 5: ReserveDataUpdated for USDC
4. logIndex 7: SCALED_TOKEN_MINT on aUSDC (interest accrual)
5. logIndex 10: SCALED_TOKEN_MINT on aUSDC (to treasury)
6. logIndex 12: **SCALED_TOKEN_BALANCE_TRANSFER** from user to treasury (liquidation fee)
7. logIndex 14: LIQUIDATION_CALL event

**Fix:**
Modified `src/degenbot/cli/aave_transaction_operations.py`:

1. **Added BalanceTransfer event decoding** (lines 519-553):
   - Added `_decode_balance_transfer_event()` method to decode `SCALED_TOKEN_BALANCE_TRANSFER` events
   - Created `COLLATERAL_TRANSFER` and `DEBT_TRANSFER` event types
   - Updated `_extract_scaled_token_events()` to include BalanceTransfer events

2. **Updated liquidation operation creation** (lines 819-840):
   - Modified `_create_liquidation_operation()` to look for both `COLLATERAL_BURN` and `COLLATERAL_TRANSFER` events
   - Falls back to collateral transfer when no burn is found

3. **Updated liquidation validation** (lines 1028-1057):
   - Modified `_validate_liquidation()` to accept either collateral burns OR collateral transfers
   - Updated error message to reflect that either event type is valid

**Code Changes:**

```python
# In _extract_scaled_token_events():
elif topic == AaveV3Event.SCALED_TOKEN_BALANCE_TRANSFER.value:
    ev = self._decode_balance_transfer_event(event)
    if ev:
        result.append(ev)

# In _create_liquidation_operation():
# Find collateral burn or transfer
collateral_burn = None
collateral_transfer = None
for ev in scaled_events:
    if ev.event["logIndex"] in assigned_indices:
        continue
    if ev.event_type == "COLLATERAL_BURN":
        if ev.user_address == user:
            collateral_burn = ev
            break
    elif ev.event_type == "COLLATERAL_TRANSFER":
        if ev.user_address == user:
            collateral_transfer = ev
            break

if collateral_burn:
    scaled_token_events.append(collateral_burn)
elif collateral_transfer:
    scaled_token_events.append(collateral_transfer)

# In _validate_liquidation():
collateral_events = [e for e in op.scaled_token_events if e.is_collateral]
if len(collateral_events) != 1:
    errors.append(
        f"Expected 1 collateral event (burn or transfer) for LIQUIDATION, got {len(collateral_events)}."
        ...
    )
```

**Key Insight:**
Aave V3 liquidations can handle collateral in two ways:
1. **Burn:** Collateral aTokens are burned from the liquidated user's position
2. **Transfer:** Collateral aTokens are transferred to the treasury (protocol fee)

The validation logic must accept either pattern. The `is_collateral` property already supports this as it checks `event_type.startswith("COLLATERAL")`, which includes both `COLLATERAL_BURN` and `COLLATERAL_TRANSFER`.

**Refactoring:**
Consider creating a more robust event categorization system:
1. Add event sub-types to distinguish between burns and transfers
2. Create helper methods like `is_collateral_burn()` and `is_collateral_transfer()`
3. Document the different liquidation patterns in the code comments
4. Add a registry of known protocol contracts (treasury, gateway, etc.) for better pattern matching

**Testing:**
- Aave update now processes block 19904828 successfully
- No validation errors for the liquidation transaction
- Collateral transfer properly matched to LIQUIDATION_CALL event

**Related Issues:**
- Report 0007: BalanceTransfer matching logic
- Report 0012: Collateral burn consumption issues
- Report 0018: BalanceTransfer to Gateway contracts
