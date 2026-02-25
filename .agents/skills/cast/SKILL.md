---
name: cast
description: Interact with Ethereum and EVM-compatible blockchains using Foundry's cast command. Use this skill to query blockchain state, inspect contracts and transactions, encode/decode ABI data, check ERC20 token balances, and perform low-level blockchain operations.
---

# Cast Blockchain Tools

Tools for interacting with Ethereum and EVM-compatible blockchains using Foundry's `cast` command.

## Quick Start

Common operations you can perform with cast:

| Task | Command |
|------|---------|
| Check ETH balance | `cast balance <address> --ether` |
| Read contract state | `cast call <contract> <function_sig>` |
| Send a transaction | `cast send <to> <sig> [args...]` |
| Query ERC20 balance | `cast erc20-token balance <token> <owner>` |
| Get transaction receipt | `cast receipt <tx_hash>` |
| Get latest block number | `cast block-number` |
| Convert wei to ETH | `cast from-wei <value>` |
| ABI encode function call | `cast calldata <sig> [args...]` |

## Common Workflows

### Reading Contract Data

```bash
# Get the total supply of a token
cast call 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e "totalSupply()"

# Check balance of a specific address
cast call 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e "balanceOf(address)" 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe
```

### Sending Transactions

```bash
# Send ETH to an address
cast send 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe --value 0.1ether

# Call a contract function that modifies state
cast send 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e "transfer(address,uint256)" 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe 1000000000000000000
```

### Working with ERC20 Tokens

```bash
# Get token balance
cast erc20-token balance 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe

# Get token metadata
cast erc20-token name 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e
cast erc20-token symbol 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e
cast erc20-token decimals 0xA0b86a33E6441E6C7D3D4B4f6c7E8F9a0B1c2D3e
```

### Encoding and Decoding Data

```bash
# Encode function call data
cast calldata "transfer(address,uint256)" 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe 1000000000000000000

# Decode transaction input
cast decode-calldata "transfer(address,uint256)" 0xa9059cbb000000000000000000000000...

# Get function selector
cast sig "transfer(address,uint256)"
```

## Tool Categories

The cast command provides many subcommands organized by purpose:

| Category | Description | See Also |
|----------|-------------|----------|
| **Blockchain Queries** | Query accounts, balances, nonces, blocks, transactions | [references/BLOCKCHAIN_QUERIES.md](references/BLOCKCHAIN_QUERIES.md) |
| **Contract Interaction** | Call functions, send transactions, estimate gas | [references/CONTRACT_INTERACTION.md](references/CONTRACT_INTERACTION.md) |
| **Contract Inspection** | Get bytecode, source, storage, implementation | [references/CONTRACT_INSPECTION.md](references/CONTRACT_INSPECTION.md) |
| **ABI Operations** | Encode/decode calldata, work with signatures | [references/ABI_OPERATIONS.md](references/ABI_OPERATIONS.md) |
| **ERC20 Tokens** | Query token balances, allowances, metadata | [references/ERC20_TOKENS.md](references/ERC20_TOKENS.md) |
| **Data Conversion** | Convert units, formats, and encodings | [references/DATA_CONVERSION.md](references/DATA_CONVERSION.md) |
| **ENS** | Resolve names and addresses | [references/ENS.md](references/ENS.md) |
| **Utilities** | Various helper functions | [references/UTILITIES.md](references/UTILITIES.md) |

## RPC URL Configuration

When a `cast` subcommand requires an RPC URL (e.g., for blockchain queries or contract interactions), determine the appropriate URL as follows:

**Lookup the RPC URL in the config file:**
- File location: `.opencode/rpc-config.json`
- This JSON file maps chain names and IDs to their RPC endpoints

**Example config structure:**
```json
{
    "ethereum": "http://127.0.0.1:8545",
    "mainnet": "http://127.0.0.1:8545",
    "1": "http://127.0.0.1:8545"
}
```

**Usage:** Match the chain identifier (name or chain ID) to the corresponding RPC URL in the config file, then pass it to commands using `--rpc-url <url>`.

## Global Options

Most commands accept these common options:

- `--rpc-url <url>` - RPC endpoint URL (see RPC URL Configuration above)
- `--chain <name_or_id>` - Chain name (ethereum, polygon) or EIP-155 chain ID
- `--block <number>` - Block height to query at

## Notes

- When `chain` is not specified, commands default to Ethereum mainnet (chain ID 1)
- Block parameters can be block numbers or tags: `earliest`, `finalized`, `safe`, `latest`, `pending`
- Use `--help` with any cast subcommand for detailed options

## Full Reference

For detailed documentation on all cast subcommands, see the reference files in the [references/](references/) directory.
