"""Test interest accrual during repayment (balance_increase > amount)."""

import pytest
from eth_abi.abi import encode
from hexbytes import HexBytes

from degenbot.cli.aave_transaction_operations import (
    AaveV3Event,
    OperationType,
    TransactionOperationsParser,
)
from degenbot.functions import get_checksum_address

USDT_VTOKEN = get_checksum_address("0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8")


@pytest.fixture
def token_type_mapping():
    """Token type mapping for tests."""
    return {
        USDT_VTOKEN: "vToken",
    }


class TestInterestAccrualDuringRepay:
    """Test that interest accrual during repayment is processed correctly.

    When a user repays variable debt and the accrued interest exceeds the
    repayment amount, the Aave contract emits a Mint event where:
    - value = balanceIncrease - amount (net interest after repayment)
    - balanceIncrease = total interest accrued

    This should be processed as INTEREST_ACCRUAL, not as part of REPAY.

    Reference: See debug/aave/0003 - Interest Accrual During Repayment Not Processed.md
    Transaction: 0x96b71f9698a072992a4e0a4ed1ade34c1872911dda9790d94946fa38360d302d
    """

    def test_interest_accrual_during_repay_creates_separate_operation(self, token_type_mapping):
        """When balance_increase > amount during repay, create INTEREST_ACCRUAL."""

        tx_hash = HexBytes("0x96b71f9698a072992a4e0a4ed1ade34c1872911dda9790d94946fa38360d302d")

        pool = get_checksum_address("0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2")
        user = get_checksum_address("0xE873793b15e6bEc6c7118D8125E40C122D46714D")
        reserve = get_checksum_address("0xdAC17F958D2ee523a2206206994597C13D831ec7")
        v_token = USDT_VTOKEN

        # Mint event: value=26804, balance_increase=26904 (interest > repayment)
        # This represents 100 USDT repayment with 26,904 interest, netting 26,804 minted
        mint_amount = 26804
        balance_increase = 26904
        index = 1007658527025333702923623478

        mint_event = {
            "address": v_token,
            "topics": [
                AaveV3Event.SCALED_TOKEN_MINT.value,
                HexBytes(
                    encode(
                        types=["address"],
                        args=[user],
                    )
                ),
                HexBytes(
                    encode(
                        types=["address"],
                        args=[user],
                    )
                ),
            ],
            "data": HexBytes(
                encode(
                    types=["uint256", "uint256", "uint256"],
                    args=[mint_amount, balance_increase, index],
                )
            ),
            "logIndex": 183,
            "blockNumber": 16_910_244,
            "transactionHash": tx_hash,
        }

        # Repay event
        repay_amount = 100
        use_a_tokens = False

        repay_event = {
            "address": pool,
            "topics": [
                AaveV3Event.REPAY.value,
                HexBytes(
                    encode(
                        types=["address"],
                        args=[reserve],
                    )
                ),
                HexBytes(
                    encode(
                        types=["address"],
                        args=[user],
                    )
                ),
            ],
            "data": HexBytes(
                encode(
                    types=["uint256", "bool"],
                    args=[repay_amount, use_a_tokens],
                )
            ),
            "logIndex": 186,
            "blockNumber": 16910244,
            "transactionHash": tx_hash,
        }

        parser = TransactionOperationsParser(token_type_mapping=token_type_mapping)
        tx_ops = parser.parse(
            events=[mint_event, repay_event],
            tx_hash=tx_hash,
        )

        # Should create 2 operations: REPAY + INTEREST_ACCRUAL
        assert len(tx_ops.operations) == 2

        repay_op, interest_op = tx_ops.operations

        assert repay_op.operation_type == OperationType.REPAY
        assert interest_op.operation_type == OperationType.INTEREST_ACCRUAL

        # INTEREST_ACCRUAL should contain the debt mint
        debt_mints = [e for e in interest_op.scaled_token_events if e.is_debt]
        assert len(debt_mints) == 1

        (mint,) = debt_mints
        assert mint.amount == 26804
        assert mint.balance_increase == 26904
        assert mint.balance_increase > mint.amount  # Key: interest > repayment

        # Validation should pass
        tx_ops.validate([mint_event, repay_event])
        assert repay_op.is_valid()
        assert interest_op.is_valid()
