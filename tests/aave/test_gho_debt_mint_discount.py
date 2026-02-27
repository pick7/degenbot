"""Tests for GHO debt mint discount processing.

Reference: Issue 0005 - GHO debt mint not applying discount in operation-based processing.
Transaction: 0xf514f3d041e74f25909bb31c5bb2c7b58b4f329f3485a3a054f648293d87579e
Block: 17699264
"""

import pytest

from degenbot.aave.libraries import percentage_math, wad_ray_math
from degenbot.aave.processors.base import DebtMintEvent, GhoMintResult, GhoUserOperation
from degenbot.aave.processors.debt.gho.v1 import GhoV1Processor
from degenbot.checksum_cache import get_checksum_address


class TestGhoDebtMintDiscount:
    """Test GHO debt mint correctly applies discount.

    This test verifies the fix for issue 0005 where GHO debt mint events
    were not applying the user's discount when processed through the
    operation-based event processing path.
    """

    def test_gho_borrow_with_discount_calculation(self):
        """Test that GHO borrow mint applies discount correctly.

        Verifies the calculation from transaction 0xf514f3d0... at block 17699264:
        - User: 0x28B723a068e99520580bbfbe871cB5F56a658dB4
        - Previous balance: 9999999714611876286
        - Previous index: 1000000028538813185832849321
        - Current index: 1000000062785390083924562220
        - Discount percent: 3000 (30%)
        - Borrow amount: 3000000000000000000000 (3000 GHO)
        - Balance increase (from Mint event): 239726031445

        Expected:
        - discount_scaled: 102739721311
        - balance_delta: 2999999811541101852930
        - Final balance: 3009999811255713729216
        """
        processor = GhoV1Processor()

        # Transaction values
        previous_balance = 9999999714611876286
        previous_index = 1000000028538813185832849321
        current_index = 1000000062785390083924562220
        discount_percent = 3000
        event_amount = 3000000000239726031445
        balance_increase = 239726031445

        # Calculate expected borrow amount
        borrow_amount = event_amount - balance_increase
        assert borrow_amount == 3000000000000000000000

        # Create event
        user_address = get_checksum_address("0x28B723a068e99520580bbfbe871cB5F56a658dB4")
        event = DebtMintEvent(
            caller=user_address,
            on_behalf_of=user_address,
            value=event_amount,
            balance_increase=balance_increase,
            index=current_index,
            scaled_amount=None,
        )

        # Process with discount
        result = processor.process_mint_event(
            event_data=event,
            previous_balance=previous_balance,
            previous_index=previous_index,
            previous_discount=discount_percent,
        )

        # Verify result
        assert isinstance(result, GhoMintResult)
        assert result.user_operation == GhoUserOperation.GHO_BORROW
        assert result.discount_scaled == 102739721311
        assert result.balance_delta == 2999999811541101852930

        # Verify final balance matches contract
        expected_final = previous_balance + result.balance_delta
        assert expected_final == 3009999811255713729216

    def test_gho_borrow_without_discount(self):
        """Test that GHO borrow without discount produces higher balance.

        This verifies that when discount=0 is used (the bug), the calculated
        balance is higher than the actual contract balance by exactly
        the discount_scaled amount.
        """
        processor = GhoV1Processor()

        # Same transaction values
        previous_balance = 9999999714611876286
        previous_index = 1000000028538813185832849321
        current_index = 1000000062785390083924562220
        event_amount = 3000000000239726031445
        balance_increase = 239726031445

        user_address = get_checksum_address("0x28B723a068e99520580bbfbe871cB5F56a658dB4")
        event = DebtMintEvent(
            caller=user_address,
            on_behalf_of=user_address,
            value=event_amount,
            balance_increase=balance_increase,
            index=current_index,
            scaled_amount=None,
        )

        # Process WITHOUT discount (the bug case)
        result_no_discount = processor.process_mint_event(
            event_data=event,
            previous_balance=previous_balance,
            previous_index=previous_index,
            previous_discount=0,
        )

        # Verify result
        assert result_no_discount.discount_scaled == 0
        assert result_no_discount.balance_delta == 2999999811643841574241

        # This is the WRONG balance (what the bug produced)
        wrong_balance = previous_balance + result_no_discount.balance_delta
        assert wrong_balance == 3009999811358453450527

        # The difference is exactly the discount_scaled amount
        correct_balance = 3009999811255713729216
        assert wrong_balance - correct_balance == 102739721311

    def test_balance_increase_calculation(self):
        """Test that balance increase is calculated correctly from indices."""
        previous_scaled = 9999999714611876286
        previous_index = 1000000028538813185832849321
        current_index = 1000000062785390083924562220

        # Calculate balance at each index
        balance_at_current = wad_ray_math.ray_mul(previous_scaled, current_index)
        balance_at_previous = wad_ray_math.ray_mul(previous_scaled, previous_index)

        # Balance increase
        balance_increase = balance_at_current - balance_at_previous

        # Should match the event's balance_increase (allowing for rounding)
        assert balance_increase == 342465759207

    def test_discount_calculation(self):
        """Test that discount is calculated correctly from balance increase."""
        balance_increase = 342465759207
        discount_percent = 3000

        # Calculate discount
        discount = percentage_math.percent_mul(balance_increase, discount_percent)
        assert discount == 102739727762

        # Calculate discount_scaled
        current_index = 1000000062785390083924562220
        discount_scaled = wad_ray_math.ray_div(discount, current_index)
        assert discount_scaled == 102739721311
