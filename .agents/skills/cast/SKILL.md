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
| Read proxy contract implementation address | `cast implementation <contract>` |
| Query ERC20 balance | `cast erc20-token balance <token> <owner>` |
| Get transaction receipt | `cast receipt <tx_hash>` |
| Get transaction trace | `cast run <tx_hash>` |
| Get latest block number | `cast block-number` |
| Convert wei to ETH | `cast from-wei <value>` |
| ABI encode function call | `cast calldata <sig> [args...]` |

## Common Workflows

### Reading Contract Data

```bash
# Call a view function with no arguments
cast call 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 "decimals()"

# Call a view function with an argument
cast call 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 "balanceOf(address)" 0x000000000004444c5dc75cB358380D2e3dE08A90
```

### Working with ERC20 Tokens

```bash
# Get WETH (0xC02a...6Cc2) token balance for Uniswap V4 Pool Manager (0x0000...8A90)
cast erc20-token balance 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 0x000000000004444c5dc75cB358380D2e3dE08A90

# Get token metadata
cast erc20-token name 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
cast erc20-token symbol 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
cast erc20-token decimals 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
```

### Encoding and Decoding Data

```bash
# Encode function call data
cast calldata "transfer(address,uint256)" 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 1000000000000000000

# Decode transaction input
cast decode-calldata "transfer(address,uint256)" '0xa9059cbb000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000000000000000000000000000000de0b6b3a7640000'

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
- Filename: `rpc-config.json`
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
