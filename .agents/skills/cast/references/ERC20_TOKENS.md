# ERC20 Tokens Reference

Commands for querying ERC20 token balances, allowances, and metadata.

## Token Operations

### erc20_token
ERC20 token operations (balance, allowance, name, symbol, decimals, total-supply).

**Parameters:**
- `subcommand` (string, required): The ERC20 subcommand (balance, allowance, name, symbol, decimals, total-supply)

**Usage:**
```bash
cast erc20-token <subcommand> [args...]
```

### erc20_balance
Query ERC20 token balance.

**Parameters:**
- `token` (string, required): The ERC20 token contract address
- `owner` (string, required): The owner to query balance for
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `block` (string, optional): The block height to query at

**Usage:**
```bash
cast erc20-token balance [--block <block>] [--rpc-url <rpc>] <token> <owner>
```

**Example:**
```bash
# Check USDC balance
cast erc20-token balance 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe
```

### erc20_allowance
Query ERC20 token allowance.

**Parameters:**
- `token` (string, required): The ERC20 token contract address
- `owner` (string, required): The owner address
- `spender` (string, required): The spender address
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `block` (string, optional): The block height to query at

**Usage:**
```bash
cast erc20-token allowance [--block <block>] [--rpc-url <rpc>] <token> <owner> <spender>
```

**Example:**
```bash
# Check Uniswap router allowance for a token
cast erc20-token allowance 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D
```

## Token Metadata

### erc20_name
Query ERC20 token name.

**Parameters:**
- `token` (string, required): The ERC20 token contract address
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `block` (string, optional): The block height to query at

**Usage:**
```bash
cast erc20-token name [--block <block>] [--rpc-url <rpc>] <token>
```

### erc20_symbol
Query ERC20 token symbol.

**Parameters:**
- `token` (string, required): The ERC20 token contract address
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `block` (string, optional): The block height to query at

**Usage:**
```bash
cast erc20-token symbol [--block <block>] [--rpc-url <rpc>] <token>
```

### erc20_decimals
Query ERC20 token decimals.

**Parameters:**
- `token` (string, required): The ERC20 token contract address
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `block` (string, optional): The block height to query at

**Usage:**
```bash
cast erc20-token decimals [--block <block>] [--rpc-url <rpc>] <token>
```

### erc20_total_supply
Query ERC20 token total supply.

**Parameters:**
- `token` (string, required): The ERC20 token contract address
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `block` (string, optional): The block height to query at

**Usage:**
```bash
cast erc20-token total-supply [--block <block>] [--rpc-url <rpc>] <token>
```

## Common Token Addresses (Mainnet)

| Token | Address |
|-------|---------|
| WETH | 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 |
| USDC | 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e |
| USDT | 0xdAC17F958D2ee523a2206206994597C13D831ec7 |
| DAI | 0x6B175474E89094C44Da98b954EedeAC495271d0F |
| WBTC | 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599 |

## Example: Get Full Token Info

```bash
TOKEN=0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e

echo "Name: $(cast erc20-token name $TOKEN)"
echo "Symbol: $(cast erc20-token symbol $TOKEN)"
echo "Decimals: $(cast erc20-token decimals $TOKEN)"
echo "Total Supply: $(cast erc20-token total-supply $TOKEN)"
```
