**Issue:** Burn Events Decoded as UNKNOWN_BURN Instead of COLLATERAL_BURN

**Date:** 2026-02-21

**Symptom:**
```
Transaction validation failed:
Operation 0 (WITHDRAW): Expected 1 collateral burn for WITHDRAW, got 0
```

**Root Cause:**
The `_decode_burn_event` method in `TransactionOperationsParser` set `event_type = "UNKNOWN_BURN"` for all non-GHO burn events. However, the `_create_withdraw_operation` method looked for events with `event_type == "COLLATERAL_BURN"` to validate WITHDRAW operations. Since burn events were never classified as "COLLATERAL_BURN", they were never matched to WITHDRAW operations.

**Transaction Details:**
- **Hash:** 0x4a88a8c6a43b5df2ee59ebcf266225fbc5b876f202009422f0f9d05cc4915f35
- **Block:** 16496928
- **Type:** WITHDRAW
- **User:** 0x872fBcb1B582e8Cd0D0DD4327fBFa0B4C2730995 (ParaSwap Delta Proxy)
- **Asset:** WETH (0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2)
- **aToken:** aEthWETH (0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8)

**Event Sequence:**
1. `[111]` SCALED_TOKEN_BURN (aEthWETH) - Collateral burn for withdraw
2. `[113]` WITHDRAW (Pool) - Pool event requiring collateral burn validation

**Fix:**
Modified `TransactionOperationsParser` to accept a `token_type_mapping` parameter that maps token addresses to their types ("aToken" or "vToken"). Updated both `_decode_burn_event` and `_decode_mint_event` to use this mapping to set the correct event type:

**Code location:** `src/degenbot/cli/aave_transaction_operations.py`

```python
# In __init__
def __init__(
    self,
    gho_token_address: ChecksumAddress | None = None,
    token_type_mapping: dict[ChecksumAddress, str] | None = None,
):
    self.token_type_mapping = token_type_mapping or {}

# In _decode_burn_event
token_type = self.token_type_mapping.get(token_address)
if token_type == "aToken":
    event_type = "COLLATERAL_BURN"
elif token_type == "vToken":
    event_type = "DEBT_BURN"
```

**Code location:** `src/degenbot/cli/aave.py`

```python
# Build token type mapping before parsing
token_type_mapping: dict[ChecksumAddress, str] = {}
for asset in market.assets:
    if asset.a_token:
        token_type_mapping[get_checksum_address(asset.a_token.address)] = "aToken"
    if asset.v_token:
        token_type_mapping[get_checksum_address(asset.v_token.address)] = "vToken"

parser = TransactionOperationsParser(
    token_type_mapping=token_type_mapping,
)
```

**Key Insight:**
The parser needed contextual information about token types to properly classify events. Without this context, it defaulted to generic "UNKNOWN" types that couldn't be matched to specific operations. This is a common pattern when parsing blockchain events - you often need external context (like database state) to properly interpret raw event data.

**Refactoring:**
Consider refactoring the `ScaledTokenEvent` class to include a reference to the asset or token type directly, rather than relying on string event types. This would make the type system more robust and prevent similar classification errors. Additionally, the parser could potentially be made more testable by allowing injection of token metadata rather than requiring database access.
