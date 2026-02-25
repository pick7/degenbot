# Utilities Reference

Miscellaneous utility commands for various blockchain operations.

## Hashing

### keccak
Hash arbitrary data using Keccak-256.

**Parameters:**
- `data` (string, optional): The data to hash

**Usage:**
```bash
cast keccak [data]
```

**Example:**
```bash
cast keccak "hello world"
```

### hash_message
Hash a message according to EIP-191.

**Parameters:**
- `message` (string, required): The message to hash

**Usage:**
```bash
cast hash-message <message>
```

## Bitwise Operations

### shl
Perform a left shifting operation.

**Parameters:**
- `value` (string, required): The value to shift
- `bits` (string, required): The number of bits to shift

**Usage:**
```bash
cast shl <value> <bits>
```

**Example:**
```bash
cast shl 1 8
# Output: 256
```

### shr
Perform a right shifting operation.

**Parameters:**
- `value` (string, required): The value to shift
- `bits` (string, required): The number of bits to shift

**Usage:**
```bash
cast shr <value> <bits>
```

**Example:**
```bash
cast shr 256 8
# Output: 1
```

## RPC Operations

### rpc
Perform a raw JSON-RPC request.

**Parameters:**
- `method` (string, required): RPC method name
- `params` (array of strings, optional): RPC parameters
- `raw` (boolean, optional): Send raw JSON parameters
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast rpc [--raw] [--rpc-url <rpc>] <method> [params...]
```

**Example:**
```bash
cast rpc eth_blockNumber
cast rpc eth_getBalance 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe latest
```

## Hex Utilities

### concat_hex
Concatenate hex strings.

**Parameters:**
- `data` (array of strings, optional): The data to concatenate

**Usage:**
```bash
cast concat-hex [data...]
```

**Example:**
```bash
cast concat-hex 0x12 0x34 0x56
# Output: 0x123456
```

## Wallet Management

### wallet
Wallet management utilities (sign, verify, import, etc.).

**Parameters:**
- `subcommand` (string, required): The wallet subcommand (address, sign, verify, import, etc.)

**Usage:**
```bash
cast wallet <subcommand> [args...]
```

**Example:**
```bash
# Get wallet address
cast wallet address

# Sign a message
cast wallet sign --message "hello"

# Verify a signature
cast wallet verify --address <addr> --message "hello" <sig>
```

## Shell Completions

### completions
Generate shell completions script.

**Parameters:**
- `shell` (string, required): The shell to generate completions for (bash, zsh, fish, powershell, elvish)

**Usage:**
```bash
cast completions <shell>
```

**Example:**
```bash
cast completions bash > /etc/bash_completion.d/cast
```

## Constants

### address_zero
Print the zero address.

**Usage:**
```bash
cast address-zero
# Output: 0x0000000000000000000000000000000000000000
```

### hash_zero
Print the zero hash.

**Usage:**
```bash
cast hash-zero
# Output: 0x0000000000000000000000000000000000000000000000000000000000000000
```

### max_int
Print the maximum value of the given integer type.

**Parameters:**
- `type` (string, required): The integer type (e.g., int256)

**Usage:**
```bash
cast max-int <type>
```

**Example:**
```bash
cast max-int int256
```

### min_int
Print the minimum value of the given integer type.

**Parameters:**
- `type` (string, required): The integer type (e.g., int256)

**Usage:**
```bash
cast min-int <type>
```

### max_uint
Print the maximum value of the given unsigned integer type.

**Parameters:**
- `type` (string, required): The unsigned integer type (e.g., uint256)

**Usage:**
```bash
cast max-uint <type>
```

**Example:**
```bash
cast max-uint uint256
```

## Special Purpose

### da_estimate
Estimate the data availability size of a given opstack block.

**Parameters:**
- `block` (string, required): The block number
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast da-estimate [--rpc-url <rpc>] <block>
```

### b2e_payload
Convert Beacon payload to execution payload.

**Parameters:**
- `payload` (string, required): The beacon payload

**Usage:**
```bash
cast b2e-payload <payload>
```
