"""Tests for Bug #0044 - Collateral Mint Event Matching for swapAndRepay Operations.

This test verifies that in swapAndRepay transactions:
1. Interest accrual mints (value == balanceIncrease) match WITHDRAW events first
2. Supply mints (value > balanceIncrease) match SUPPLY events
3. Event consumption prevents cross-matching between mints

See debug/aave/0044 for detailed bug report.
"""

from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

from hexbytes import HexBytes

from degenbot.checksum_cache import get_checksum_address
from degenbot.aave.events import AaveV3PoolEvent
from degenbot.cli.aave_event_matching import (
    EventMatcher,
    ScaledTokenEventType,
)

if TYPE_CHECKING:
    from web3.types import LogReceipt


# Valid 32-byte hex values for test data
ZERO_32 = "0x0000000000000000000000000000000000000000000000000000000000000000"
CALLER_ADDR = "0x0000000000000000000000001809f186d680f239420b56948c58f8dbbcdf1e18"
TEST_VALUE = "0x000000000000000000000000000000000000000000000000000000001fc39e8c"
TEST_INDEX = "0x000000000000000000000000000000000000000003498abf9523bd0559960244"


class TestSwapAndRepayMatching:
    """Test swapAndRepay transaction event matching."""

    def test_interest_mint_matches_withdraw_before_supply(self):
        """Interest accrual mint should match WITHDRAW before SUPPLY.

        In swapAndRepay transactions, the first mint (interest accrual) should
        match the WITHDRAW event, not the SUPPLY event that belongs to the
        second mint (supply of excess).

        See debug/aave/0044.
        """
        user = get_checksum_address("0x6CD71d6Cb7824add7c277F2CA99635D98F8b9248")
        caller = get_checksum_address("0x1809f186D680f239420B56948C58F8DbbCdf1E18")
        reserve = get_checksum_address("0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0")

        # Create WITHDRAW event at logIndex 296
        withdraw_event = {
            "address": get_checksum_address("0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"),
            "topics": [
                AaveV3PoolEvent.WITHDRAW.value,
                HexBytes(reserve),
                HexBytes(caller),
            ],
            "data": HexBytes(ZERO_32),  # amount
            "logIndex": 296,
            "transactionHash": HexBytes("0x1234"),
            "blockNumber": 16502006,
        }

        # Create SUPPLY event at logIndex 318
        supply_event = {
            "address": get_checksum_address("0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"),
            "topics": [
                AaveV3PoolEvent.SUPPLY.value,
                HexBytes(reserve),
                HexBytes(caller),
                HexBytes(ZERO_32),
            ],
            "data": HexBytes(CALLER_ADDR + ZERO_32[2:]),  # caller + amount
            "logIndex": 318,
            "transactionHash": HexBytes("0x1234"),
            "blockNumber": 16502006,
        }

        # Create transaction context with pool events
        tx_context = MagicMock()
        tx_context.pool_events = [
            cast("LogReceipt", withdraw_event),
            cast("LogReceipt", supply_event),
        ]
        tx_context.matched_pool_events = {}

        # Create EventMatcher
        matcher = EventMatcher(tx_context)

        # Try to find matching pool event for interest mint
        # When value == balanceIncrease, should try WITHDRAW first
        result = matcher.find_matching_pool_event(
            event_type=ScaledTokenEventType.COLLATERAL_MINT,
            user_address=caller,
            reserve_address=reserve,
            check_users=[user],
            try_event_type_first=AaveV3PoolEvent.WITHDRAW,
        )

        # Should find the WITHDRAW event
        assert result is not None, "Should find matching WITHDRAW event"
        assert result["pool_event"]["logIndex"] == 296, "Should match WITHDRAW at logIndex 296"

    def test_supply_mint_matches_supply_after_interest_mint(self):
        """Supply mint should match SUPPLY after interest mint consumed WITHDRAW.

        In swapAndRepay transactions, after the interest mint matches the WITHDRAW
        event, the supply mint should still be able to match the SUPPLY event.

        See debug/aave/0044.
        """
        user = get_checksum_address("0x6CD71d6Cb7824add7c277F2CA99635D98F8b9248")
        caller = get_checksum_address("0x1809f186D680f239420B56948C58F8DbbCdf1E18")
        reserve = get_checksum_address("0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0")

        # Create WITHDRAW event at logIndex 296
        withdraw_event = {
            "address": get_checksum_address("0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"),
            "topics": [
                AaveV3PoolEvent.WITHDRAW.value,
                HexBytes(reserve),
                HexBytes(caller),
            ],
            "data": HexBytes(ZERO_32),
            "logIndex": 296,
            "transactionHash": HexBytes("0x1234"),
            "blockNumber": 16502006,
        }

        # Create SUPPLY event at logIndex 318
        supply_event = {
            "address": get_checksum_address("0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"),
            "topics": [
                AaveV3PoolEvent.SUPPLY.value,
                HexBytes(reserve),
                HexBytes(caller),
                HexBytes(ZERO_32),
            ],
            "data": HexBytes(CALLER_ADDR + ZERO_32[2:]),
            "logIndex": 318,
            "transactionHash": HexBytes("0x1234"),
            "blockNumber": 16502006,
        }

        tx_context = MagicMock()
        tx_context.pool_events = [
            cast("LogReceipt", withdraw_event),
            cast("LogReceipt", supply_event),
        ]
        tx_context.matched_pool_events = {}

        matcher = EventMatcher(tx_context)

        # First, interest mint consumes WITHDRAW
        matcher.find_matching_pool_event(
            event_type=ScaledTokenEventType.COLLATERAL_MINT,
            user_address=caller,
            reserve_address=reserve,
            check_users=[user],
            try_event_type_first=AaveV3PoolEvent.WITHDRAW,
        )

        # Second, supply mint (value > balanceIncrease) should match SUPPLY
        result = matcher.find_matching_pool_event(
            event_type=ScaledTokenEventType.COLLATERAL_MINT,
            user_address=user,
            reserve_address=reserve,
            check_users=[caller],
        )

        assert result is not None, "Should find matching SUPPLY event"
        assert result["pool_event"]["logIndex"] == 318, "Should match SUPPLY at logIndex 318"

    def test_try_event_type_first_parameter(self):
        """try_event_type_first parameter should reorder event type matching.

        When try_event_type_first is specified, that event type should be tried
        first, before the default order in MatchConfig.
        """
        user = get_checksum_address("0x6CD71d6Cb7824add7c277F2CA99635D98F8b9248")
        reserve = get_checksum_address("0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0")

        # Create WITHDRAW event
        withdraw_event = {
            "address": get_checksum_address("0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"),
            "topics": [
                AaveV3PoolEvent.WITHDRAW.value,
                HexBytes(reserve),
                HexBytes(user),
            ],
            "data": HexBytes(ZERO_32),
            "logIndex": 100,
            "transactionHash": HexBytes("0x1234"),
            "blockNumber": 16502006,
        }

        # Create SUPPLY event
        supply_event = {
            "address": get_checksum_address("0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"),
            "topics": [
                AaveV3PoolEvent.SUPPLY.value,
                HexBytes(reserve),
                HexBytes(user),
                HexBytes(ZERO_32),
            ],
            "data": HexBytes(CALLER_ADDR + ZERO_32[2:]),
            "logIndex": 200,
            "transactionHash": HexBytes("0x1234"),
            "blockNumber": 16502006,
        }

        tx_context = MagicMock()
        tx_context.pool_events = [
            cast("LogReceipt", supply_event),
            cast("LogReceipt", withdraw_event),
        ]
        tx_context.matched_pool_events = {}

        matcher = EventMatcher(tx_context)

        # Without try_event_type_first, SUPPLY is tried first (per MatchConfig)
        result1 = matcher.find_matching_pool_event(
            event_type=ScaledTokenEventType.COLLATERAL_MINT,
            user_address=user,
            reserve_address=reserve,
        )
        assert result1["pool_event"]["logIndex"] == 200, "Should match SUPPLY first by default"

        # Reset
        tx_context.matched_pool_events = {}

        # With try_event_type_first=WITHDRAW, WITHDRAW should be tried first
        result2 = matcher.find_matching_pool_event(
            event_type=ScaledTokenEventType.COLLATERAL_MINT,
            user_address=user,
            reserve_address=reserve,
            try_event_type_first=AaveV3PoolEvent.WITHDRAW,
        )
        assert result2["pool_event"]["logIndex"] == 100, "Should match WITHDRAW when specified"
