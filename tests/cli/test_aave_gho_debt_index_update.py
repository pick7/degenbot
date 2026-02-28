"""Test GHO debt index update from Mint events.

See debug/aave/0010 - GHO Debt Index Update Bug in process_gho_debt_mint_event.md
"""

import pytest
from degenbot.aave.processors.debt.gho.v1 import GhoV1Processor
from degenbot.aave.processors.base import DebtMintEvent


class TestGhoDebtIndexUpdate:
    """Test that GHO debt index is correctly updated from Mint events.

    Bug report: debug/aave/0010
    The _process_gho_debt_mint_event function was fetching the index from the
    Pool contract instead of using the index from the Mint event (via processor).
    """

    def test_mint_event_index_extraction(self):
        """Verify that the processor extracts the correct index from Mint events."""
        processor = GhoV1Processor()

        # Mint event data from transaction 0x7120d824085292eafa6d540a17386f4a09168c658d17ea47d2705cd002a81636
        # Block 17859071 - GHO Variable Debt Token
        event_index = 1000919954862378321350351390  # Correct current global index

        event_data = DebtMintEvent(
            caller="0x0000000000000000000000000000000000000000",  # ZERO_ADDRESS
            on_behalf_of="0x0fd3E4B5FcaC38ba6E48e9c7703805679eDFCcC4",
            value=0,  # No actual mint, just index update
            balance_increase=0,  # Pure interest accrual / index update
            index=event_index,
            scaled_amount=None,
        )

        # Process the mint event
        result = processor.process_mint_event(
            event_data=event_data,
            previous_balance=1000000000000000000,  # Some existing balance
            previous_index=1000919640646688461729030319,  # Old index
            previous_discount=0,
        )

        # Verify the processor returns the correct new_index
        assert result.new_index == event_index, (
            f"Processor returned wrong index: {result.new_index} != {event_index}"
        )

    def test_mint_event_zero_values(self):
        """Test Mint events with value=0 and balanceIncrease=0 (index updates)."""
        processor = GhoV1Processor()

        # This simulates a Mint event triggered by stkAAVE activity
        # where no actual tokens are minted, but the user's index is updated
        # When both value and balanceIncrease are 0, value >= balanceIncrease
        # so this is treated as a borrow operation with 0 amount
        event_data = DebtMintEvent(
            caller="0x0000000000000000000000000000000000000000",
            on_behalf_of="0x0fd3E4B5FcaC38ba6E48e9c7703805679eDFCcC4",
            value=0,
            balance_increase=0,
            index=1000919954862378321350351390,
            scaled_amount=None,
        )

        result = processor.process_mint_event(
            event_data=event_data,
            previous_balance=5000000000000000000,
            previous_index=1000919640646688461729030319,
            previous_discount=1000,  # 10% discount
        )

        # When value == balanceIncrease == 0, value >= balance_increase is True
        # So it's processed as a BORROW with 0 amount
        # The key point is that the index is correctly extracted
        assert result.new_index == 1000919954862378321350351390

    def test_processor_uses_event_index_not_calculated(self):
        """Verify processor uses the event index, not a calculated value."""
        processor = GhoV1Processor()

        # Use a clearly distinct index value
        test_index = 123456789012345678901234567890

        event_data = DebtMintEvent(
            caller="0x0000000000000000000000000000000000000000",
            on_behalf_of="0x1234567890123456789012345678901234567890",
            value=1000000000000000000,  # Borrowing 1 token
            balance_increase=500000000000000000,  # Some interest accrued
            index=test_index,
            scaled_amount=None,
        )

        result = processor.process_mint_event(
            event_data=event_data,
            previous_balance=0,
            previous_index=0,
            previous_discount=0,
        )

        # The processor should return the exact index from the event
        assert result.new_index == test_index, (
            f"Processor should use event index exactly, got {result.new_index} instead of {test_index}"
        )


class TestDebtIndexEncoding:
    """Test that debt indices are correctly encoded/decoded."""

    def test_index_from_hex(self):
        """Test decoding the index from transaction event data."""
        # From transaction 0x7120d824085292eafa6d540a17386f4a09168c658d17ea47d2705cd002a81636
        # Mint event data (last 32 bytes = index):
        # 0x000000000000000000000000000000000000000000000000033bf10b7a2ff390851dda1e
        hex_index = "0x000000000000000000000000000000000000000000000000033bf10b7a2ff390851dda1e"
        decoded_index = int(hex_index, 16)
        expected_index = 1000919954862378321350351390

        assert decoded_index == expected_index, (
            f"Index decoding failed: {decoded_index} != {expected_index}"
        )

    def test_database_vs_contract_index(self):
        """Document the index discrepancy from the bug report."""
        database_index = 1000919640646688461729030319  # Wrong value in DB
        contract_index = 1000919954862378321350351390  # Correct value from contract
        event_index = 1000919954862378321350351390  # Value from Mint event

        # The database had the wrong value
        assert database_index != contract_index

        # The event had the correct value
        assert event_index == contract_index

        # The difference
        difference = contract_index - database_index
        assert difference == 314215689859621321071


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
