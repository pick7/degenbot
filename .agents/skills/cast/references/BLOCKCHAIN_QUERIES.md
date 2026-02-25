# Blockchain Queries Reference

Commands for querying blockchain state, accounts, blocks, and transactions.

## Account Information

### balance
Get the balance of an account in wei.

**Parameters:**
- `who` (string, required): The account to get the balance for
- `block` (string, optional): The block height to query at
- `ether` (boolean, optional): Convert the balance to ether
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `erc20` (string, optional): The ERC20 token address

**Usage:**
```bash
cast balance [--block <block>] [--ether] [--erc20 <token>] [--rpc-url <rpc>] <who>
```

### nonce
Get the nonce for an account.

**Parameters:**
- `who` (string, required): The account address
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast nonce [--block <block>] [--rpc-url <rpc>] <who>
```

### codehash
Get the codehash for an account.

**Parameters:**
- `who` (string, required): The account address
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast codehash [--block <block>] [--rpc-url <rpc>] <who>
```

### codesize
Get the runtime bytecode size of a contract.

**Parameters:**
- `who` (string, required): The contract address
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast codesize [--block <block>] [--rpc-url <rpc>] <who>
```

## Chain Information

### chain
Get the symbolic name of the current chain.

**Parameters:**
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast chain [--rpc-url <rpc>]
```

### chain_id
Get the Ethereum chain ID.

**Parameters:**
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast chain-id [--rpc-url <rpc>]
```

### client
Get the current client version.

**Parameters:**
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast client [--rpc-url <rpc>]
```

### gas_price
Get the current gas price.

**Parameters:**
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast gas-price [--rpc-url <rpc>]
```

## Block Information

### age
Get the timestamp of a block.

**Parameters:**
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast age [--rpc-url <rpc>] [block]
```

### base_fee
Get the basefee of a block.

**Parameters:**
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast base-fee [--rpc-url <rpc>] [block]
```

### block_number
Get the latest block number.

**Parameters:**
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast block-number [--rpc-url <rpc>]
```

### block
Get information about a block.

**Parameters:**
- `block` (string, optional): The block height to query at
- `raw` (boolean, optional): Print the block header as raw RLP bytes
- `full` (boolean, optional): Print the full block information
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast block [--raw] [--full] [--rpc-url <rpc>] [block]
```

### find_block
Get the block number closest to the provided timestamp.

**Parameters:**
- `timestamp` (string, required): The UNIX timestamp to search for, in seconds
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `insecure` (boolean, optional): Allow insecure RPC connections

**Usage:**
```bash
cast find-block [--rpc-url <rpc>] [--insecure] <timestamp>
```

## Transaction Information

### receipt
Get the receipt for a transaction.

**Parameters:**
- `txHash` (string, required): The transaction hash
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast receipt --async [--rpc-url <rpc>] <txHash>
```

### tx
Get information about a transaction.

**Parameters:**
- `txHash` (string, required): The transaction hash
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast tx [--rpc-url <rpc>] <txHash>
```

### run
Runs a published transaction in a local environment and prints the trace.

**Parameters:**
- `txHash` (string, required): The transaction hash
- `decodeInternal` (boolean, optional): Whether to identify internal functions in traces
- `tracePrinter` (boolean, optional): Print out opcode traces
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast run [--decode-internal] [--trace-printer] [--rpc-url <rpc>] <txHash>
```

## Logs & Events

### logs
Get logs by signature or topic.

**Parameters:**
- `sigOrTopic` (string, optional): The signature of the event or topic to filter by
- `topicsOrArgs` (array of strings, optional): Indexed fields to filter by or remaining topics
- `fromBlock` (string, optional): The block height to start query at
- `toBlock` (string, optional): The block height to stop query at
- `address` (string, optional): The contract address to filter on
- `etherscanApiKey` (string, optional): The Etherscan (or equivalent) API key
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast logs [--from-block <block>] [--to-block <block>] [--address <addr>] [--etherscan-api-key <key>] [--rpc-url <rpc>] [sigOrTopic] [topicsOrArgs...]
```

## Transaction Pool

### tx_pool
Inspect the TxPool of a node.

**Parameters:**
- `action` (string, optional): The action to perform (content, inspect, status)
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast tx-pool [--rpc-url <rpc>] [action]
```
