"""
Test for Issue 0009 - Debt Swap Transaction Processing.

Reference: debug/aave/0009 - Debt Swap Transaction Processing.md

This test verifies the correct processing of a debt swap transaction where:
1. A user swaps USDC debt for BAL debt using a flash loan
2. The swapper borrows BAL on behalf of the user
3. The transaction includes both Mint and Burn events for the BAL debt token

Transaction: 0xa044d93a1aced198395d3293d4456fcb09a9a734d2949b5e2dff66338fa89625
Block: 17996836
Token: BAL Variable Debt Token (0x3D3efceb4Ff0966D34d9545D3A2fa2dcdBf451f2)
User: 0xC5Ec4153F98729f4eaf61013B54B704Eb282ECF4
Token Revision: 5
"""

import pytest

from degenbot.aave.libraries import wad_ray_math
from degenbot.aave.processors.base import BurnResult, DebtBurnEvent, DebtMintEvent, MintResult
from degenbot.aave.processors.debt.v5 import DebtV5Processor


class TestIssue0009DebtSwap:
    """Test debt swap transaction processing for Issue 0009."""

    @pytest.fixture
    def processor(self) -> DebtV5Processor:
        """Create a DebtV5Processor instance."""
        return DebtV5Processor()

    def test_mint_event_calculation(self, processor: DebtV5Processor) -> None:
        """
        Test that Mint event values are correctly converted to scaled amounts.

        The Mint event in the debt swap has:
        - value = 1,363,704,425,086,802,700 (amountToMint)
        - balanceIncrease = 44,551,487 (interest accrued)
        - index = 1068666840869650537514145061

        The borrowed underlying amount = value - balanceIncrease
        The scaled amount = ceiling(borrowed_underlying * 1e27 / index)
        """
        # Event data from transaction
        mint_event = DebtMintEvent(
            caller="0x8f30ADaA6950b31f675bF8a709Bc23F55aa24735",
            on_behalf_of="0xC5Ec4153F98729f4eaf61013B54B704Eb282ECF4",
            value=1363704425086802700,
            balance_increase=44551487,
            index=1068666840869650537514145061,
        )

        result: MintResult = processor.process_mint_event(
            event_data=mint_event,
            previous_balance=0,  # Not used for calculation
            previous_index=0,  # Not used for calculation
        )

        # Verify it's detected as a BORROW (value > balance_increase)
        assert result.is_repay is False

        # Calculate expected scaled amount
        borrowed_underlying = mint_event.value - mint_event.balance_increase
        expected_scaled = wad_ray_math.ray_div_ceil(borrowed_underlying, mint_event.index)

        assert result.balance_delta == expected_scaled
        assert result.new_index == mint_event.index

    def test_burn_event_calculation(self, processor: DebtV5Processor) -> None:
        """
        Test that Burn event values are correctly converted to scaled amounts.

        The Burn event in the debt swap has:
        - value = 1,363,745,535,260,938,187 (amountToBurn)
        - balanceIncrease = 0 (interest already accounted in Mint)
        - index = 1068666840869650537514145061

        The repaid underlying amount = value
        The scaled amount = floor(repaid_underlying * 1e27 / index)
        """
        # Event data from transaction
        burn_event = DebtBurnEvent(
            from_="0xC5Ec4153F98729f4eaf61013B54B704Eb282ECF4",
            target="0x0000000000000000000000000000000000000000",
            value=1363745535260938187,
            balance_increase=0,
            index=1068666840869650537514145061,
        )

        result: BurnResult = processor.process_burn_event(
            event_data=burn_event,
            previous_balance=0,  # Not used for calculation
            previous_index=0,  # Not used for calculation
        )

        # Calculate expected scaled amount
        repaid_underlying = burn_event.value + burn_event.balance_increase
        expected_scaled = wad_ray_math.ray_div_floor(repaid_underlying, burn_event.index)

        # Burn should decrease balance (negative delta)
        assert result.balance_delta == -expected_scaled
        assert result.new_index == burn_event.index

    def test_net_balance_change(self, processor: DebtV5Processor) -> None:
        """
        Test that the net balance change from the debt swap is correct.

        In this transaction:
        - Mint adds ~1,276,080,039,998,721,792 scaled units
        - Burn removes ~1,276,118,508,693,655,296 scaled units
        - Net change should be approximately -38,468,694,933,504 scaled units
          (debt decreases slightly)
        """
        mint_event = DebtMintEvent(
            caller="0x8f30ADaA6950b31f675bF8a709Bc23F55aa24735",
            on_behalf_of="0xC5Ec4153F98729f4eaf61013B54B704Eb282ECF4",
            value=1363704425086802700,
            balance_increase=44551487,
            index=1068666840869650537514145061,
        )

        burn_event = DebtBurnEvent(
            from_="0xC5Ec4153F98729f4eaf61013B54B704Eb282ECF4",
            target="0x0000000000000000000000000000000000000000",
            value=1363745535260938187,
            balance_increase=0,
            index=1068666840869650537514145061,
        )

        mint_result = processor.process_mint_event(
            event_data=mint_event,
            previous_balance=0,
            previous_index=0,
        )

        burn_result = processor.process_burn_event(
            event_data=burn_event,
            previous_balance=0,
            previous_index=0,
        )

        # Calculate net change
        net_change = mint_result.balance_delta + burn_result.balance_delta

        # The net change should be negative (more burned than minted)
        assert net_change < 0

        # The exact expected value (calculated from event data)
        expected_net = -38468694933510
        assert net_change == expected_net, f"Net change {net_change} != expected {expected_net}"

        # Verify the event structure
        assert mint_event.caller != mint_event.on_behalf_of
        assert mint_event.value > mint_event.balance_increase  # BORROW path

        result = processor.process_mint_event(
            event_data=mint_event,
            previous_balance=961160985395385548453,  # Starting balance from DB
            previous_index=1068666840869650537514145061,
        )

        # Result should indicate this is a borrow (not repay)
        assert result.is_repay is False

        # Balance should increase (we're borrowing)
        assert result.balance_delta > 0


# Additional integration test that could be added:
# - Test the full transaction processing pipeline with real event data
# - Verify the balance after processing both Mint and Burn events
# - Ensure the final balance matches the on-chain state
