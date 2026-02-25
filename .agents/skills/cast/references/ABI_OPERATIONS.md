# ABI Operations Reference

Commands for encoding/decoding ABI data, working with function signatures, and calldata.

## ABI Encoding

### abi_encode
ABI encode the given function argument, excluding the selector.

**Parameters:**
- `sig` (string, required): The function signature
- `args` (array of strings, required): The arguments of the function
- `packed` (boolean, optional): Whether to use packed encoding

**Usage:**
```bash
cast abi-encode <sig> [args...] [--packed]
```

**Example:**
```bash
cast abi-encode "address,uint256" 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe 1000000000000000000
```

### abi_encode_event
ABI encode an event and its arguments to generate topics and data.

**Parameters:**
- `sig` (string, required): The event signature
- `args` (array of strings, required): The arguments of the event

**Usage:**
```bash
cast abi-encode-event <sig> [args...]
```

### calldata
ABI-encode a function with arguments.

**Parameters:**
- `sig` (string, required): The function signature
- `args` (array of strings, optional): The arguments to encode
- `file` (string, optional): The file containing the ABI

**Usage:**
```bash
cast calldata [--file <file>] <sig> [args...]
```

**Example:**
```bash
cast calldata "transfer(address,uint256)" 0x742d35Cc6634C0532925a3b844Bc9e7595f6dEe 1000000000000000000
```

## ABI Decoding

### decode_abi
Decode ABI-encoded input or output data.

**Parameters:**
- `sig` (string, required): The function signature in the format `<name>(<in-types>)(<out-types>)`
- `calldata` (string, required): The ABI-encoded calldata
- `input` (boolean, optional): Decode input data instead of output data

**Usage:**
```bash
cast decode-abi [--input] <sig> <calldata>
```

### decode_calldata
Decode ABI-encoded input data.

**Parameters:**
- `sig` (string, required): The function signature
- `calldata` (string, optional): The ABI-encoded calldata
- `file` (string, optional): Load ABI-encoded calldata from a file instead

**Usage:**
```bash
cast decode-calldata [--file <file>] <sig> [calldata]
```

### decode_error
Decode custom error data.

**Parameters:**
- `data` (string, required): The error data to decode
- `sig` (string, optional): The error signature

**Usage:**
```bash
cast decode-error [--sig <sig>] <data>
```

### decode_event
Decode event data.

**Parameters:**
- `data` (string, required): The event data to decode
- `sig` (string, optional): The event signature

**Usage:**
```bash
cast decode-event [--sig <sig>] <data>
```

### decode_string
Decode ABI-encoded string.

**Parameters:**
- `data` (string, required): The ABI-encoded string

**Usage:**
```bash
cast decode-string <data>
```

### decode_transaction
Decode a raw signed EIP-2718 typed transaction.

**Parameters:**
- `tx` (string, optional): The raw signed transaction to decode

**Usage:**
```bash
cast decode-transaction [tx]
```

## Function Signatures

### four_byte
Get the function signature for the given selector.

**Parameters:**
- `selector` (string, required): The function selector (4 bytes)

**Usage:**
```bash
cast 4byte <selector>
```

**Example:**
```bash
cast 4byte 0xa9059cbb
```

### four_byte_calldata
Decode ABI-encoded calldata using 4byte.directory.

**Parameters:**
- `calldata` (string, required): The ABI-encoded calldata

**Usage:**
```bash
cast 4byte-calldata <calldata>
```

### four_byte_event
Get the event signature for a given topic0.

**Parameters:**
- `topic0` (string, required): Topic 0 (event signature hash)

**Usage:**
```bash
cast 4byte-event <topic0>
```

### sig
Get the selector for a function.

**Parameters:**
- `sig` (string, optional): The function signature, e.g. `transfer(address,uint256)`
- `optimize` (string, optional): Optimize signature to contain provided amount of leading zeroes in selector

**Usage:**
```bash
cast sig [sig] [optimize]
```

**Example:**
```bash
cast sig "transfer(address,uint256)"
```

### sig_event
Generate event signatures from event string.

**Parameters:**
- `eventString` (string, optional): The event string to generate a signature for

**Usage:**
```bash
cast sig-event [eventString]
```

## Calldata Utilities

### pretty_calldata
Pretty print calldata.

**Parameters:**
- `calldata` (string, optional): The calldata to pretty print

**Usage:**
```bash
cast pretty-calldata [calldata]
```

### upload_signature
Upload the given signatures to https://openchain.xyz.

**Parameters:**
- `signatures` (array of strings, required): The signatures to upload

**Usage:**
```bash
cast upload-signature <signatures...>
```
