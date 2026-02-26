"""Tests for MINT_TO_TREASURY operation handling.

These tests verify that mintToTreasury operations do not update
collateral positions for the treasury address.
"""

import pytest
from hexbytes import HexBytes
from web3.types import LogReceipt

from degenbot.cli.aave_transaction_operations import (
    AaveV3Event,
    OperationType,
    TransactionOperationsParser,
)
from degenbot.checksum_cache import get_checksum_address

# Test addresses
TEST_POOL = get_checksum_address("0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2")
TEST_TREASURY = get_checksum_address("0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c")
TEST_ATOKEN = get_checksum_address("0x0B925eD163218f6662a35e0f0371Ac234f9E9371")
TEST_RESERVE = get_checksum_address("0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0")

MINT_EVENT_TOPIC = HexBytes("0x458f5fa412d0f69b08dd84872b0215675cc67bc1d5b6fd93300a1c3878b86196")


def create_mint_event(
    caller: str,
    user: str,
    amount: int,
    balance_increase: int,
    index: int,
    log_index: int,
    token_address: str = TEST_ATOKEN,
) -> LogReceipt:
    """Create a Mint event for testing."""

    data = (
        amount.to_bytes(32, "big")
        + balance_increase.to_bytes(32, "big")
        + index.to_bytes(32, "big")
    )

    return {
        "address": token_address,
        "topics": [
            MINT_EVENT_TOPIC,
            HexBytes("0x" + "0" * 24 + caller[2:]),
            HexBytes("0x" + "0" * 24 + user[2:]),
        ],
        "data": data,
        "blockNumber": 16516952,
        "blockHash": HexBytes("0x" + "ab" * 32),
        "transactionHash": HexBytes("0x" + "cd" * 32),
        "transactionIndex": 0,
        "logIndex": log_index,
        "removed": False,
    }


class TestMintToTreasury:
    """Test mintToTreasury operation handling."""

    def test_mint_to_treasury_operation_created(self):
        """Test that MINT_TO_TREASURY operations are created correctly."""

        token_mapping = {TEST_ATOKEN: "aToken"}
        parser = TransactionOperationsParser(
            token_type_mapping=token_mapping,
            pool_address=TEST_POOL,
        )

        # Create a mint event where caller is Pool and user is Treasury
        mint_event = create_mint_event(
            caller=TEST_POOL,
            user=TEST_TREASURY,
            amount=1942944858625595,
            balance_increase=0,
            index=1000118049507356325074809392,
            log_index=10,
        )

        tx_hash = HexBytes("0x" + "12" * 32)
        tx_operations = parser.parse([mint_event], tx_hash)

        # Should create exactly one operation
        assert len(tx_operations.operations) == 1

        operation = tx_operations.operations[0]

        # Should be MINT_TO_TREASURY type
        assert operation.operation_type == OperationType.MINT_TO_TREASURY

        # Should have no pool event
        assert operation.pool_event is None

        # Should have exactly one scaled token event
        assert len(operation.scaled_token_events) == 1

        # The scaled token event should be COLLATERAL_MINT
        assert operation.scaled_token_events[0].event_type == "COLLATERAL_MINT"

        # The user should be the treasury
        assert operation.scaled_token_events[0].user_address == TEST_TREASURY

        # The caller should be the pool
        assert operation.scaled_token_events[0].caller_address == TEST_POOL

    def test_regular_supply_not_affected(self):
        """Test that regular SUPPLY operations are still created correctly."""

        token_mapping = {TEST_ATOKEN: "aToken"}
        parser = TransactionOperationsParser(
            token_type_mapping=token_mapping,
            pool_address=TEST_POOL,
        )

        user = get_checksum_address("0x1234567890123456789012345678901234567890")

        # Create a mint event where caller is NOT Pool (regular user supply)
        mint_event = create_mint_event(
            caller=user,  # User is the caller, not Pool
            user=user,
            amount=1000000000000000000,  # 1 token
            balance_increase=0,
            index=1000000000000000000000000000,
            log_index=10,
        )

        tx_hash = HexBytes("0x" + "34" * 32)
        tx_operations = parser.parse([mint_event], tx_hash)

        # Should NOT create a MINT_TO_TREASURY operation
        # (it might create an unassigned operation or no operation)
        mint_to_treasury_ops = [
            op
            for op in tx_operations.operations
            if op.operation_type == OperationType.MINT_TO_TREASURY
        ]
        assert len(mint_to_treasury_ops) == 0

    def test_multiple_mint_to_treasury_events(self):
        """Test handling multiple mintToTreasury events in one transaction."""

        token_mapping = {
            TEST_ATOKEN: "aToken",
            get_checksum_address("0x0987654321098765432109876543210987654321"): "aToken",
        }
        parser = TransactionOperationsParser(
            token_type_mapping=token_mapping,
            pool_address=TEST_POOL,
        )

        token2 = get_checksum_address("0x0987654321098765432109876543210987654321")

        # Create multiple mint events to treasury
        mint_event_1 = create_mint_event(
            caller=TEST_POOL,
            user=TEST_TREASURY,
            amount=1942944858625595,
            balance_increase=0,
            index=1000118049507356325074809392,
            log_index=10,
            token_address=TEST_ATOKEN,
        )

        mint_event_2 = create_mint_event(
            caller=TEST_POOL,
            user=TEST_TREASURY,
            amount=64747802839500,
            balance_increase=0,
            index=1000118049507356325074809392,
            log_index=20,
            token_address=token2,
        )

        tx_hash = HexBytes("0x" + "56" * 32)
        tx_operations = parser.parse([mint_event_1, mint_event_2], tx_hash)

        # Should create exactly two MINT_TO_TREASURY operations
        mint_to_treasury_ops = [
            op
            for op in tx_operations.operations
            if op.operation_type == OperationType.MINT_TO_TREASURY
        ]
        assert len(mint_to_treasury_ops) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
