"""Test pairing of ERC20 Transfer and BalanceTransfer events.

This tests the fix for the balance mismatch at block 16521648 where both
ERC20 Transfer and BalanceTransfer events exist for the same transfer,
but with different amounts (BalanceTransfer includes interest).
"""

import eth_abi
import pytest
from degenbot.cli.aave_transaction_operations import (
    OperationType,
    TransactionOperationsParser,
)
from degenbot.checksum_cache import get_checksum_address
from hexbytes import HexBytes


# Token type mapping for parser - must use checksummed addresses
# aEthWETH token address (checksummed)
AETH_WETH_ADDRESS = "0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8"
TEST_TOKEN_TYPE_MAPPING = {
    AETH_WETH_ADDRESS: "aToken",
}


class TestTransferBalanceTransferPairing:
    """Test that Transfer and BalanceTransfer events are paired correctly."""

    @pytest.fixture
    def parser(self):
        """Create operation parser with token type mapping."""
        return TransactionOperationsParser(token_type_mapping=TEST_TOKEN_TYPE_MAPPING)

    def _create_transfer_event(
        self,
        log_index: int,
        token_address: str,
        from_addr: str,
        to_addr: str,
        amount: int,
    ) -> dict:
        """Create an ERC20 Transfer event."""
        from_addr_normalized = from_addr[2:].lower()
        to_addr_normalized = to_addr[2:].lower()

        # Encode the data properly
        data = eth_abi.encode(["uint256"], [amount])

        return {
            "address": get_checksum_address(token_address),
            "topics": [
                HexBytes("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"),
                HexBytes(f"0x000000000000000000000000{from_addr_normalized}"),
                HexBytes(f"0x000000000000000000000000{to_addr_normalized}"),
            ],
            "data": HexBytes(data),
            "blockNumber": 16521648,
            "logIndex": log_index,
            "transactionHash": HexBytes(
                "0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec"
            ),
            "transactionIndex": 19,
            "blockHash": HexBytes(
                "0x6a5170699900a8208bd28e60e61acd6a8cacea587e34341fddea217e162bf521"
            ),
        }

    def _create_balance_transfer_event(
        self,
        log_index: int,
        token_address: str,
        from_addr: str,
        to_addr: str,
        amount: int,
        index: int,
    ) -> dict:
        """Create a BalanceTransfer event."""
        from_addr_normalized = from_addr[2:].lower()
        to_addr_normalized = to_addr[2:].lower()

        # Encode the data properly: amount, index
        data = eth_abi.encode(["uint256", "uint256"], [amount, index])

        return {
            "address": get_checksum_address(token_address),
            "topics": [
                HexBytes("0x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666"),
                HexBytes(f"0x000000000000000000000000{from_addr_normalized}"),
                HexBytes(f"0x000000000000000000000000{to_addr_normalized}"),
            ],
            "data": HexBytes(data),
            "blockNumber": 16521648,
            "logIndex": log_index,
            "transactionHash": HexBytes(
                "0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec"
            ),
            "transactionIndex": 19,
            "blockHash": HexBytes(
                "0x6a5170699900a8208bd28e60e61acd6a8cacea587e34341fddea217e162bf521"
            ),
        }

    def test_transfer_and_balance_transfer_are_paired(self, parser):
        """Test that Transfer and BalanceTransfer events are paired in one operation."""
        # Token address (aEthWETH)
        token = "0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8"
        from_addr = "0x23db246031fd6f4e81b0814e9c1dc0901a18da2d"
        to_addr = "0x464c71f6c2f760dda6093dcb91c24c39e5d6e18c"

        # ERC20 Transfer amount (without interest)
        transfer_amount = 0xE93616EA3D0BF
        # BalanceTransfer amount (with interest) - this is what the contract shows
        balance_transfer_amount = 0xE92C9BA5C88A9
        index = 0x33B4FDF4D8CC08BEE51BA00

        # Create events like in block 16521648
        events = [
            # logIndex 151: ERC20 Transfer
            self._create_transfer_event(
                log_index=151,
                token_address=token,
                from_addr=from_addr,
                to_addr=to_addr,
                amount=transfer_amount,
            ),
            # logIndex 152: BalanceTransfer (includes interest)
            self._create_balance_transfer_event(
                log_index=152,
                token_address=token,
                from_addr=from_addr,
                to_addr=to_addr,
                amount=balance_transfer_amount,
                index=index,
            ),
        ]

        # Parse the transaction
        result = parser.parse(
            events=events,
            tx_hash=HexBytes("0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec"),
        )

        # Debug: Print all operations
        print(f"\nTotal operations: {len(result.operations)}")
        print(f"Unassigned events: {len(result.unassigned_events)}")
        for op in result.operations:
            print(f"  - {op.operation_type.name}: {len(op.scaled_token_events)} scaled events")
            for ev in op.scaled_token_events:
                print(f"      {ev.event_type} at logIndex {ev.event['logIndex']}")

        # Debug: Print scaled events directly from parser
        scaled_events = parser._extract_scaled_token_events(events)
        print(f"\nExtracted scaled events: {len(scaled_events)}")
        for ev in scaled_events:
            print(
                f"  - {ev.event_type}: logIndex {ev.event['logIndex']}, token {ev.event['address']}"
            )

        # Should create one BALANCE_TRANSFER operation
        transfer_ops = [
            op for op in result.operations if op.operation_type == OperationType.BALANCE_TRANSFER
        ]
        assert len(transfer_ops) == 1, (
            f"Expected 1 BALANCE_TRANSFER operation, got {len(transfer_ops)}"
        )

        op = transfer_ops[0]

        # Operation should have both events
        assert len(op.scaled_token_events) == 1, "Should have 1 scaled token event (the Transfer)"
        assert len(op.balance_transfer_events) == 1, "Should have 1 balance transfer event"

        # Check that the events are the correct ones
        assert op.scaled_token_events[0].event["logIndex"] == 151
        assert op.balance_transfer_events[0]["logIndex"] == 152

        # The BalanceTransfer should have the higher amount (includes interest)
        # Decode amount from the event data (first uint256 is amount, second is index)
        decoded_amount, _ = eth_abi.abi.decode(
            ["uint256", "uint256"], op.balance_transfer_events[0]["data"]
        )
        assert decoded_amount == balance_transfer_amount
        assert op.scaled_token_events[0].amount == transfer_amount

        # Validate - should pass without errors
        result.validate(events)

    def test_standalone_transfer_without_balance_transfer(self, parser):
        """Test that standalone Transfer events are handled correctly."""
        token = "0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8"
        from_addr = "0x23db246031fd6f4e81b0814e9c1dc0901a18da2d"
        to_addr = "0x464c71f6c2f760dda6093dcb91c24c39e5d6e18c"

        transfer_amount = 1000000

        # Only ERC20 Transfer event, no BalanceTransfer
        events = [
            self._create_transfer_event(
                log_index=100,
                token_address=token,
                from_addr=from_addr,
                to_addr=to_addr,
                amount=transfer_amount,
            ),
        ]

        result = parser.parse(
            tx_hash=HexBytes("0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"),
            events=events,
        )

        # Should create one BALANCE_TRANSFER operation
        transfer_ops = [
            op for op in result.operations if op.operation_type == OperationType.BALANCE_TRANSFER
        ]
        assert len(transfer_ops) == 1

        op = transfer_ops[0]

        # Should have the Transfer event but no BalanceTransfer
        assert len(op.scaled_token_events) == 1
        assert len(op.balance_transfer_events) == 0, (
            "Should have no balance transfer events when not present"
        )

    def test_only_balance_transfer_events_processed(self, parser):
        """Test that standalone BalanceTransfer events are processed correctly."""
        token = "0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8"
        from_addr = "0x23db246031fd6f4e81b0814e9c1dc0901a18da2d"
        to_addr = "0x464c71f6c2f760dda6093dcb91c24c39e5d6e18c"

        balance_transfer_amount = 0xE92C9BA5C88A9
        index = 0x33B4FDF4D8CC08BEE51BA00

        # Only BalanceTransfer event (can happen in some edge cases)
        events = [
            self._create_balance_transfer_event(
                log_index=100,
                token_address=token,
                from_addr=from_addr,
                to_addr=to_addr,
                amount=balance_transfer_amount,
                index=index,
            ),
        ]

        result = parser.parse(
            events=events,
            tx_hash=HexBytes("0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"),
        )

        # Should create one BALANCE_TRANSFER operation for the BalanceTransfer event
        transfer_ops = [
            op for op in result.operations if op.operation_type == OperationType.BALANCE_TRANSFER
        ]
        assert len(transfer_ops) == 1

        op = transfer_ops[0]

        # The BalanceTransfer should be in scaled_token_events since it's a COLLATERAL_TRANSFER type
        assert len(op.scaled_token_events) == 1
        # Since there's no paired ERC20 Transfer, balance_transfer_events should be empty
        # The event itself is the scaled_token_event, and balance_transfer_events is only
        # populated when there's a paired Transfer + BalanceTransfer
        assert len(op.balance_transfer_events) == 0
