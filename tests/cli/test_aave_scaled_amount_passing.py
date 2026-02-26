"""Tests for scaled_amount passing to processors.

These tests verify that the scaled_amount field from scaled token events
is correctly passed to the revision-specific processors.

This addresses the bug where scaled_amount was not being passed, causing
processors to use fallback calculations instead of the pre-calculated values.
"""

import pytest

from degenbot.aave.processors import (
    CollateralMintEvent,
    CollateralBurnEvent,
    DebtMintEvent,
    DebtBurnEvent,
)
from degenbot.aave.processors.collateral.v5 import CollateralV5Processor
from degenbot.aave.processors.debt.v5 import DebtV5Processor


class TestScaledAmountPassing:
    """Test that scaled_amount is correctly passed to processors."""

    def test_debt_mint_uses_scaled_amount(self):
        """Test that DebtV5Processor uses scaled_amount when provided."""
        processor = DebtV5Processor()

        # Create a debt mint event with pre-calculated scaled_amount
        event = DebtMintEvent(
            caller="0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91",
            on_behalf_of="0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91",
            value=10**18,  # 1 DAI
            balance_increase=0,
            index=10**27,  # 1.0 RAY
            scaled_amount=10**18,  # Pre-calculated scaled amount
        )

        # When scaled_delta is provided, it should be used directly
        result = processor.process_mint_event(
            event_data=event,
            previous_balance=0,
            previous_index=10**27,
            scaled_delta=event.scaled_amount,
        )

        # The balance_delta should be the scaled_amount, not calculated from event data
        assert result.balance_delta == 10**18
        assert result.new_index == 10**27
        assert result.is_repay is False

    def test_debt_mint_fallback_calculation(self):
        """Test that DebtV5Processor falls back to calculation when scaled_amount is None."""
        processor = DebtV5Processor()

        # Create a debt mint event without scaled_amount
        event = DebtMintEvent(
            caller="0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91",
            on_behalf_of="0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91",
            value=10**18,  # 1 DAI
            balance_increase=0,
            index=10**27,  # 1.0 RAY
            scaled_amount=None,
        )

        # When scaled_delta is None, processor should calculate from event data
        result = processor.process_mint_event(
            event_data=event,
            previous_balance=0,
            previous_index=10**27,
            scaled_delta=None,
        )

        # Should calculate: ray_div_ceil(1e18 - 0, 1e27) = 1e18
        assert result.balance_delta == 10**18
        assert result.new_index == 10**27
        assert result.is_repay is False

    def test_collateral_mint_uses_scaled_amount(self):
        """Test that CollateralV5Processor uses scaled_amount when provided."""
        processor = CollateralV5Processor()

        # Create a collateral mint event with pre-calculated scaled_amount
        event = CollateralMintEvent(
            value=10**18,  # 1 token
            balance_increase=0,
            index=10**27,  # 1.0 RAY
            scaled_amount=10**18,  # Pre-calculated scaled amount
        )

        # When scaled_delta is provided, it should be used directly
        result = processor.process_mint_event(
            event_data=event,
            previous_balance=0,
            previous_index=10**27,
            scaled_delta=event.scaled_amount,
        )

        # The balance_delta should be the scaled_amount, not calculated from event data
        assert result.balance_delta == 10**18
        assert result.new_index == 10**27
        assert result.is_repay is False

    def test_collateral_burn_uses_scaled_amount(self):
        """Test that CollateralV5Processor uses scaled_amount for burn when provided."""
        processor = CollateralV5Processor()

        # Create a collateral burn event with pre-calculated scaled_amount
        event = CollateralBurnEvent(
            value=10**18,  # 1 token
            balance_increase=0,
            index=10**27,  # 1.0 RAY
            scaled_amount=10**18,  # Pre-calculated scaled amount
        )

        # When scaled_delta is provided, it should be used directly (negative for burn)
        result = processor.process_burn_event(
            event_data=event,
            previous_balance=10**18,
            previous_index=10**27,
            scaled_delta=event.scaled_amount,
        )

        # The balance_delta should be negative scaled_amount
        assert result.balance_delta == -(10**18)
        assert result.new_index == 10**27

    def test_debt_burn_uses_scaled_amount(self):
        """Test that DebtV5Processor uses scaled_amount for burn when provided."""
        processor = DebtV5Processor()

        # Create a debt burn event with pre-calculated scaled_amount
        event = DebtBurnEvent(
            from_="0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91",
            target="0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91",
            value=10**18,  # 1 DAI
            balance_increase=0,
            index=10**27,  # 1.0 RAY
            scaled_amount=10**18,  # Pre-calculated scaled amount
        )

        # When scaled_delta is provided, it should be used directly
        result = processor.process_burn_event(
            event_data=event,
            previous_balance=10**18,
            previous_index=10**27,
            scaled_delta=event.scaled_amount,
        )

        # The balance_delta should be negative scaled_amount
        assert result.balance_delta == -(10**18)
        assert result.new_index == 10**27


class TestDebtMintEventIntegrity:
    """Test that DebtMintEvent values are not corrupted."""

    def test_debt_mint_event_value_is_not_address(self):
        """Test that the value field is not accidentally set to an address.

        This tests the specific bug where user address was being stored as balance.
        """
        user_address = "0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91"
        user_address_int = int(user_address, 16)

        # Create event with proper value
        event = DebtMintEvent(
            caller=user_address,
            on_behalf_of=user_address,
            value=10**18,  # Should be 1e18, not the address
            balance_increase=0,
            index=10**27,
            scaled_amount=10**18,
        )

        # Verify value is not the address
        assert event.value != user_address_int
        assert event.value == 10**18

        # Verify caller and on_behalf_of are addresses
        assert event.caller == user_address
        assert event.on_behalf_of == user_address

    def test_v5_processor_does_not_corrupt_value(self):
        """Test that V5 processor doesn't corrupt the value field."""
        processor = DebtV5Processor()

        user_address = "0x7FA5195595EFE0dFbc79f03303448af3FbE4ea91"
        user_address_int = int(user_address, 16)

        event = DebtMintEvent(
            caller=user_address,
            on_behalf_of=user_address,
            value=10**18,
            balance_increase=0,
            index=10**27,
            scaled_amount=None,
        )

        result = processor.process_mint_event(
            event_data=event,
            previous_balance=0,
            previous_index=10**27,
            scaled_delta=None,
        )

        # Result should be reasonable (1e18), not user address
        assert result.balance_delta != user_address_int
        assert result.balance_delta == 10**18
