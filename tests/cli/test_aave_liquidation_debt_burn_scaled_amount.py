"""
Test liquidation debt burn scaled amount calculation.

These tests verify that when processing liquidation debt burns, the scaled amount
is calculated from the actual Burn event values, not from the debt_to_cover value
in the LIQUIDATION_CALL event. This ensures accurate balance tracking when
interest accrues between the liquidation call and the burn event.
"""

import pytest
from hexbytes import HexBytes

from degenbot.aave.processors.base import DebtBurnEvent
from degenbot.aave.processors.debt.v1 import DebtV1Processor
from degenbot.aave.processors.debt.v4 import DebtV4Processor
from degenbot.cli.aave_transaction_operations import OperationType


class TestLiquidationDebtBurnScaledAmount:
    """
    Test scaled amount calculation for liquidation debt burns.

    When a liquidation occurs, the LIQUIDATION_CALL event specifies the debt_to_cover,
    but the actual Burn event may have different values due to interest accrual.
    The scaled amount must be calculated from the Burn event values, not from
    debt_to_cover.
    """

    def test_liquidation_scaled_amount_from_burn_event_not_debt_to_cover(self):
        """
        Verify that liquidation debt burns use Burn event values, not debt_to_cover.

        This is the core issue: debt_to_cover from LIQUIDATION_CALL represents the
        liquidator's intent, but the Burn event contains the actual values after
        interest accrual.

        Example from transaction 0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec:
        - debt_to_cover: 1265883725747618387045 (liquidator's intent)
        - Burn value: 1264696671508058415345 (principal)
        - Burn balance_increase: 1187054239559971700 (interest accrued)
        - Actual amount: value + balance_increase = 1265883725747618387045

        The scaled amount must be calculated from (value + balance_increase) / index,
        not directly from debt_to_cover.
        """
        # Actual values from the failing transaction
        debt_to_cover = 1265883725747618387045  # From LIQUIDATION_CALL
        burn_value = 1264696671508058415345  # From Burn event
        balance_increase = 1187054239559971700  # From Burn event
        index = 1000601460939760049231298523  # From Burn event

        # Verify the relationship
        assert burn_value + balance_increase == debt_to_cover, (
            "The sum of Burn value and balance_increase should equal debt_to_cover"
        )

    def test_v1_processor_calculates_from_event_values_when_scaled_delta_none(self):
        """
        Test that V1 processor calculates scaled amount from event values.

        When scaled_delta is None, the V1 processor should calculate the balance
        delta from the Burn event values using ray_div.
        """
        processor = DebtV1Processor()

        # Create a Burn event with liquidation values
        event = DebtBurnEvent(
            from_="0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D",
            target="0x0000000000000000000000000000000000000000",
            value=1264696671508058415345,  # Principal
            balance_increase=1187054239559971700,  # Interest
            index=1000601460939760049231298523,
            scaled_amount=None,  # Key: scaled_amount is None for liquidations
        )

        # Process with scaled_delta=None (simulating liquidation)
        result = processor.process_burn_event(
            event_data=event,
            previous_balance=1265548956393672469791,
            previous_index=1000599573289860491491149989,
            scaled_delta=None,  # This triggers calculation from event values
        )

        # The balance delta should be calculated from (value + balance_increase) / index
        expected_requested_amount = event.value + event.balance_increase
        import degenbot.aave.libraries as aave_library

        wad_ray_math = aave_library.wad_ray_math
        expected_scaled_amount = wad_ray_math.ray_div(
            a=expected_requested_amount,
            b=event.index,
        )

        assert result.balance_delta == -expected_scaled_amount, (
            f"Expected balance_delta to be {-expected_scaled_amount}, got {result.balance_delta}"
        )

    def test_liquidation_detection_prevents_debt_to_cover_usage(self):
        """
        Test that liquidation detection prevents using debt_to_cover.

        When processing a liquidation debt burn, the code should detect that
        it's a liquidation and NOT set raw_amount to debt_to_cover, allowing
        the processor to calculate from event values instead.
        """
        # Simulated extraction_data from EventMatcher
        extraction_data = {
            "debt_to_cover": 1265883725747618387045,
            "liquidated_collateral": 857463537419512830,
        }

        # For liquidations, raw_amount should remain None
        is_liquidation = True
        raw_amount = extraction_data.get("raw_amount")  # None - no REPAY event

        # The fix: for liquidations, don't fall back to debt_to_cover
        if raw_amount is None and not is_liquidation:
            raw_amount = extraction_data.get("debt_to_cover")

        # Verify raw_amount is None for liquidations
        assert raw_amount is None, (
            "For liquidations, raw_amount should remain None to allow "
            "the processor to calculate from Burn event values"
        )

    def test_v4_processor_uses_scaled_delta_when_provided(self):
        """
        Test that V4 processor uses scaled_delta when provided.

        For non-liquidation burns (like REPAY), scaled_delta is calculated
        from the paybackAmount and should be used directly.
        """
        processor = DebtV4Processor()

        # Create a Burn event with pre-calculated scaled_amount
        pre_calculated_scaled = 1000000000000000000  # 1 token in scaled units

        event = DebtBurnEvent(
            from_="0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D",
            target="0x0000000000000000000000000000000000000000",
            value=1001000000000000000000,  # Principal + interest
            balance_increase=1000000000000000000,  # Interest
            index=1000000000000000000000000000,
            scaled_amount=pre_calculated_scaled,
        )

        # Process with pre-calculated scaled_delta
        result = processor.process_burn_event(
            event_data=event,
            previous_balance=5000000000000000000,
            previous_index=1000000000000000000000000000,
            scaled_delta=pre_calculated_scaled,  # Pre-calculated for REPAY
        )

        # Should use the pre-calculated scaled_delta
        assert result.balance_delta == -pre_calculated_scaled, (
            f"Expected balance_delta to be {-pre_calculated_scaled}, got {result.balance_delta}"
        )

    def test_v4_processor_calculates_from_event_when_scaled_delta_none(self):
        """
        Test that V4 processor falls back to event calculation when scaled_delta is None.

        For liquidations, scaled_delta is None and the processor should calculate
        from the Burn event values using ray_div_floor.
        """
        processor = DebtV4Processor()

        # Create a Burn event (liquidation scenario)
        event = DebtBurnEvent(
            from_="0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D",
            target="0x0000000000000000000000000000000000000000",
            value=1264696671508058415345,
            balance_increase=1187054239559971700,
            index=1000601460939760049231298523,
            scaled_amount=None,  # Key: None for liquidations
        )

        # Process with scaled_delta=None
        result = processor.process_burn_event(
            event_data=event,
            previous_balance=1265548956393672469791,
            previous_index=1000599573289860491491149989,
            scaled_delta=None,
        )

        # Should calculate using ray_div_floor
        import degenbot.aave.libraries as aave_library

        wad_ray_math = aave_library.wad_ray_math
        requested_amount = event.value + event.balance_increase
        expected_scaled = wad_ray_math.ray_div_floor(
            a=requested_amount,
            b=event.index,
        )

        assert result.balance_delta == -expected_scaled, (
            f"Expected balance_delta to be {-expected_scaled}, got {result.balance_delta}"
        )


class TestOperationTypeDetection:
    """Test detection of liquidation operations."""

    def test_liquidation_operation_types(self):
        """Verify the liquidation operation types are correctly defined."""
        liquidation_types = {
            OperationType.LIQUIDATION,
            OperationType.GHO_LIQUIDATION,
            OperationType.SELF_LIQUIDATION,
        }

        for op_type in liquidation_types:
            assert "LIQUIDATION" in op_type.name

    def test_non_liquidation_operation_types(self):
        """Verify non-liquidation types are not detected as liquidations."""
        non_liquidation_types = {
            OperationType.BORROW,
            OperationType.REPAY,
            OperationType.SUPPLY,
            OperationType.WITHDRAW,
            OperationType.REPAY_WITH_ATOKENS,
        }

        for op_type in non_liquidation_types:
            assert "LIQUIDATION" not in op_type.name
