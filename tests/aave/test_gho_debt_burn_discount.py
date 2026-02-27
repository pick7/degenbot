"""Test GHO debt burn with discount in operation-based processing path.

This test verifies the fix for issue 0007 where GHO debt burns in the
operation-based processing path were not using the GHO-specific processor,
which handles discount mechanics.

See debug/aave/0007 for full bug report.
"""

import pytest

from degenbot.aave.processors.base import DebtBurnEvent
from degenbot.aave.processors.debt.gho.v1 import GhoV1Processor


class TestGhoDebtBurnDiscount:
    """Test GHO debt burn operations with discount mechanics."""

    def test_gho_burn_with_discount_calculation(self) -> None:
        """Verify correct balance calculation when burning GHO debt with discount.

        This test replicates the scenario from issue 0007 where a user repaid
        5,500 GHO while having a 15.26% discount. The discount should be applied
        to the interest accrual before calculating the burn amount.
        """
        processor = GhoV1Processor()

        # Scenario from issue 0007:
        # - User has debt with 15.26% discount
        # - Repaying 5,500 GHO (scaled amount burned: 5,499,998,829,504,419,508,388)
        # - Accrued interest: 1,170,495,580,491,612
        # - Expected: discount is applied to interest, then burned

        # Interest has accrued, so previous_index < current_index
        previous_index = 1000000000000000000000000000  # Lower index
        current_index = 1000002876716465823842112176  # Higher index

        event_data = DebtBurnEvent(
            from_="0x84aC9de807CEFa7205b53108c705744dA523f901",
            target="0x0000000000000000000000000000000000000000",
            value=5499998829504419508388,  # scaled debt amount
            balance_increase=1170495580491612,  # accrued interest
            index=current_index,  # variable borrow index
        )

        # Previous balance was approximately the same as the burn amount
        previous_balance = 5499998829504419508388
        previous_discount = 1526  # 15.26% discount (basis points)

        result = processor.process_burn_event(
            event_data=event_data,
            previous_balance=previous_balance,
            previous_index=previous_index,
            previous_discount=previous_discount,
        )

        # Verify that a discount was calculated and applied
        # The discount_scaled should be > 0 when there's a discount
        assert result.discount_scaled > 0, "Expected discount to be applied"

        # Verify balance delta is negative (debt is being reduced)
        assert result.balance_delta < 0, "Expected negative balance delta for burn"

        # Verify the result includes discount information
        assert result.should_refresh_discount is True, "Expected discount refresh"

    def test_gho_burn_without_discount(self) -> None:
        """Verify burn calculation without discount (0% discount percent)."""
        processor = GhoV1Processor()

        event_data = DebtBurnEvent(
            from_="0x84aC9de807CEFa7205b53108c705744dA523f901",
            target="0x0000000000000000000000000000000000000000",
            value=1000000000000000000000,  # 1000 GHO scaled
            balance_increase=1000000000000000000,  # 1 GHO interest
            index=1000000000000000000000000000,
        )

        result = processor.process_burn_event(
            event_data=event_data,
            previous_balance=1000000000000000000000,
            previous_index=1000000000000000000000000000,
            previous_discount=0,  # No discount
        )

        # With no discount, discount_scaled should be 0
        assert result.discount_scaled == 0, "Expected no discount"

        # Balance delta should still be negative
        assert result.balance_delta < 0, "Expected negative balance delta"

    def test_discount_accrual_calculation(self) -> None:
        """Verify interest accrual with discount is calculated correctly.

        When a user has a discount, the interest they owe is reduced by the
        discount percentage. This test verifies the accrue_debt_on_action
        calculation matches expected behavior.
        """
        processor = GhoV1Processor()

        # Simulate interest accrual with 15.26% discount
        previous_scaled_balance = 1000000000000000000000  # 1000 scaled
        previous_index = 1000000000000000000000000000
        current_index = 1000100000000000000000000000  # 0.1% growth
        discount_percent = 1526  # 15.26%

        discount_scaled = processor.accrue_debt_on_action(
            previous_scaled_balance=previous_scaled_balance,
            previous_index=previous_index,
            discount_percent=discount_percent,
            current_index=current_index,
        )

        # Calculate expected values
        wad_ray = processor.get_math_libraries()["wad_ray"]
        percentage = processor.get_math_libraries()["percentage"]

        # balanceIncrease = previousScaledBalance.rayMul(currentIndex) -
        #                   previousScaledBalance.rayMul(previousIndex)
        balance_increase = wad_ray.ray_mul(
            previous_scaled_balance, current_index
        ) - wad_ray.ray_mul(previous_scaled_balance, previous_index)

        # discount = balanceIncrease.percentMul(discountPercent)
        expected_discount = percentage.percent_mul(balance_increase, discount_percent)

        # discountScaled = discount.rayDiv(currentIndex)
        expected_discount_scaled = wad_ray.ray_div(expected_discount, current_index)

        assert discount_scaled == expected_discount_scaled, (
            f"Discount mismatch: got {discount_scaled}, expected {expected_discount_scaled}"
        )

    def test_gho_burn_discount_reset_scenario(self) -> None:
        """Test burn when discount is reset from non-zero to zero.

        This replicates the exact scenario from issue 0007 where a user's
        discount was reset from 15.26% to 0% during a repayment transaction.
        The key is that the OLD discount should be used for the accrual
        calculation, not the new (reset) discount.
        """
        processor = GhoV1Processor()

        # Simulate the repayment from issue 0007
        # User had 15.26% discount, was reset to 0% in same transaction
        # The OLD discount (15.26%) should be used for interest calculation

        # Interest has accrued, so previous_index < current_index
        previous_index = 1000000000000000000000000000  # Lower index
        current_index = 1000002876716465823842112176  # Higher index

        event_data = DebtBurnEvent(
            from_="0x84aC9de807CEFa7205b53108c705744dA523f901",
            target="0x0000000000000000000000000000000000000000",
            value=5499998829504419508388,
            balance_increase=1170495580491612,
            index=current_index,
        )

        previous_balance = 5499998829504419508388
        old_discount = 1526  # OLD discount before reset

        result = processor.process_burn_event(
            event_data=event_data,
            previous_balance=previous_balance,
            previous_index=previous_index,
            previous_discount=old_discount,
        )

        # Verify discount was applied using the OLD discount rate
        assert result.discount_scaled > 0, "Expected discount to be applied"

        # The balance delta should account for:
        # 1. The principal repayment (event_data.value)
        # 2. The interest accrual (balance_increase)
        # 3. Minus the discount on interest
        assert result.balance_delta < 0, "Expected debt reduction"

        # Verify the math: total_scaled = (value + balance_increase).rayDiv(index)
        wad_ray = processor.get_math_libraries()["wad_ray"]
        total_amount = event_data.value + event_data.balance_increase
        total_scaled = wad_ray.ray_div(total_amount, event_data.index)

        # The discount reduces the amount actually burned
        expected_balance_delta = -(total_scaled + result.discount_scaled)

        assert result.balance_delta == expected_balance_delta, (
            f"Balance delta mismatch: got {result.balance_delta}, expected {expected_balance_delta}"
        )
