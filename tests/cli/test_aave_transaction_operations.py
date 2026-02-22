"""Tests for Aave V3 transaction operations parser.

These tests verify the operation-based event parsing handles all patterns
identified in the bug reports in debug/aave/.
"""

import eth_abi
import pytest
from hexbytes import HexBytes
from web3.types import LogReceipt

from degenbot.checksum_cache import get_checksum_address
from degenbot.cli.aave_transaction_operations import (
    GHO_VARIABLE_DEBT_TOKEN_ADDRESS,
    AaveV3Event,
    OperationType,
    TransactionOperationsParser,
    TransactionValidationError,
)


# Test token addresses - used for classification
TEST_COLLATERAL_TOKEN = get_checksum_address("0x" + "1" * 40)  # aToken
TEST_DEBT_TOKEN = get_checksum_address("0x" + "2" * 40)  # vToken

# Token type mapping for parser
TEST_TOKEN_TYPE_MAPPING = {
    TEST_COLLATERAL_TOKEN: "aToken",
    TEST_DEBT_TOKEN: "vToken",
}


class EventFactory:
    """Factory for creating test events."""

    @staticmethod
    def create_supply_event(reserve: str, user: str, amount: int, log_index: int) -> LogReceipt:
        """Create a SUPPLY pool event."""

        topics = [
            AaveV3Event.SUPPLY.value,
            HexBytes("0x" + "0" * 24 + reserve[2:]),
            HexBytes("0x" + "0" * 24 + user[2:]),
        ]

        data = eth_abi.encode(
            ["address", "uint256"],
            [get_checksum_address("0x" + "0" * 40), amount],
        )

        return {
            "address": get_checksum_address("0x" + "0" * 40),
            "topics": topics,
            "data": HexBytes(data),
            "logIndex": log_index,
            "blockNumber": 1000000,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

    @staticmethod
    def create_withdraw_event(reserve: str, user: str, amount: int, log_index: int) -> LogReceipt:
        """Create a WITHDRAW pool event."""

        topics = [
            AaveV3Event.WITHDRAW.value,
            HexBytes("0x" + "0" * 24 + reserve[2:]),
            HexBytes("0x" + "0" * 24 + user[2:]),
        ]

        data = eth_abi.encode(["uint256"], [amount])

        return {
            "address": get_checksum_address("0x" + "0" * 40),
            "topics": topics,
            "data": HexBytes(data),
            "logIndex": log_index,
            "blockNumber": 1000000,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

    @staticmethod
    def create_liquidation_call_event(
        *,
        collateral_asset: str,
        debt_asset: str,
        user: str,
        debt_to_cover: int,
        liquidated_collateral: int,
        log_index: int,
    ) -> LogReceipt:
        """Create a LIQUIDATION_CALL pool event."""

        topics = [
            AaveV3Event.LIQUIDATION_CALL.value,
            HexBytes("0x" + "0" * 24 + collateral_asset[2:]),
            HexBytes("0x" + "0" * 24 + debt_asset[2:]),
            HexBytes("0x" + "0" * 24 + user[2:]),
        ]

        data = eth_abi.encode(
            ["uint256", "uint256", "address", "bool"],
            [
                debt_to_cover,
                liquidated_collateral,
                get_checksum_address("0x" + "0" * 40),
                False,
            ],
        )

        return {
            "address": get_checksum_address("0x" + "0" * 40),
            "topics": topics,
            "data": HexBytes(data),
            "logIndex": log_index,
            "blockNumber": 1000000,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

    @staticmethod
    def create_repay_event(
        *,
        reserve: str,
        user: str,
        amount: int,
        use_a_tokens: bool,
        log_index: int,
    ) -> LogReceipt:
        """Create a REPAY pool event."""

        topics = [
            AaveV3Event.REPAY.value,
            HexBytes("0x" + "0" * 24 + reserve[2:]),
            HexBytes("0x" + "0" * 24 + user[2:]),
        ]

        data = eth_abi.encode(
            ["uint256", "bool"],
            [amount, use_a_tokens],
        )

        return {
            "address": get_checksum_address("0x" + "0" * 40),
            "topics": topics,
            "data": HexBytes(data),
            "logIndex": log_index,
            "blockNumber": 1000000,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

    @staticmethod
    def create_collateral_mint_event(
        user: str, amount: int, balance_increase: int, log_index: int
    ) -> LogReceipt:
        """Create a collateral Mint event."""

        caller = get_checksum_address("0x" + "0" * 40)

        topics = [
            AaveV3Event.SCALED_TOKEN_MINT.value,
            HexBytes("0x" + "0" * 24 + caller[2:]),
            HexBytes("0x" + "0" * 24 + user[2:]),
        ]

        data = eth_abi.encode(
            ["uint256", "uint256", "uint256"],
            [amount, balance_increase, 1000000000000000000000000000],
        )

        return {
            "address": TEST_COLLATERAL_TOKEN,
            "topics": topics,
            "data": HexBytes(data),
            "logIndex": log_index,
            "blockNumber": 1000000,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

    @staticmethod
    def create_collateral_burn_event(
        user: str, amount: int, balance_increase: int, log_index: int
    ) -> LogReceipt:
        """Create a collateral Burn event."""

        target = get_checksum_address("0x" + "0" * 40)

        topics = [
            AaveV3Event.SCALED_TOKEN_BURN.value,
            HexBytes("0x" + "0" * 24 + user[2:]),
            HexBytes("0x" + "0" * 24 + target[2:]),
        ]

        data = eth_abi.encode(
            ["uint256", "uint256", "uint256"],
            [amount, balance_increase, 1000000000000000000000000000],
        )

        return {
            "address": TEST_COLLATERAL_TOKEN,
            "topics": topics,
            "data": HexBytes(data),
            "logIndex": log_index,
            "blockNumber": 1000000,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

    @staticmethod
    def create_debt_mint_event(
        user: str, amount: int, balance_increase: int, log_index: int
    ) -> LogReceipt:
        """Create a debt Mint event (interest accrual)."""

        caller = get_checksum_address("0x" + "0" * 40)

        topics = [
            AaveV3Event.SCALED_TOKEN_MINT.value,
            HexBytes("0x" + "0" * 24 + caller[2:]),
            HexBytes("0x" + "0" * 24 + user[2:]),
        ]

        data = eth_abi.encode(
            ["uint256", "uint256", "uint256"],
            [amount, balance_increase, 1000000000000000000000000000],
        )

        return {
            "address": TEST_DEBT_TOKEN,
            "topics": topics,
            "data": HexBytes(data),
            "logIndex": log_index,
            "blockNumber": 1000000,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

    @staticmethod
    def create_debt_burn_event(
        user: str, amount: int, balance_increase: int, log_index: int
    ) -> LogReceipt:
        """Create a debt Burn event."""

        target = get_checksum_address("0x" + "0" * 40)

        topics = [
            AaveV3Event.SCALED_TOKEN_BURN.value,
            HexBytes("0x" + "0" * 24 + user[2:]),
            HexBytes("0x" + "0" * 24 + target[2:]),
        ]

        data = eth_abi.encode(
            ["uint256", "uint256", "uint256"],
            [amount, balance_increase, 1000000000000000000000000000],
        )

        return {
            "address": TEST_DEBT_TOKEN,
            "topics": topics,
            "data": HexBytes(data),
            "logIndex": log_index,
            "blockNumber": 1000000,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }

    @staticmethod
    def create_gho_burn_event(
        user: str, amount: int, balance_increase: int, log_index: int
    ) -> LogReceipt:
        """Create a GHO debt Burn event."""

        target = get_checksum_address("0x" + "0" * 40)

        topics = [
            AaveV3Event.SCALED_TOKEN_BURN.value,
            HexBytes("0x" + "0" * 24 + user[2:]),
            HexBytes("0x" + "0" * 24 + target[2:]),
        ]

        data = eth_abi.encode(
            ["uint256", "uint256", "uint256"],
            [amount, balance_increase, 1000000000000000000000000000],
        )

        return {
            "address": GHO_VARIABLE_DEBT_TOKEN_ADDRESS,
            "topics": topics,
            "data": HexBytes(data),
            "logIndex": log_index,
            "blockNumber": 1000000,
            "transactionHash": HexBytes("0x" + "00" * 32),
        }


class TestOperationParsing:
    """Test parsing transactions into operations."""

    def test_supply_operation_parsed_correctly(self):
        """Standard SUPPLY -> COLLATERAL_MINT operation."""
        user = get_checksum_address("0x1234567890123456789012345678901234567890")
        reserve = get_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")

        # Create events
        mint_event = EventFactory.create_collateral_mint_event(
            user=user,
            amount=1000000000000000000,
            balance_increase=999999999999999999,  # Less than amount for deposit
            log_index=10,
        )

        supply_event = EventFactory.create_supply_event(
            reserve=reserve,
            user=user,
            amount=1000000000000000000,
            log_index=12,  # SUPPLY comes after Mint
        )

        parser = TransactionOperationsParser(token_type_mapping=TEST_TOKEN_TYPE_MAPPING)
        tx_ops = parser.parse([mint_event, supply_event], HexBytes("0x" + "00" * 32))

        assert len(tx_ops.operations) == 1
        op = tx_ops.operations[0]

        assert op.operation_type == OperationType.SUPPLY
        assert len(op.scaled_token_events) == 1
        assert op.scaled_token_events[0].event_type == "COLLATERAL_MINT"
        assert op.is_valid()

    def test_liquidation_parsed_as_single_operation(self):
        """Liquidation with LIQUIDATION_CALL -> debt burn + collateral burn."""
        user = get_checksum_address("0x1234567890123456789012345678901234567890")
        collateral_asset = get_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
        debt_asset = get_checksum_address("0xA0b86a33E6441e6C7D3D4B4b8B8B8B8B8B8B8B8B")

        # Create events
        liquidation_event = EventFactory.create_liquidation_call_event(
            collateral_asset=collateral_asset,
            debt_asset=debt_asset,
            user=user,
            debt_to_cover=500000000000000000,
            liquidated_collateral=300000000000000000,
            log_index=100,
        )

        debt_burn_event = EventFactory.create_debt_burn_event(
            user=user,
            amount=500000000000000000,
            balance_increase=500000000000000000,
            log_index=97,  # Before liquidation
        )

        collateral_burn_event = EventFactory.create_collateral_burn_event(
            user=user,
            amount=300000000000000000,
            balance_increase=300000000000000000,
            log_index=104,  # After liquidation
        )

        parser = TransactionOperationsParser(token_type_mapping=TEST_TOKEN_TYPE_MAPPING)
        tx_ops = parser.parse(
            [debt_burn_event, liquidation_event, collateral_burn_event],
            HexBytes("0x" + "00" * 32),
        )

        assert len(tx_ops.operations) == 1
        op = tx_ops.operations[0]

        assert op.operation_type == OperationType.LIQUIDATION
        assert len(op.scaled_token_events) == 2

        # Verify both burns are present
        debt_burns = [e for e in op.scaled_token_events if e.is_debt]
        collateral_burns = [e for e in op.scaled_token_events if e.is_collateral]

        assert len(debt_burns) == 1
        assert len(collateral_burns) == 1
        assert op.is_valid()

    def test_repay_with_atokens_parsed_correctly(self):
        """Repay with aTokens has debt burn + collateral burn."""
        user = get_checksum_address("0x1234567890123456789012345678901234567890")
        reserve = get_checksum_address("0xA0b86a33E6441e6C7D3D4B4b8B8B8B8B8B8B8B8B")

        # Create events
        repay_event = EventFactory.create_repay_event(
            reserve=reserve,
            user=user,
            amount=1000000000000000000,
            use_a_tokens=True,
            log_index=100,
        )

        debt_burn_event = EventFactory.create_debt_burn_event(
            user=user,
            amount=1000000000000000000,
            balance_increase=1000000000000000000,
            log_index=98,
        )

        collateral_burn_event = EventFactory.create_collateral_burn_event(
            user=user,
            amount=1000000000000000000,
            balance_increase=1000000000000000000,
            log_index=99,
        )

        parser = TransactionOperationsParser(token_type_mapping=TEST_TOKEN_TYPE_MAPPING)
        tx_ops = parser.parse(
            [debt_burn_event, collateral_burn_event, repay_event],
            HexBytes("0x" + "00" * 32),
        )

        assert len(tx_ops.operations) == 1
        op = tx_ops.operations[0]

        assert op.operation_type == OperationType.REPAY_WITH_ATOKENS
        assert len(op.scaled_token_events) == 2
        assert op.is_valid()

    def test_gho_liquidation_detected_by_address(self):
        """GHO liquidation detected by GHO token address."""
        user = get_checksum_address("0x1234567890123456789012345678901234567890")
        collateral_asset = get_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")

        # Create events
        liquidation_event = EventFactory.create_liquidation_call_event(
            collateral_asset=collateral_asset,
            debt_asset=GHO_VARIABLE_DEBT_TOKEN_ADDRESS,
            user=user,
            debt_to_cover=500000000000000000,
            liquidated_collateral=300000000000000000,
            log_index=100,
        )

        gho_burn_event = EventFactory.create_gho_burn_event(
            user=user,
            amount=500000000000000000,
            balance_increase=500000000000000000,
            log_index=97,
        )

        collateral_burn_event = EventFactory.create_collateral_burn_event(
            user=user,
            amount=300000000000000000,
            balance_increase=300000000000000000,
            log_index=104,
        )

        parser = TransactionOperationsParser()
        tx_ops = parser.parse(
            [gho_burn_event, liquidation_event, collateral_burn_event],
            HexBytes("0x" + "00" * 32),
        )

        assert len(tx_ops.operations) == 1
        op = tx_ops.operations[0]

        assert op.operation_type == OperationType.GHO_LIQUIDATION

    def test_multi_operation_tx_parsed_correctly(self):
        """ParaSwap-style multi-operation transaction."""
        user1 = get_checksum_address("0x1234567890123456789012345678901234567890")
        user2 = get_checksum_address("0x0987654321098765432109876543210987654321")
        reserve = get_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")

        # Operation 1: Withdraw
        withdraw_event = EventFactory.create_withdraw_event(
            reserve=reserve,
            user=user1,
            amount=1000000000000000000,
            log_index=50,
        )

        burn_event_1 = EventFactory.create_collateral_burn_event(
            user=user1,
            amount=1000000000000000000,
            balance_increase=1000000000000000000,
            log_index=52,  # After withdraw
        )

        # Operation 2: Supply
        supply_event = EventFactory.create_supply_event(
            reserve=reserve,
            user=user2,
            amount=2000000000000000000,
            log_index=100,
        )

        mint_event = EventFactory.create_collateral_mint_event(
            user=user2,
            amount=2000000000000000000,
            balance_increase=2000000000000000000,
            log_index=102,  # After supply
        )

        parser = TransactionOperationsParser()
        tx_ops = parser.parse(
            [withdraw_event, burn_event_1, supply_event, mint_event],
            HexBytes("0x" + "00" * 32),
        )

        assert len(tx_ops.operations) == 2

        # Verify operation types
        assert tx_ops.operations[0].operation_type == OperationType.WITHDRAW
        assert tx_ops.operations[1].operation_type == OperationType.SUPPLY


class TestOperationValidation:
    """Test strict validation of operations."""

    def test_validation_fails_on_incomplete_liquidation(self):
        """Missing collateral burn causes validation error."""
        user = get_checksum_address("0x1234567890123456789012345678901234567890")
        collateral_asset = get_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
        debt_asset = get_checksum_address("0xA0b86a33E6441e6C7D3D4B4b8B8B8B8B8B8B8B8B")

        liquidation_event = EventFactory.create_liquidation_call_event(
            collateral_asset=collateral_asset,
            debt_asset=debt_asset,
            user=user,
            debt_to_cover=500000000000000000,
            liquidated_collateral=300000000000000000,
            log_index=100,
        )

        debt_burn_event = EventFactory.create_debt_burn_event(
            user=user,
            amount=500000000000000000,
            balance_increase=500000000000000000,
            log_index=97,
        )

        # Missing collateral burn!

        parser = TransactionOperationsParser()
        tx_ops = parser.parse(
            [debt_burn_event, liquidation_event],
            HexBytes("0x" + "00" * 32),
        )

        with pytest.raises(TransactionValidationError) as exc_info:
            tx_ops.validate([debt_burn_event, liquidation_event])

        error_str = str(exc_info.value)
        assert "Expected 1 collateral burn" in error_str
        assert "DEBUG NOTE" in error_str
        assert "logIndex" in error_str

    def test_validation_fails_on_missing_debt_burn(self):
        """Missing debt burn in liquidation causes validation error."""
        user = get_checksum_address("0x1234567890123456789012345678901234567890")
        collateral_asset = get_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
        debt_asset = get_checksum_address("0xA0b86a33E6441e6C7D3D4B4b8B8B8B8B8B8B8B8B")

        liquidation_event = EventFactory.create_liquidation_call_event(
            collateral_asset=collateral_asset,
            debt_asset=debt_asset,
            user=user,
            debt_to_cover=500000000000000000,
            liquidated_collateral=300000000000000000,
            log_index=100,
        )

        # Missing debt burn!

        collateral_burn_event = EventFactory.create_collateral_burn_event(
            user=user,
            amount=300000000000000000,
            balance_increase=300000000000000000,
            log_index=104,
        )

        parser = TransactionOperationsParser()
        tx_ops = parser.parse(
            [liquidation_event, collateral_burn_event],
            HexBytes("0x" + "00" * 32),
        )

        with pytest.raises(TransactionValidationError) as exc_info:
            tx_ops.validate([liquidation_event, collateral_burn_event])

        error_str = str(exc_info.value)
        assert "Expected 1 debt burn" in error_str

    def test_repay_with_zero_debt_burns_validates(self):
        """Interest-only repayment has 0 debt burns (only interest accrual mint)."""
        # Regression test for issue #0029
        # Transaction: 0x96b71f9698a072992a4e0a4ed1ade34c1872911dda9790d94946fa38360d302d
        user = get_checksum_address("0xE873793b15e6bEc6c7118D8125E40C122D46714D")
        reserve = get_checksum_address("0xdAC17F958D2ee523a2206206994597C13D831ec7")

        # Create events: interest accrual mint + repay (no burn since only interest covered)
        interest_mint_event = EventFactory.create_debt_mint_event(
            user=user,
            amount=26804,  # Scaled tokens minted as interest
            balance_increase=26904,
            log_index=183,
        )

        repay_event = EventFactory.create_repay_event(
            reserve=reserve,
            user=user,
            amount=100000000,  # 100 USDT (6 decimals)
            use_a_tokens=False,
            log_index=186,
        )

        parser = TransactionOperationsParser(token_type_mapping=TEST_TOKEN_TYPE_MAPPING)
        tx_ops = parser.parse(
            [interest_mint_event, repay_event],
            HexBytes("0x" + "00" * 32),
        )

        assert len(tx_ops.operations) == 1
        op = tx_ops.operations[0]

        assert op.operation_type == OperationType.REPAY
        # Should have 0 debt burns (interest-only repayment)
        debt_burns = [e for e in op.scaled_token_events if e.is_debt]
        assert len(debt_burns) == 0

        # Validation should pass with 0 burns - no exception raised
        tx_ops.validate([interest_mint_event, repay_event])
        assert op.is_valid()

    def test_repay_with_one_debt_burn_validates(self):
        """Standard principal repayment has 1 debt burn."""
        user = get_checksum_address("0x1234567890123456789012345678901234567890")
        reserve = get_checksum_address("0xA0b86a33E6441e6C7D3D4B4b8B8B8B8B8B8B8B8B")

        debt_burn_event = EventFactory.create_debt_burn_event(
            user=user,
            amount=1000000000000000000,
            balance_increase=1000000000000000000,
            log_index=98,
        )

        repay_event = EventFactory.create_repay_event(
            reserve=reserve,
            user=user,
            amount=1000000000000000000,
            use_a_tokens=False,
            log_index=100,
        )

        parser = TransactionOperationsParser(token_type_mapping=TEST_TOKEN_TYPE_MAPPING)
        tx_ops = parser.parse(
            [debt_burn_event, repay_event],
            HexBytes("0x" + "00" * 32),
        )

        assert len(tx_ops.operations) == 1
        op = tx_ops.operations[0]

        assert op.operation_type == OperationType.REPAY
        # Should have 1 debt burn (principal repayment)
        debt_burns = [e for e in op.scaled_token_events if e.is_debt]
        assert len(debt_burns) == 1

        # Validation should pass with 1 burn - no exception raised
        tx_ops.validate([debt_burn_event, repay_event])
        assert op.is_valid()
