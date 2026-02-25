# ENS (Ethereum Name Service) Reference

Commands for resolving ENS names and addresses.

## Name Resolution

### resolve_name
Perform an ENS lookup.

**Parameters:**
- `name` (string, required): The ENS name to resolve
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast resolve-name [--rpc-url <rpc>] <name>
```

**Example:**
```bash
cast resolve-name vitalik.eth
# Output: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

cast resolve-name uniswap.eth
```

## Reverse Lookup

### lookup_address
Perform an ENS reverse lookup.

**Parameters:**
- `address` (string, required): The address to look up
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast lookup-address [--rpc-url <rpc>] <address>
```

**Example:**
```bash
cast lookup-address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
# Output: vitalik.eth
```

## Namehash

### namehash
Calculate the ENS namehash of a name.

**Parameters:**
- `name` (string, required): The ENS name

**Usage:**
```bash
cast namehash <name>
```

**Example:**
```bash
cast namehash vitalik.eth
# Output: 0x6f8... (the namehash)
```

## Common ENS Names

| Name | Known Address |
|------|---------------|
| vitalik.eth | 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 |
| uniswap.eth | Varies by resolver |
| ethereum.eth | Varies |

## Notes

- ENS resolution requires an RPC connection to a node that supports ENS
- Mainnet ENS is the default; other chains may have their own ENS deployments
- Not all addresses have reverse records set up
- Some names may have multiple resolved addresses depending on the coin type
