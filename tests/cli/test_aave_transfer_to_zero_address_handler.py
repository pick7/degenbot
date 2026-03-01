"""Test transfer-to-zero-address handler fix.

These tests verify that the fix for the transfer-to-zero-address bug works
correctly. The bug was that when an ERC20 Transfer event transferred aTokens
to the zero address (effectively burning them), the sender's balance was not
being reduced because the position lookup couldn't find the position that
was just created in a previous operation.

The fix ensures that _process_collateral_transfer_with_match and
_process_debt_transfer_with_match use _get_or_create_collateral_position/
_get_or_create_debt_position instead of direct scalar queries. This leverages
the relationship cache which will have the position even if the scalar query
doesn't see it yet due to session isolation.

Reference transaction: 0x4a88a8c6a43b5df2ee59ebcf266225fbc5b876f202009422f0f9d05cc4915f35
Block: 16496928
"""

import pytest
from hexbytes import HexBytes

from degenbot.checksum_cache import get_checksum_address
from degenbot.cli.aave_transaction_operations import (
    GHO_TOKEN_ADDRESS,
    TransactionOperationsParser,
    OperationType,
)

# Test addresses
USER_ADDRESS = get_checksum_address("0xE4217040c894e8873EE19d675b6d0EeC992c2c0D")
ADAPTER_ADDRESS = get_checksum_address("0x872fBcb1B582e8Cd0D0DD4327fBFa0B4C2730995")
ZERO_ADDRESS = get_checksum_address("0x0000000000000000000000000000000000000000")
ATOKEN_ADDRESS = get_checksum_address("0x4d5f47fa6a74757f35c14fd3a6ef8e3c9bc514e8")

# Token type mapping for parser
TEST_TOKEN_TYPE_MAPPING = {
    ATOKEN_ADDRESS: "aToken",
}

# ERC20 Transfer topic
TRANSFER_TOPIC = HexBytes("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")


class TestTransferToZeroAddressParsing:
    """Test that transfer-to-zero-address events are parsed correctly."""

    def test_two_transfers_create_separate_operations(self) -> None:
        """Verify that two transfer events create two separate BALANCE_TRANSFER operations."""
        transfer_amount = 1000000000000000  # 0.001 WETH

        # Transfer 1: User -> Adapter
        transfer_1 = {
            "address": ATOKEN_ADDRESS,
            "topics": [
                TRANSFER_TOPIC,
                HexBytes("0x" + "0" * 24 + USER_ADDRESS[2:]),
                HexBytes("0x" + "0" * 24 + ADAPTER_ADDRESS[2:]),
            ],
            "data": HexBytes("0x" + transfer_amount.to_bytes(32, "big").hex()),
            "blockNumber": 16496928,
            "logIndex": 0x68,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

        # Transfer 2: Adapter -> Zero Address
        transfer_2 = {
            "address": ATOKEN_ADDRESS,
            "topics": [
                TRANSFER_TOPIC,
                HexBytes("0x" + "0" * 24 + ADAPTER_ADDRESS[2:]),
                HexBytes("0x" + "0" * 24 + ZERO_ADDRESS[2:]),
            ],
            "data": HexBytes("0x" + transfer_amount.to_bytes(32, "big").hex()),
            "blockNumber": 16496928,
            "logIndex": 0x6E,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

        events = [transfer_1, transfer_2]
        parser = TransactionOperationsParser(token_type_mapping=TEST_TOKEN_TYPE_MAPPING)
        tx_operations = parser.parse(events, HexBytes("0x" + "00" * 32))

        # Should create 2 BALANCE_TRANSFER operations
        assert len(tx_operations.operations) == 2, (
            f"Expected 2 operations, got {len(tx_operations.operations)}"
        )

        # Both should be BALANCE_TRANSFER operations
        for op in tx_operations.operations:
            assert op.operation_type == OperationType.BALANCE_TRANSFER, (
                f"Expected BALANCE_TRANSFER, got {op.operation_type}"
            )
            assert len(op.scaled_token_events) == 1
            assert op.scaled_token_events[0].event_type == "COLLATERAL_TRANSFER"

        # First operation should have User -> Adapter
        op1 = tx_operations.operations[0]
        assert op1.scaled_token_events[0].from_address == USER_ADDRESS
        assert op1.scaled_token_events[0].target_address == ADAPTER_ADDRESS

        # Second operation should have Adapter -> Zero
        op2 = tx_operations.operations[1]
        assert op2.scaled_token_events[0].from_address == ADAPTER_ADDRESS
        assert op2.scaled_token_events[0].target_address == ZERO_ADDRESS

    def test_transfer_to_zero_address_has_correct_event_type(self) -> None:
        """Verify that transfer to zero address is correctly typed as COLLATERAL_TRANSFER."""
        transfer_amount = 1000000000000000

        transfer_event = {
            "address": ATOKEN_ADDRESS,
            "topics": [
                TRANSFER_TOPIC,
                HexBytes("0x" + "0" * 24 + ADAPTER_ADDRESS[2:]),
                HexBytes("0x" + "0" * 24 + ZERO_ADDRESS[2:]),
            ],
            "data": HexBytes("0x" + transfer_amount.to_bytes(32, "big").hex()),
            "blockNumber": 16496928,
            "logIndex": 0x6E,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

        parser = TransactionOperationsParser(token_type_mapping=TEST_TOKEN_TYPE_MAPPING)
        tx_operations = parser.parse([transfer_event], HexBytes("0x" + "00" * 32))

        assert len(tx_operations.operations) == 1
        op = tx_operations.operations[0]
        assert op.scaled_token_events[0].event_type == "COLLATERAL_TRANSFER"
        assert op.scaled_token_events[0].target_address == ZERO_ADDRESS


class TestTransferToZeroAddressAmounts:
    """Test that transfer amounts are correctly decoded."""

    def test_transfer_amount_matches_expected(self) -> None:
        """Verify that the transfer amount from the bug transaction is correctly decoded."""
        # From the actual bug transaction
        expected_amount = 1000000000000000  # 0.001 WETH = 0x38d7ea4c68000

        transfer_event = {
            "address": ATOKEN_ADDRESS,
            "topics": [
                TRANSFER_TOPIC,
                HexBytes("0x" + "0" * 24 + USER_ADDRESS[2:]),
                HexBytes("0x" + "0" * 24 + ADAPTER_ADDRESS[2:]),
            ],
            "data": HexBytes("0x" + expected_amount.to_bytes(32, "big").hex()),
            "blockNumber": 16496928,
            "logIndex": 0x68,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

        parser = TransactionOperationsParser(token_type_mapping=TEST_TOKEN_TYPE_MAPPING)
        tx_operations = parser.parse([transfer_event], HexBytes("0x" + "00" * 32))

        assert len(tx_operations.operations) == 1
        assert tx_operations.operations[0].scaled_token_events[0].amount == expected_amount
