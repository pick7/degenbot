# Data Conversion Reference

Commands for converting between different units, formats, and encodings.

## Unit Conversions (ETH)

### from_wei
Convert wei into an ETH amount.

**Parameters:**
- `value` (string, required): The value in wei
- `unit` (string, optional): The output unit (ether, gwei, wei)

**Usage:**
```bash
cast from-wei [unit] <value>
```

**Example:**
```bash
cast from-wei 1000000000000000000
# Output: 1
cast from-wei gwei 1000000000
# Output: 1
```

### to_wei
Convert an ETH amount to wei.

**Parameters:**
- `value` (string, required): The value to convert
- `unit` (string, optional): The input unit (ether, gwei, wei)

**Usage:**
```bash
cast to-wei [unit] <value>
```

**Example:**
```bash
cast to-wei 1ether
# Output: 1000000000000000000
cast to-wei gwei 1
# Output: 1000000000
```

### to_unit
Convert an ETH amount into another unit (ether, gwei or wei).

**Parameters:**
- `value` (string, required): The value to convert
- `unit` (string, required): The target unit

**Usage:**
```bash
cast to-unit <value> <unit>
```

## Fixed Point Conversions

### from_fixed_point
Convert a fixed point number into an integer.

**Parameters:**
- `decimals` (string, required): The number of decimals
- `value` (string, required): The fixed point value

**Usage:**
```bash
cast from-fixed-point <decimals> <value>
```

**Example:**
```bash
cast from-fixed-point 6 1000000
# Output: 1
```

### to_fixed_point
Convert an integer into a fixed point number.

**Parameters:**
- `decimals` (string, required): The number of decimals
- `value` (string, required): The integer value

**Usage:**
```bash
cast to-fixed-point <decimals> <value>
```

**Example:**
```bash
cast to-fixed-point 6 1
# Output: 1000000
```

### format_units
Format a number from smallest unit to decimal with arbitrary decimals.

**Parameters:**
- `decimals` (string, required): The number of decimals
- `value` (string, required): The value to format

**Usage:**
```bash
cast format-units <decimals> <value>
```

**Example:**
```bash
cast format-units 6 1000000
# Output: 1.000000
```

### parse_units
Convert a number from decimal to smallest unit with arbitrary decimals.

**Parameters:**
- `decimals` (string, required): The number of decimals
- `value` (string, required): The value to parse

**Usage:**
```bash
cast parse-units <decimals> <value>
```

**Example:**
```bash
cast parse-units 6 1
# Output: 1000000
```

## Text and Hex Conversions

### from_utf8
Convert UTF8 text to hex.

**Parameters:**
- `text` (string, required): The text to convert

**Usage:**
```bash
cast from-utf8 <text>
```

**Example:**
```bash
cast from-utf8 "Hello World"
# Output: 0x48656c6c6f20576f726c64
```

### to_utf8
Convert hex data to a UTF-8 string.

**Parameters:**
- `hex` (string, required): The hex data to convert

**Usage:**
```bash
cast to-utf8 <hex>
```

### to_ascii
Convert hex data to an ASCII string.

**Parameters:**
- `hex` (string, required): The hex data to convert

**Usage:**
```bash
cast to-ascii <hex>
```

### from_bin
Convert binary data into hex data.

**Parameters:**
- `binary` (string, required): The binary data to convert

**Usage:**
```bash
cast from-bin <binary>
```

## Numeric Conversions

### to_base
Convert a number from one base to another.

**Parameters:**
- `value` (string, required): The value to convert
- `from` (string, required): The input base
- `to` (string, required): The output base

**Usage:**
```bash
cast to-base <value> <from> <to>
```

**Example:**
```bash
cast to-base 255 10 16
# Output: 0xff
```

### to_dec
Convert a number to decimal.

**Parameters:**
- `value` (string, required): The value to convert
- `base` (string, optional): The input base (default: 16)

**Usage:**
```bash
cast to-dec [--base <base>] <value>
```

**Example:**
```bash
cast to-dec 0xff
# Output: 255
cast to-dec --base 2 11111111
# Output: 255
```

### to_hex
Convert a number to hexadecimal.

**Parameters:**
- `value` (string, required): The value to convert
- `base` (string, optional): The input base (default: 10)

**Usage:**
```bash
cast to-hex [--base <base>] <value>
```

**Example:**
```bash
cast to-hex 255
# Output: 0xff
cast to-hex --base 2 11111111
# Output: 0xff
```

## Ethereum Types

### to_int256
Convert a number to a hex-encoded int256.

**Parameters:**
- `value` (string, required): The value to convert

**Usage:**
```bash
cast to-int256 <value>
```

### to_uint256
Convert a number to a hex-encoded uint256.

**Parameters:**
- `value` (string, required): The value to convert

**Usage:**
```bash
cast to-uint256 <value>
```

### to_bytes32
Right-pads hex data to 32 bytes.

**Parameters:**
- `value` (string, required): The value to pad

**Usage:**
```bash
cast to-bytes32 <value>
```

### to_hexdata
Normalize the input to lowercase, 0x-prefixed hex.

**Parameters:**
- `value` (string, required): The value to normalize

**Usage:**
```bash
cast to-hexdata <value>
```

### to_check_sum_address
Convert an address to a checksummed format (EIP-55).

**Parameters:**
- `address` (string, required): The address to checksum

**Usage:**
```bash
cast to-check-sum-address <address>
```

## Bytes32 String Encoding

### format_bytes32_string
Format a string into bytes32 encoding.

**Parameters:**
- `value` (string, required): The string to format

**Usage:**
```bash
cast format-bytes32-string <value>
```

### parse_bytes32_string
Parse a string from bytes32 encoding.

**Parameters:**
- `bytes32` (string, required): The bytes32 value

**Usage:**
```bash
cast parse-bytes32-string <bytes32>
```

### parse_bytes32_address
Parse a checksummed address from bytes32 encoding.

**Parameters:**
- `bytes32` (string, required): The bytes32 value

**Usage:**
```bash
cast parse-bytes32-address <bytes32>
```

## RLP Encoding

### to_rlp
RLP encode hex data or an array of hex data.

**Parameters:**
- `value` (string, required): The value to encode

**Usage:**
```bash
cast to-rlp <value>
```

### from_rlp
Decode RLP hex-encoded data.

**Parameters:**
- `data` (string, required): The RLP-encoded data

**Usage:**
```bash
cast from-rlp <data>
```

## Padding

### pad
Pad hex data to a specified length.

**Parameters:**
- `value` (string, required): The value to pad
- `length` (string, required): The target length
- `left` (boolean, optional): Pad on the left (default: true)

**Usage:**
```bash
cast pad [--left] <value> <length>
```
