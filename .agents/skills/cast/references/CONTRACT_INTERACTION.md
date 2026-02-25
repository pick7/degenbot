# Contract Interaction Reference

Commands for calling contract functions, sending transactions, and estimating gas.

## Calling Functions

### call
Perform a call on an account without publishing a transaction.

**Parameters:**
- `to` (string, optional): The contract address to call
- `sig` (string, optional): The function signature to call
- `args` (array of strings, optional): The arguments for the function call
- `data` (string, optional): The hex-encoded data for the call
- `block` (string, optional): The block height to query at
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `trace` (boolean, optional): Trace the execution of the call
- `value` (string, optional): The value to send with the call
- `gasLimit` (string, optional): The gas limit for the call
- `gasPrice` (string, optional): The gas price for the call
- `from` (string, optional): The sender address for the call

**Usage:**
```bash
cast call [options] [to] [sig] [args...]
```

**Examples:**
```bash
# Read a simple value
cast call 0x6B175474E89094C44Da98b954EedeAC495271d0F "name()"

# Call with arguments
cast call 0x6B175474E89094C44Da98b954EedeAC495271d0F "balanceOf(address)" 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe

# Call at a specific block
cast call --block 18000000 0x6B175474E89094C44Da98b954EedeAC495271d0F "totalSupply()"
```

## Sending Transactions

### send
Sign and publish a transaction.

**Parameters:**
- `to` (string, optional): The recipient address
- `sig` (string, optional): The function signature
- `args` (array of strings, optional): The function arguments
- `data` (string, optional): The hex-encoded transaction data
- `value` (string, optional): The value to send (in wei)
- `gasLimit` (string, optional): The gas limit
- `gasPrice` (string, optional): The gas price
- `nonce` (string, optional): The transaction nonce
- `chain` (string, optional): The chain name or EIP-155 chain ID
- `from` (string, optional): The sender address
- `ledger` (boolean, optional): Use a Ledger hardware wallet
- `trezor` (boolean, optional): Use a Trezor hardware wallet
- `privateKey` (string, optional): The private key to sign with

**Usage:**
```bash
cast send [--value <value>] [--gas-limit <limit>] [--gas-price <price>] [--nonce <nonce>] [--rpc-url <rpc>] [to] [sig] [args...]
```

**Examples:**
```bash
# Send ETH
cast send 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe --value 1ether

# Call a contract function
cast send 0x6B175474E89094C44Da98b954EedeAC495271d0F "transfer(address,uint256)" 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe 1000000000000000000

# Use hardware wallet
cast send --ledger 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe --value 0.1ether
```

### mktx
Build and sign a transaction (without publishing).

**Parameters:**
- `to` (string, optional): The recipient address
- `sig` (string, optional): The function signature
- `args` (array of strings, optional): The function arguments
- `data` (string, optional): The hex-encoded transaction data
- `value` (string, optional): The value to send (in wei)
- `gasLimit` (string, optional): The gas limit
- `gasPrice` (string, optional): The gas price
- `nonce` (string, optional): The transaction nonce
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast mktx [--value <value>] [--gas-limit <limit>] [--gas-price <price>] [--nonce <nonce>] [to] [sig] [args...]
```

### publish
Publish a raw transaction to the network.

**Parameters:**
- `rawTx` (string, required): The raw signed transaction
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast publish [--rpc-url <rpc>] <rawTx>
```

## Gas and Access Lists

### estimate
Estimate the gas cost of a transaction.

**Parameters:**
- `to` (string, optional): The recipient address
- `sig` (string, optional): The function signature
- `args` (array of strings, optional): The function arguments
- `data` (string, optional): The hex-encoded transaction data
- `value` (string, optional): The value to send
- `from` (string, optional): The sender address
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast estimate [--value <value>] [--from <from>] [--rpc-url <rpc>] [to] [sig] [args...]
```

### access_list
Create an access list for a transaction.

**Parameters:**
- `to` (string, optional): The recipient address
- `sig` (string, optional): The function signature
- `args` (array of strings, optional): The function arguments
- `data` (string, optional): The hex-encoded transaction data
- `value` (string, optional): The value to send
- `from` (string, optional): The sender address
- `chain` (string, optional): The chain name or EIP-155 chain ID

**Usage:**
```bash
cast access-list [--value <value>] [--from <from>] [--rpc-url <rpc>] [to] [sig] [args...]
```

## EIP-7702 (Account Abstraction)

### recover_authority
Recover an EIP-7702 authority from an Authorization JSON string.

**Parameters:**
- `auth` (string, required): The authorization JSON string

**Usage:**
```bash
cast recover-authority <auth>
```
