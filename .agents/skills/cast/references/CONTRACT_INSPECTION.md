# Contract Inspection Reference

Commands for inspecting contract code, storage, and deployment information.

## Proxy and Implementation

### admin
Fetch the EIP-1967 admin account.

**Parameters:**
- `who` (string, required): The address from which the admin account will be fetched
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast admin [--block <block>] [--rpc-url <rpc>] <who>
```

### implementation
Fetch the EIP-1967 implementation address for a contract.

**Parameters:**
- `who` (string, required): The address for which the implementation will be fetched
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast implementation [--block <block>] [--rpc-url <rpc>] <who>
```

## Bytecode and Source

### code
Get the runtime bytecode of a contract.

**Parameters:**
- `who` (string, required): The contract address
- `block` (string, optional): The block height to query at
- `disassemble` (boolean, optional): Disassemble bytecodes
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast code [--block <block>] [--disassemble] [--rpc-url <rpc>] <who>
```

### source
Get the source code of a contract from a block explorer.

**Parameters:**
- `address` (string, required): The contract address
- `flatten` (boolean, optional): Flatten the source code

**Usage:**
```bash
cast source [--flatten] <address>
```

### disassemble
Disassemble hex-encoded bytecode into a human-readable representation.

**Parameters:**
- `bytecode` (string, required): The hex-encoded bytecode

**Usage:**
```bash
cast disassemble <bytecode>
```

## Storage

### storage
Get the raw value of a contract's storage slot.

**Parameters:**
- `address` (string, required): The contract address
- `baseSlot` (string, optional): The base storage slot
- `offset` (string, optional): The offset from the base slot

**Usage:**
```bash
cast storage <address> [baseSlot] [offset]
```

### storage_root
Get the storage root for an account.

**Parameters:**
- `who` (string, required): The account address
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast storage-root [--block <block>] [--rpc-url <rpc>] <who>
```

### proof
Generate a storage proof for a given storage slot.

**Parameters:**
- `address` (string, required): The contract address
- `slots` (array of strings, required): The storage slots to prove
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast proof [--block <block>] [--rpc-url <rpc>] <address> <slots...>
```

### index
Compute the storage slot for an entry in a mapping.

**Parameters:**
- `keyType` (string, required): The mapping key type
- `key` (string, required): The mapping key
- `slotNumber` (string, required): The storage slot of the mapping

**Usage:**
```bash
cast index <keyType> <key> <slotNumber>
```

**Example:**
```bash
# Compute storage slot for balances[address] in an ERC20
# Assuming balances is at slot 2
cast index address 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe 2
```

### index_erc7201
Compute storage slots as specified by ERC-7201 (Namespaced Storage Layout).

**Parameters:**
- `id` (string, required): The namespace ID

**Usage:**
```bash
cast index-erc7201 <id>
```

## Contract Analysis

### selectors
Extract function selectors and arguments from bytecode.

**Parameters:**
- `bytecode` (string, required): The contract bytecode

**Usage:**
```bash
cast selectors <bytecode>
```

### interface
Generate a Solidity interface from a given ABI.

**Parameters:**
- `abiOrPath` (string, required): The ABI string or path to ABI file

**Usage:**
```bash
cast interface <abiOrPath>
```

### bind
Generate a Rust binding from a given ABI.

**Parameters:**
- `abiOrPath` (string, required): The ABI string or path to ABI file

**Usage:**
```bash
cast bind <abiOrPath>
```

## Deployment

### create2
Generate a deterministic contract address using CREATE2.

**Parameters:**
- `deployer` (string, required): The deployer address
- `salt` (string, required): The salt value
- `initCode` (string, required): The contract init code

**Usage:**
```bash
cast create2 <deployer> <salt> <initCode>
```

### compute_address
Compute the contract address from a given nonce and deployer address.

**Parameters:**
- `deployer` (string, required): The deployer address
- `nonce` (string, optional): The deployer nonce (defaults to current nonce)

**Usage:**
```bash
cast compute-address [--nonce <nonce>] <deployer>
```

### constructor_args
Display constructor arguments used for contract initialization.

**Parameters:**
- `address` (string, required): The contract address
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast constructor-args [--rpc-url <rpc>] <address>
```

### creation_code
Download a contract creation code from Etherscan and RPC.

**Parameters:**
- `address` (string, required): The contract address
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast creation-code [--rpc-url <rpc>] <address>
```

### artifact
Generate an artifact file that can be used to deploy a contract locally.

**Parameters:**
- `bytecode` (string, required): The contract bytecode

**Usage:**
```bash
cast artifact <bytecode>
```
