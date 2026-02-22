# Issue: GHO BORROW Validation Fails Due to Incorrect Token Address Check

## Date
2025-02-21

## Symptom
```
Transaction validation failed:
Operation 0 (BORROW): Expected 1 debt mint for BORROW, got 0
```

## Root Cause
The `_create_borrow_operation()` method (and similar methods for REPAY and LIQUIDATION) incorrectly compared the reserve address from Pool events against `self.gho_token_address`, which was set to the GHO Variable Debt Token address (0x786dbff...) instead of the GHO Token address (0x40d16f...).

When processing a GHO borrow transaction:
- The BORROW event's `reserve` field contains the GHO Token address (0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f)
- The code compared this against `self.gho_token_address` which was the Variable Debt Token (0x786dbff3f1292ae8f92ea68cf93c30b34b1ed04b)
- Since these addresses don't match, `is_gho` was always `False`
- The code then looked for `DEBT_MINT` events instead of `GHO_DEBT_MINT` events
- The SCALED_TOKEN_MINT was correctly classified as `GHO_DEBT_MINT` (since it occurred at the Variable Debt Token address)
- The mismatch caused validation to fail

## Transaction Details

- **Hash**: `0x97858017903ffbe793a4c5789293f170719f5a9d918db52e31e7f74e1129dd75`
- **Block**: 17699253
- **Chain**: Ethereum mainnet (chain_id: 1)
- **Function**: `borrow(address,uint256,uint256,uint16,address)`
- **User**: `0xB9CDf9c22F204118Af35D3293FE57A356Dd9c8C8`
- **Asset (Reserve)**: GHO (`0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f`)
- **Variable Debt Token**: `0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B`

### Event Flow

| LogIndex | Event | Contract | Description |
|----------|-------|----------|-------------|
| 338 | Transfer | variableDebtEthGHO | Underlying transfer |
| 339 | ScaledTokenMint | variableDebtEthGHO | Mint debt tokens (GHO_DEBT_MINT) |
| 340 | ReserveDataUpdated | Aave Pool | Reserve rate update |
| 341 | Transfer | GHO Token | Transfer borrowed GHO |
| 342 | Event | GHO Token | DiscountPercentUpdated |
| 343 | Borrow | Aave Pool | BORROW event emitted |

## Fix

**File**: `src/degenbot/cli/aave_transaction_operations.py`

### Changes Made

1. **Added GHO_TOKEN_ADDRESS constant** (line 77):
```python
# GHO Token Address (Ethereum Mainnet)
GHO_TOKEN_ADDRESS = get_checksum_address("0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f")
```

2. **Fixed `_create_borrow_operation()`** (line 644):
```python
# Before:
is_gho = reserve == self.gho_token_address

# After:
is_gho = reserve == GHO_TOKEN_ADDRESS
```

3. **Fixed `_create_repay_operation()`** (line 685):
```python
# Before:
is_gho = reserve == self.gho_token_address

# After:
is_gho = reserve == GHO_TOKEN_ADDRESS
```

4. **Fixed `_create_liquidation_operation()`** (line 746):
```python
# Before:
is_gho = debt_asset == self.gho_token_address

# After:
is_gho = debt_asset == GHO_TOKEN_ADDRESS
```

## Key Insight

When checking if a reserve/asset is GHO, compare against the **GHO Token address** (the underlying asset), not the **GHO Variable Debt Token address** (the debt token contract). Pool events reference the underlying asset address in their `reserve` field, while scaled token events occur at the debt token contract address.

## Refactoring

1. **Rename `gho_token_address` parameter**: Consider renaming the constructor parameter from `gho_token_address` to `gho_variable_debt_token_address` to clarify its purpose.

2. **Consolidate GHO constants**: Move all GHO-related addresses to a dedicated constants module or configuration file to prevent similar confusion.

3. **Add address validation**: Add runtime checks to ensure the GHO token address and variable debt token address are different (they should be), preventing silent failures from swapped addresses.

4. **Document address semantics**: Add clear documentation distinguishing between:
   - Underlying asset addresses (e.g., GHO Token)
   - Debt token contract addresses (e.g., variableDebtEthGHO)
   - AToken contract addresses
