"""Tests for MINT_TO_TREASURY operation handling.

These tests verify that mintToTreasury operations do not update
collateral positions for the treasury address.
"""

import pytest
from hexbytes import HexBytes
from web3.types import LogReceipt

from degenbot.cli.aave_transaction_operations import (
    AaveV3Event,
    OperationType,
    TransactionOperationsParser,
)
from degenbot.checksum_cache import get_checksum_address

# Test addresses
TEST_POOL = get_checksum_address("0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2")
TEST_TREASURY = get_checksum_address("0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c")
TEST_ATOKEN = get_checksum_address("0x0B925eD163218f6662a35e0f0371Ac234f9E9371")
TEST_RESERVE = get_checksum_address("0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0")

MINT_EVENT_TOPIC = HexBytes("0x458f5fa412d0f69b08dd84872b0215675cc67bc1d5b6fd93300a1c3878b86196")


def create_mint_event(
    caller: str,
    user: str,
    amount: int,
    balance_increase: int,
    index: int,
    log_index: int,
    token_address: str = TEST_ATOKEN,
) -> LogReceipt:
    """Create a Mint event for testing."""

    data = (
        amount.to_bytes(32, "big")
        + balance_increase.to_bytes(32, "big")
        + index.to_bytes(32, "big")
    )

    return {
        "address": token_address,
        "topics": [
            MINT_EVENT_TOPIC,
            HexBytes("0x" + "0" * 24 + caller[2:]),
            HexBytes("0x" + "0" * 24 + user[2:]),
        ],
        "data": data,
        "blockNumber": 16516952,
        "blockHash": HexBytes("0x" + "ab" * 32),
        "transactionHash": HexBytes("0x" + "cd" * 32),
        "transactionIndex": 0,
        "logIndex": log_index,
        "removed": False,
    }


class TestMintToTreasury:
    """Test mintToTreasury operation handling."""

    def test_mint_to_treasury_operation_created(self):
        """Test that MINT_TO_TREASURY operations are created correctly."""

        token_mapping = {TEST_ATOKEN: "aToken"}
        parser = TransactionOperationsParser(
            token_type_mapping=token_mapping,
            pool_address=TEST_POOL,
        )

        # Create a mint event where caller is Pool and user is Treasury
        mint_event = create_mint_event(
            caller=TEST_POOL,
            user=TEST_TREASURY,
            amount=1942944858625595,
            balance_increase=0,
            index=1000118049507356325074809392,
            log_index=10,
        )

        tx_hash = HexBytes("0x" + "12" * 32)
        tx_operations = parser.parse([mint_event], tx_hash)

        # Should create exactly one operation
        assert len(tx_operations.operations) == 1

        operation = tx_operations.operations[0]

        # Should be MINT_TO_TREASURY type
        assert operation.operation_type == OperationType.MINT_TO_TREASURY

        # Should have no pool event
        assert operation.pool_event is None

        # Should have exactly one scaled token event
        assert len(operation.scaled_token_events) == 1

        # The scaled token event should be COLLATERAL_MINT
        assert operation.scaled_token_events[0].event_type == "COLLATERAL_MINT"

        # The user should be the treasury
        assert operation.scaled_token_events[0].user_address == TEST_TREASURY

        # The caller should be the pool
        assert operation.scaled_token_events[0].caller_address == TEST_POOL

    def test_regular_supply_not_affected(self):
        """Test that regular SUPPLY operations are still created correctly."""

        token_mapping = {TEST_ATOKEN: "aToken"}
        parser = TransactionOperationsParser(
            token_type_mapping=token_mapping,
            pool_address=TEST_POOL,
        )

        user = get_checksum_address("0x1234567890123456789012345678901234567890")

        # Create a mint event where caller is NOT Pool (regular user supply)
        mint_event = create_mint_event(
            caller=user,  # User is the caller, not Pool
            user=user,
            amount=1000000000000000000,  # 1 token
            balance_increase=0,
            index=1000000000000000000000000000,
            log_index=10,
        )

        tx_hash = HexBytes("0x" + "34" * 32)
        tx_operations = parser.parse([mint_event], tx_hash)

        # Should NOT create a MINT_TO_TREASURY operation
        # (it might create an unassigned operation or no operation)
        mint_to_treasury_ops = [
            op
            for op in tx_operations.operations
            if op.operation_type == OperationType.MINT_TO_TREASURY
        ]
        assert len(mint_to_treasury_ops) == 0

    def test_multiple_mint_to_treasury_events(self):
        """Test handling multiple mintToTreasury events in one transaction."""

        token_mapping = {
            TEST_ATOKEN: "aToken",
            get_checksum_address("0x0987654321098765432109876543210987654321"): "aToken",
        }
        parser = TransactionOperationsParser(
            token_type_mapping=token_mapping,
            pool_address=TEST_POOL,
        )

        token2 = get_checksum_address("0x0987654321098765432109876543210987654321")

        # Create multiple mint events to treasury
        mint_event_1 = create_mint_event(
            caller=TEST_POOL,
            user=TEST_TREASURY,
            amount=1942944858625595,
            balance_increase=0,
            index=1000118049507356325074809392,
            log_index=10,
            token_address=TEST_ATOKEN,
        )

        mint_event_2 = create_mint_event(
            caller=TEST_POOL,
            user=TEST_TREASURY,
            amount=64747802839500,
            balance_increase=0,
            index=1000118049507356325074809392,
            log_index=20,
            token_address=token2,
        )

        tx_hash = HexBytes("0x" + "56" * 32)
        tx_operations = parser.parse([mint_event_1, mint_event_2], tx_hash)

        # Should create exactly two MINT_TO_TREASURY operations
        mint_to_treasury_ops = [
            op
            for op in tx_operations.operations
            if op.operation_type == OperationType.MINT_TO_TREASURY
        ]
        assert len(mint_to_treasury_ops) == 2

    def test_mint_to_treasury_in_liquidation_transaction(self):
        """Test MINT_TO_TREASURY detection when Mint event appears in a liquidation transaction.

        This reproduces the bug from transaction 0xf89d68692625fa37f7e7d2a10f7f8763434938bfa2005c9e94716ac2a7372aec
        where a Mint event with caller=Pool and user=Treasury was not being detected as MINT_TO_TREASURY.
        """

        # Real addresses from the transaction
        POOL = get_checksum_address("0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2")
        TREASURY = get_checksum_address("0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c")
        aWETH = get_checksum_address("0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8")
        LIQUIDATED_USER = get_checksum_address("0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D")
        LIQUIDATOR = get_checksum_address("0x3697E949A4d9a507A6Ce2f6ff6bB99Bcc8EaCb81")
        WETH = get_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
        DAI = get_checksum_address("0x6B175474E89094C44Da98b954EedeAC495271d0F")

        token_mapping = {aWETH: "aToken"}
        parser = TransactionOperationsParser(
            token_type_mapping=token_mapping,
            pool_address=POOL,
        )

        # Create the liquidation transaction events (in order of logIndex)
        events = []

        # Event 147: Burn - user's collateral being burned
        burn_event = {
            "address": aWETH,
            "topics": [
                AaveV3Event.SCALED_TOKEN_BURN.value,
                HexBytes("0x" + "0" * 24 + LIQUIDATED_USER[2:]),
                HexBytes("0x" + "0" * 24 + LIQUIDATOR[2:]),
            ],
            "data": (
                (857051950632003076).to_bytes(32, "big")  # amount
                + (411586787509754).to_bytes(32, "big")  # balanceIncrease
                + (1000158838985426411575163392).to_bytes(32, "big")  # index
            ),
            "blockNumber": 16521648,
            "blockHash": HexBytes("0x" + "ab" * 32),
            "transactionHash": HexBytes("0x" + "cd" * 32),
            "transactionIndex": 0,
            "logIndex": 147,
            "removed": False,
        }
        events.append(burn_event)

        # Event 150: Mint - protocol fee to treasury (this is the problematic one)
        mint_event = {
            "address": aWETH,
            "topics": [
                MINT_EVENT_TOPIC,
                HexBytes("0x" + "0" * 24 + POOL[2:]),  # caller = Pool
                HexBytes("0x" + "0" * 24 + TREASURY[2:]),  # user = Treasury
            ],
            "data": (
                (2239091028604).to_bytes(32, "big")  # amount
                + (2239091028604).to_bytes(32, "big")  # balanceIncrease
                + (1000158838985426411575163392).to_bytes(32, "big")  # index
            ),
            "blockNumber": 16521648,
            "blockHash": HexBytes("0x" + "ab" * 32),
            "transactionHash": HexBytes("0x" + "cd" * 32),
            "transactionIndex": 0,
            "logIndex": 150,
            "removed": False,
        }
        events.append(mint_event)

        # Event 154: LiquidationCall - the pool event
        liquidation_event = {
            "address": POOL,
            "topics": [
                AaveV3Event.LIQUIDATION_CALL.value,
                HexBytes("0x" + "0" * 24 + WETH[2:]),  # collateralAsset
                HexBytes("0x" + "0" * 24 + DAI[2:]),  # debtAsset
                HexBytes("0x" + "0" * 24 + LIQUIDATED_USER[2:]),  # user
            ],
            "data": (
                (1265883725747618387045).to_bytes(32, "big")  # debtToCover
                + (857463537419512830).to_bytes(32, "big")  # liquidatedCollateralAmount
                + HexBytes("0x" + "0" * 24 + LIQUIDATOR[2:])  # liquidator
                + (0).to_bytes(32, "big")  # receiveAToken (false)
            ),
            "blockNumber": 16521648,
            "blockHash": HexBytes("0x" + "ab" * 32),
            "transactionHash": HexBytes("0x" + "cd" * 32),
            "transactionIndex": 0,
            "logIndex": 154,
            "removed": False,
        }
        events.append(liquidation_event)

        tx_hash = HexBytes("0x" + "ef" * 32)
        tx_operations = parser.parse(events, tx_hash)

        # Should create exactly 2 operations:
        # 1. LIQUIDATION operation with the burn
        # 2. MINT_TO_TREASURY operation with the mint
        assert len(tx_operations.operations) == 2, (
            f"Expected 2 operations, got {len(tx_operations.operations)}: {[op.operation_type for op in tx_operations.operations]}"
        )

        # Find the MINT_TO_TREASURY operation
        mint_to_treasury_ops = [
            op
            for op in tx_operations.operations
            if op.operation_type == OperationType.MINT_TO_TREASURY
        ]
        assert len(mint_to_treasury_ops) == 1, (
            f"Expected 1 MINT_TO_TREASURY operation, got {len(mint_to_treasury_ops)}"
        )

        mint_op = mint_to_treasury_ops[0]
        assert mint_op.pool_event is None
        assert len(mint_op.scaled_token_events) == 1
        assert mint_op.scaled_token_events[0].event_type == "COLLATERAL_MINT"
        assert mint_op.scaled_token_events[0].user_address == TREASURY
        assert mint_op.scaled_token_events[0].caller_address == POOL

        # Find the LIQUIDATION operation
        liquidation_ops = [
            op for op in tx_operations.operations if op.operation_type == OperationType.LIQUIDATION
        ]
        assert len(liquidation_ops) == 1, (
            f"Expected 1 LIQUIDATION operation, got {len(liquidation_ops)}"
        )

        liq_op = liquidation_ops[0]
        assert liq_op.pool_event is not None
        assert len(liq_op.scaled_token_events) == 1  # Just the burn
        assert liq_op.scaled_token_events[0].event_type == "COLLATERAL_BURN"

    def test_mint_to_treasury_with_transfer_events(self):
        """Test that Transfer events to treasury are handled correctly alongside MINT_TO_TREASURY.

        This tests the scenario where both a Mint and a Transfer event go to the treasury
        in the same liquidation transaction.
        """

        # Real addresses from the transaction
        POOL = get_checksum_address("0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2")
        TREASURY = get_checksum_address("0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c")
        aWETH = get_checksum_address("0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8")
        LIQUIDATED_USER = get_checksum_address("0x23dB246031fd6F4e81B0814E9C1DC0901a18Da2D")
        LIQUIDATOR = get_checksum_address("0x3697E949A4d9a507A6Ce2f6ff6bB99Bcc8EaCb81")
        WETH = get_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
        DAI = get_checksum_address("0x6B175474E89094C44Da98b954EedeAC495271d0F")

        TRANSFER_TOPIC = HexBytes(
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        )

        token_mapping = {aWETH: "aToken"}
        parser = TransactionOperationsParser(
            token_type_mapping=token_mapping,
            pool_address=POOL,
        )

        # Create the transaction events (in order of logIndex)
        events = []

        # Event 147: Burn - user's collateral being burned
        burn_event = {
            "address": aWETH,
            "topics": [
                AaveV3Event.SCALED_TOKEN_BURN.value,
                HexBytes("0x" + "0" * 24 + LIQUIDATED_USER[2:]),
                HexBytes("0x" + "0" * 24 + LIQUIDATOR[2:]),
            ],
            "data": (
                (857051950632003076).to_bytes(32, "big")  # amount
                + (411586787509754).to_bytes(32, "big")  # balanceIncrease
                + (1000158838985426411575163392).to_bytes(32, "big")  # index
            ),
            "blockNumber": 16521648,
            "blockHash": HexBytes("0x" + "ab" * 32),
            "transactionHash": HexBytes("0x" + "cd" * 32),
            "transactionIndex": 0,
            "logIndex": 147,
            "removed": False,
        }
        events.append(burn_event)

        # Event 150: Mint - protocol fee to treasury
        mint_event = {
            "address": aWETH,
            "topics": [
                MINT_EVENT_TOPIC,
                HexBytes("0x" + "0" * 24 + POOL[2:]),  # caller = Pool
                HexBytes("0x" + "0" * 24 + TREASURY[2:]),  # user = Treasury
            ],
            "data": (
                (2239091028604).to_bytes(32, "big")  # amount
                + (2239091028604).to_bytes(32, "big")  # balanceIncrease
                + (1000158838985426411575163392).to_bytes(32, "big")  # index
            ),
            "blockNumber": 16521648,
            "blockHash": HexBytes("0x" + "ab" * 32),
            "transactionHash": HexBytes("0x" + "cd" * 32),
            "transactionIndex": 0,
            "logIndex": 150,
            "removed": False,
        }
        events.append(mint_event)

        # Event 151: Transfer - liquidation bonus from user to treasury
        transfer_event = {
            "address": aWETH,
            "topics": [
                TRANSFER_TOPIC,
                HexBytes("0x" + "0" * 24 + LIQUIDATED_USER[2:]),  # from = liquidated user
                HexBytes("0x" + "0" * 24 + TREASURY[2:]),  # to = treasury
            ],
            "data": (
                (4102696351289535).to_bytes(32, "big")  # amount
            ),
            "blockNumber": 16521648,
            "blockHash": HexBytes("0x" + "ab" * 32),
            "transactionHash": HexBytes("0x" + "cd" * 32),
            "transactionIndex": 0,
            "logIndex": 151,
            "removed": False,
        }
        events.append(transfer_event)

        # Event 154: LiquidationCall - the pool event
        liquidation_event = {
            "address": POOL,
            "topics": [
                AaveV3Event.LIQUIDATION_CALL.value,
                HexBytes("0x" + "0" * 24 + WETH[2:]),  # collateralAsset
                HexBytes("0x" + "0" * 24 + DAI[2:]),  # debtAsset
                HexBytes("0x" + "0" * 24 + LIQUIDATED_USER[2:]),  # user
            ],
            "data": (
                (1265883725747618387045).to_bytes(32, "big")  # debtToCover
                + (857463537419512830).to_bytes(32, "big")  # liquidatedCollateralAmount
                + HexBytes("0x" + "0" * 24 + LIQUIDATOR[2:])  # liquidator
                + (0).to_bytes(32, "big")  # receiveAToken (false)
            ),
            "blockNumber": 16521648,
            "blockHash": HexBytes("0x" + "ab" * 32),
            "transactionHash": HexBytes("0x" + "cd" * 32),
            "transactionIndex": 0,
            "logIndex": 154,
            "removed": False,
        }
        events.append(liquidation_event)

        tx_hash = HexBytes("0x" + "ef" * 32)
        tx_operations = parser.parse(events, tx_hash)

        # Debug: print all operations
        print(f"\nNumber of operations: {len(tx_operations.operations)}")
        for i, op in enumerate(tx_operations.operations):
            print(f"  Operation {i}: {op.operation_type}")
            print(f"    Scaled token events: {[ev.event_type for ev in op.scaled_token_events]}")
            print(f"    Pool event: {op.pool_event is not None}")

        # Should create at least 2 operations:
        # 1. LIQUIDATION operation with the burn
        # 2. MINT_TO_TREASURY operation with the mint
        # 3. Possibly a BALANCE_TRANSFER operation with the transfer
        assert len(tx_operations.operations) >= 2, (
            f"Expected at least 2 operations, got {len(tx_operations.operations)}"
        )

        # Find the MINT_TO_TREASURY operation
        mint_to_treasury_ops = [
            op
            for op in tx_operations.operations
            if op.operation_type == OperationType.MINT_TO_TREASURY
        ]
        assert len(mint_to_treasury_ops) == 1, (
            f"Expected 1 MINT_TO_TREASURY operation, got {len(mint_to_treasury_ops)}"
        )

        # Find the LIQUIDATION operation
        liquidation_ops = [
            op for op in tx_operations.operations if op.operation_type == OperationType.LIQUIDATION
        ]
        assert len(liquidation_ops) == 1, (
            f"Expected 1 LIQUIDATION operation, got {len(liquidation_ops)}"
        )
