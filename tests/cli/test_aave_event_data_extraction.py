"""Tests for Aave V3 event data extraction functions.

These tests verify that event data is correctly extracted from Pool events,
accounting for address fields in the data that must be skipped before
decoding uint256 amounts.

See debug/aave/0045 for the bug report on incorrect event data decoding.
"""

import pytest
from eth_abi import encode
from hexbytes import HexBytes
from web3.types import LogReceipt

from degenbot.checksum_cache import get_checksum_address
from degenbot.cli.aave_event_matching import OperationAwareEventMatcher
from degenbot.cli.aave_transaction_operations import (
    AssetFlow,
    Operation,
    OperationType,
    ScaledTokenEvent,
)

# Test addresses
TEST_RESERVE = get_checksum_address("0x6B175474E89094C44Da98b954EedeAC495271d0F")  # DAI
TEST_USER = get_checksum_address("0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91")
TEST_CALLER = get_checksum_address("0x1234567890123456789012345678901234567890")
TEST_ONBEHALF = get_checksum_address("0xABCDEF1234567890ABCDEF1234567890ABCDEF12")
TEST_LIQUIDATOR = get_checksum_address("0x1111111111111111111111111111111111111111")


def create_pool_event(
    *,
    event_topic: HexBytes,
    topics: list[HexBytes],
    data: bytes,
    log_index: int = 100,
    block_number: int = 16496939,
) -> LogReceipt:
    """Create a pool event for testing."""
    return {
        "address": get_checksum_address("0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"),
        "topics": topics,
        "data": HexBytes(data),
        "logIndex": log_index,
        "blockNumber": block_number,
        "transactionHash": HexBytes("0x" + "00" * 32),
        "transactionIndex": 0,
        "blockHash": HexBytes("0x" + "00" * 32),
    }


def create_test_operation(
    *,
    operation_type: OperationType,
    pool_event: LogReceipt | None,
    scaled_token_events: list[ScaledTokenEvent] | None = None,
) -> Operation:
    """Create a test operation for the event matcher."""
    return Operation(
        operation_id=1,
        operation_type=operation_type,
        pool_event=pool_event,
        scaled_token_events=scaled_token_events or [],
        transfer_events=[],
        balance_transfer_events=[],
        asset_flows=[],
        validation_errors=[],
    )


class TestSupplyDataExtraction:
    """Test SUPPLY event data extraction."""

    def test_extract_supply_amount_skips_address(self):
        """SUPPLY event: data=(address caller, uint256 amount, uint16 referralCode)

                The first 32 bytes is the caller address, which must be skipped
        to get the amount.
        """
        # SUPPLY event: Supply(address,address,address,uint256,uint16)
        # topics: [event_sig, reserve, user, onBehalfOf]
        # data: (address caller, uint256 amount, uint16 referralCode)
        supply_topic = HexBytes(
            "0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61"
        )

        # Encode data: address caller, uint256 amount, uint16 referralCode
        amount = 10**18  # 1 DAI
        data = encode(
            ["address", "uint256", "uint16"],
            [TEST_CALLER, amount, 0],  # referralCode = 0
        )

        pool_event = create_pool_event(
            event_topic=supply_topic,
            topics=[
                supply_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),
                HexBytes("0x" + "00" * 24 + TEST_ONBEHALF[2:]),
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.SUPPLY,
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_supply_data()

        assert result["raw_amount"] == amount, (
            f"Expected amount {amount}, got {result['raw_amount']}. "
            f"If we decoded from byte 0, we'd get {int(TEST_CALLER, 16)}"
        )

    def test_extract_supply_with_zero_amount(self):
        """SUPPLY event with zero amount."""
        supply_topic = HexBytes(
            "0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61"
        )

        data = encode(
            ["address", "uint256", "uint16"],
            [TEST_CALLER, 0, 0],
        )

        pool_event = create_pool_event(
            event_topic=supply_topic,
            topics=[
                supply_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),
                HexBytes("0x" + "00" * 24 + TEST_ONBEHALF[2:]),
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.SUPPLY,
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_supply_data()

        assert result["raw_amount"] == 0

    def test_extract_supply_with_none_event(self):
        """SUPPLY extraction with None pool event returns 0."""
        operation = create_test_operation(
            operation_type=OperationType.SUPPLY,
            pool_event=None,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_supply_data()

        assert result["raw_amount"] == 0


class TestWithdrawDataExtraction:
    """Test WITHDRAW event data extraction."""

    def test_extract_withdraw_amount(self):
        """WITHDRAW event: data=(uint256 amount)

        WITHDRAW has no address at the start, so we decode directly from byte 0.
        """
        # WITHDRAW event: Withdraw(address,address,address,uint256)
        # topics: [event_sig, reserve, user, to]
        # data: (uint256 amount)
        withdraw_topic = HexBytes(
            "0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7"
        )

        amount = 5 * 10**18  # 5 DAI
        data = encode(["uint256"], [amount])

        pool_event = create_pool_event(
            event_topic=withdraw_topic,
            topics=[
                withdraw_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),  # to = user
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.WITHDRAW,
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_withdraw_data()

        assert result["raw_amount"] == amount

    def test_extract_withdraw_with_none_event(self):
        """WITHDRAW extraction with None pool event returns 0."""
        operation = create_test_operation(
            operation_type=OperationType.WITHDRAW,
            pool_event=None,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_withdraw_data()

        assert result["raw_amount"] == 0


class TestBorrowDataExtraction:
    """Test BORROW event data extraction."""

    def test_extract_borrow_amount_skips_address(self):
        """BORROW event: data=(address caller, uint256 amount, uint8 interestRateMode, uint256 borrowRate, uint16 referralCode)

                The first 32 bytes is the caller address, which must be skipped
        to get the amount.
        """
        # BORROW event: Borrow(address,address,address,uint256,uint8,uint256,uint16)
        # topics: [event_sig, reserve, user, onBehalfOf]
        # data: (address caller, uint256 amount, uint8 interestRateMode, uint256 borrowRate, uint16 referralCode)
        borrow_topic = HexBytes(
            "0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0"
        )

        amount = 10**18  # 1 DAI
        data = encode(
            ["address", "uint256", "uint8", "uint256", "uint16"],
            [TEST_CALLER, amount, 2, 10**27, 0],  # variable rate, index=1e27, referral=0
        )

        pool_event = create_pool_event(
            event_topic=borrow_topic,
            topics=[
                borrow_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),
                HexBytes("0x" + "00" * 24 + TEST_ONBEHALF[2:]),
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.BORROW,
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_borrow_data()

        assert result["raw_amount"] == amount, (
            f"Expected amount {amount}, got {result['raw_amount']}. "
            f"If we decoded from byte 0, we'd get {int(TEST_CALLER, 16)}"
        )

    def test_extract_borrow_with_none_event(self):
        """BORROW extraction with None pool event returns 0."""
        operation = create_test_operation(
            operation_type=OperationType.BORROW,
            pool_event=None,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_borrow_data()

        assert result["raw_amount"] == 0


class TestRepayDataExtraction:
    """Test REPAY event data extraction."""

    def test_extract_repay_amount_and_use_atokens(self):
        """REPAY event: data=(uint256 amount, bool useATokens)

        REPAY has no address at the start, so we decode directly from byte 0.
        """
        # REPAY event: Repay(address,address,address,uint256,bool)
        # topics: [event_sig, reserve, user, repayer]
        # data: (uint256 amount, bool useATokens)
        repay_topic = HexBytes("0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051")

        amount = 2 * 10**18  # 2 DAI
        use_atokens = True
        data = encode(["uint256", "bool"], [amount, use_atokens])

        pool_event = create_pool_event(
            event_topic=repay_topic,
            topics=[
                repay_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),
                HexBytes("0x" + "00" * 24 + TEST_CALLER[2:]),  # repayer
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.REPAY,
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_repay_data()

        assert result["raw_amount"] == amount
        assert result["use_a_tokens"] == use_atokens

    def test_extract_repay_without_atokens(self):
        """REPAY event with useATokens=False."""
        repay_topic = HexBytes("0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051")

        amount = 10**18
        use_atokens = False
        data = encode(["uint256", "bool"], [amount, use_atokens])

        pool_event = create_pool_event(
            event_topic=repay_topic,
            topics=[
                repay_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),
                HexBytes("0x" + "00" * 24 + TEST_CALLER[2:]),
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.REPAY,
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_repay_data()

        assert result["raw_amount"] == amount
        assert result["use_a_tokens"] == use_atokens

    def test_extract_repay_with_none_event(self):
        """REPAY extraction with None pool event returns 0/False."""
        operation = create_test_operation(
            operation_type=OperationType.REPAY,
            pool_event=None,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_repay_data()

        assert result["raw_amount"] == 0
        assert result["use_a_tokens"] == False


class TestLiquidationDataExtraction:
    """Test LIQUIDATION_CALL event data extraction."""

    def test_extract_liquidation_amounts(self):
        """LIQUIDATION_CALL event: data=(uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)

        The first two uint256s are debtToCover and liquidatedCollateralAmount.
        We decode both from byte 0 since there's no address prefix.
        """
        # LIQUIDATION_CALL event
        liquidation_topic = HexBytes(
            "0xe413a413e37c9bfde0de62e4858d257fd299aade3c5a43e4b1b05982392c9105"
        )

        debt_to_cover = 10**18  # 1 DAI
        liquidated_collateral = 15 * 10**17  # 1.5 collateral

        data = encode(
            ["uint256", "uint256", "address", "bool"],
            [debt_to_cover, liquidated_collateral, TEST_LIQUIDATOR, False],
        )

        pool_event = create_pool_event(
            event_topic=liquidation_topic,
            topics=[
                liquidation_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),  # collateralAsset
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),  # debtAsset (same for simplicity)
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),  # user
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.LIQUIDATION,
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_liquidation_data()

        assert result["debt_to_cover"] == debt_to_cover
        assert result["liquidated_collateral"] == liquidated_collateral

    def test_extract_liquidation_with_none_event(self):
        """LIQUIDATION extraction with None pool event returns 0s."""
        operation = create_test_operation(
            operation_type=OperationType.LIQUIDATION,
            pool_event=None,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_liquidation_data()

        assert result["debt_to_cover"] == 0
        assert result["liquidated_collateral"] == 0


class TestDeficitDataExtraction:
    """Test DEFICIT_CREATED event data extraction."""

    def test_extract_deficit_amount(self):
        """DEFICIT_CREATED event: data=(uint256 amountCreated)"""
        # DEFICIT_CREATED event
        deficit_topic = HexBytes(
            "0x6c0a0e82a1c5e6c8f5c6f4d5c3b2a1908f7e6d5c4b3a29180706050403020100"
        )

        amount_created = 5 * 10**17  # 0.5
        data = encode(["uint256"], [amount_created])

        pool_event = create_pool_event(
            event_topic=deficit_topic,
            topics=[
                deficit_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.GHO_FLASH_LOAN,  # or other operation type
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_deficit_data()

        assert result["amount_created"] == amount_created

    def test_extract_deficit_with_none_event(self):
        """DEFICIT extraction with None pool event returns 0."""
        operation = create_test_operation(
            operation_type=OperationType.GHO_FLASH_LOAN,
            pool_event=None,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_deficit_data()

        assert result["amount_created"] == 0


class TestEventDataExtractionEdgeCases:
    """Test edge cases for event data extraction."""

    def test_supply_amount_not_equal_to_caller_address(self):
        """Ensure SUPPLY amount is not accidentally the caller address.

        This is the specific bug that was fixed - if we decoded from byte 0,
        we'd get the caller address as the amount.
        """
        supply_topic = HexBytes(
            "0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61"
        )

        amount = 10**18
        data = encode(
            ["address", "uint256", "uint16"],
            [TEST_CALLER, amount, 0],
        )

        pool_event = create_pool_event(
            event_topic=supply_topic,
            topics=[
                supply_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),
                HexBytes("0x" + "00" * 24 + TEST_ONBEHALF[2:]),
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.SUPPLY,
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_supply_data()

        caller_as_int = int(TEST_CALLER, 16)
        assert result["raw_amount"] != caller_as_int, (
            f"Amount should not equal caller address! "
            f"Got {result['raw_amount']} which equals address {TEST_CALLER}"
        )
        assert result["raw_amount"] == amount

    def test_borrow_amount_not_equal_to_caller_address(self):
        """Ensure BORROW amount is not accidentally the caller address."""
        borrow_topic = HexBytes(
            "0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0"
        )

        amount = 10**18
        data = encode(
            ["address", "uint256", "uint8", "uint256", "uint16"],
            [TEST_CALLER, amount, 2, 10**27, 0],
        )

        pool_event = create_pool_event(
            event_topic=borrow_topic,
            topics=[
                borrow_topic,
                HexBytes("0x" + "00" * 24 + TEST_RESERVE[2:]),
                HexBytes("0x" + "00" * 24 + TEST_USER[2:]),
                HexBytes("0x" + "00" * 24 + TEST_ONBEHALF[2:]),
            ],
            data=data,
        )

        operation = create_test_operation(
            operation_type=OperationType.BORROW,
            pool_event=pool_event,
        )

        matcher = OperationAwareEventMatcher(operation)
        result = matcher._extract_borrow_data()

        caller_as_int = int(TEST_CALLER, 16)
        assert result["raw_amount"] != caller_as_int, (
            f"Amount should not equal caller address! "
            f"Got {result['raw_amount']} which equals address {TEST_CALLER}"
        )
        assert result["raw_amount"] == amount
