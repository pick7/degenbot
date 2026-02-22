"""Aave V3 transaction operation parser.

Parses transaction events into logical operations based on asset flows.
Provides strict validation with detailed plain-text error reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TypedDict

import eth_abi
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3.types import LogReceipt

from degenbot.checksum_cache import get_checksum_address

# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================


class OperationType(Enum):
    """Types of Aave operations based on asset flows."""

    # Standard operations
    SUPPLY = auto()  # SUPPLY -> COLLATERAL_MINT
    WITHDRAW = auto()  # WITHDRAW -> COLLATERAL_BURN
    BORROW = auto()  # BORROW -> DEBT_MINT
    REPAY = auto()  # REPAY -> DEBT_BURN

    # Composite operations
    REPAY_WITH_ATOKENS = auto()  # REPAY -> DEBT_BURN + COLLATERAL_BURN
    LIQUIDATION = auto()  # LIQUIDATION_CALL -> DEBT_BURN + COLLATERAL_BURN
    SELF_LIQUIDATION = auto()  # LIQUIDATION_CALL -> DEBT_MINT + COLLATERAL_MINT

    # GHO-specific operations
    GHO_BORROW = auto()  # BORROW -> GHO_DEBT_MINT
    GHO_REPAY = auto()  # REPAY -> GHO_DEBT_BURN
    GHO_LIQUIDATION = auto()  # LIQUIDATION_CALL -> GHO_DEBT_BURN + COLLATERAL_BURN
    GHO_FLASH_LOAN = auto()  # DEFICIT_CREATED -> GHO_DEBT_BURN

    # Standalone events
    INTEREST_ACCRUAL = auto()  # Mint/Burn with no pool event
    BALANCE_TRANSFER = auto()  # Standalone BalanceTransfer
    UNKNOWN = auto()


class AaveV3Event(Enum):
    """Aave V3 Pool event topic hashes."""

    SUPPLY = HexBytes("0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61")
    WITHDRAW = HexBytes("0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7")
    BORROW = HexBytes("0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0")
    REPAY = HexBytes("0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051")
    LIQUIDATION_CALL = HexBytes(
        "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"
    )
    DEFICIT_CREATED = HexBytes("0x2bccfb3fad376d59d7accf970515eb77b2f27b082c90ed0fb15583dd5a942699")

    # Scaled token events
    SCALED_TOKEN_MINT = HexBytes(
        "0x458f5fa412d0f69b08dd84872b0215675cc67bc1d5b6fd93300a1c3878b86196"
    )
    SCALED_TOKEN_BURN = HexBytes(
        "0x4cf25bc1d991c17529c25213d3cc0cda295eeaad5f13f361969b12ea48015f90"
    )
    SCALED_TOKEN_BALANCE_TRANSFER = HexBytes(
        "0x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666"
    )


# GHO Token Address (Ethereum Mainnet)
GHO_TOKEN_ADDRESS = get_checksum_address("0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f")

# GHO Variable Debt Token Address (Ethereum Mainnet)
GHO_VARIABLE_DEBT_TOKEN_ADDRESS = get_checksum_address("0x786dBff3f1292ae8F92ea68Cf93c30b34B1ed04B")

# Token event topic hashes
TRANSFER_TOPIC = HexBytes("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass(frozen=True)
class AssetFlow:
    """Represents a single asset movement in an operation."""

    asset_address: ChecksumAddress
    from_address: ChecksumAddress
    to_address: ChecksumAddress
    amount: int
    event_type: str  # "Mint", "Burn", "Transfer", etc.
    event_log_index: int


@dataclass(frozen=True)
class ScaledTokenEvent:
    """Wrapper for scaled token events with decoded data."""

    event: LogReceipt
    event_type: str  # "COLLATERAL_MINT", "COLLATERAL_BURN", "DEBT_MINT", etc.
    user_address: ChecksumAddress
    caller_address: ChecksumAddress | None  # For Mint events
    from_address: ChecksumAddress | None  # For Burn events
    target_address: ChecksumAddress | None  # For Burn events
    amount: int
    balance_increase: int
    index: int

    @property
    def is_interest_accrual(self) -> bool:
        """Check if this is pure interest accrual (value == balanceIncrease)."""
        return self.amount == self.balance_increase

    @property
    def is_collateral(self) -> bool:
        return self.event_type.startswith("COLLATERAL")

    @property
    def is_debt(self) -> bool:
        return self.event_type.startswith("DEBT") or self.event_type.startswith("GHO")

    @property
    def is_mint(self) -> bool:
        return self.event_type.endswith("MINT")

    @property
    def is_burn(self) -> bool:
        return self.event_type.endswith("BURN")


@dataclass(frozen=True)
class Operation:
    """A single logical operation with complete asset flow context."""

    operation_id: int
    operation_type: OperationType

    # Core events
    pool_event: LogReceipt | None
    scaled_token_events: list[ScaledTokenEvent]

    # Supporting events
    transfer_events: list[LogReceipt]
    balance_transfer_events: list[LogReceipt]

    # Computed asset flows
    asset_flows: list[AssetFlow] = field(default_factory=list)

    # Validation state
    validation_errors: list[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Check if operation passed validation."""
        return len(self.validation_errors) == 0

    def get_all_events(self) -> list[LogReceipt]:
        """Get all events involved in this operation."""
        events = []
        if self.pool_event:
            events.append(self.pool_event)
        events.extend([e.event for e in self.scaled_token_events])
        events.extend(self.transfer_events)
        events.extend(self.balance_transfer_events)
        return events

    def get_event_log_indices(self) -> list[int]:
        """Get all log indices involved in this operation."""
        return [e["logIndex"] for e in self.get_all_events()]


class EventMatchResult(TypedDict):
    """Result of a successful event match."""

    pool_event: LogReceipt
    should_consume: bool
    extraction_data: dict[str, int | bool]


# ============================================================================
# EXCEPTIONS
# ============================================================================


class TransactionValidationError(Exception):
    """Raised when transaction validation fails.

    Provides comprehensive plain-text dump of all events and operations
    for debugging.
    """

    def __init__(
        self,
        message: str,
        tx_hash: HexBytes,
        events: list[LogReceipt],
        operations: list[Operation],
    ):
        self.tx_hash = tx_hash
        self.events = events
        self.operations = operations
        self.error_message = message

        # Build comprehensive dump
        dump = self._build_error_dump()
        super().__init__(dump)

    def _build_error_dump(self) -> str:
        """Build human-readable error report."""
        lines = [
            "=" * 80,
            "TRANSACTION VALIDATION FAILED",
            "=" * 80,
            "",
            f"Transaction Hash: {self.tx_hash.to_0x_hex()}",
            f"Block: {self.events[0]['blockNumber'] if self.events else 'N/A'}",
            "",
            "-" * 40,
            "RAW EVENTS (sorted by logIndex)",
            "-" * 40,
            "",
        ]

        for event in sorted(self.events, key=lambda e: e["logIndex"]):
            lines.extend(self._format_event(event))

        lines.extend([
            "",
            "-" * 40,
            f"PARSED OPERATIONS ({len(self.operations)})",
            "-" * 40,
            "",
        ])

        for op in self.operations:
            lines.extend(self._format_operation(op))

        lines.extend([
            "",
            "VALIDATION ERRORS:",
            "-" * 40,
            self.error_message,
            "=" * 80,
        ])

        return "\n".join(lines)

    def _format_event(self, event: LogReceipt) -> list[str]:
        """Format a single event for display."""
        topic = event["topics"][0]
        topic_name = self._get_event_name(topic)

        lines = [
            f"[{event['logIndex']}] {topic_name}",
            f"    Address: {event['address']}",
            f"    Topic: {topic.hex()}",
        ]

        # Add indexed parameters
        if len(event["topics"]) > 1:
            for j, t in enumerate(event["topics"][1:], 1):
                addr = self._try_decode_address(t)
                if addr:
                    lines.append(f"    Topic[{j}] (address): {addr}")
                else:
                    lines.append(f"    Topic[{j}]: {t.hex()}")

        # Add data
        data_str = event["data"].hex()
        if len(data_str) > 60:
            data_str = data_str[:30] + "..." + data_str[-30:]
        lines.append(f"    Data: {data_str}")
        lines.append("")

        return lines

    def _format_operation(self, op: Operation) -> list[str]:
        """Format a single operation for display."""
        lines = [
            f"Operation {op.operation_id}: {op.operation_type.name}",
        ]

        if op.pool_event:
            lines.append(f"  Pool Event: logIndex={op.pool_event['logIndex']}")
        else:
            lines.append("  Pool Event: None")

        lines.append(f"  Scaled Token Events ({len(op.scaled_token_events)}):")
        for ev in op.scaled_token_events:
            lines.append(f"    logIndex {ev.event['logIndex']}: {ev.event_type}")
            lines.append(f"      user: {ev.user_address}")
            lines.append(f"      amount: {ev.amount}")
            lines.append(f"      balance_increase: {ev.balance_increase}")

        if op.validation_errors:
            lines.append("  VALIDATION ERRORS:")
            for err in op.validation_errors:
                lines.append(f"    X {err}")
        else:
            lines.append("  Status: OK Valid")

        lines.append("")
        return lines

    def _get_event_name(self, topic: HexBytes) -> str:
        """Get human-readable event name from topic."""
        for ev in AaveV3Event:
            if ev.value == topic:
                return ev.name
        if topic == TRANSFER_TOPIC:
            return "Transfer"
        return "UNKNOWN"

    def _try_decode_address(self, topic: HexBytes) -> ChecksumAddress | None:
        """Try to decode topic as address."""
        try:
            return get_checksum_address("0x" + topic.hex()[-40:])
        except Exception:
            return None


# ============================================================================
# PARSER
# ============================================================================


class TransactionOperationsParser:
    """Parses transaction events into logical operations."""

    def __init__(
        self,
        gho_token_address: ChecksumAddress | None = None,
        token_type_mapping: dict[ChecksumAddress, str] | None = None,
    ):
        """Initialize parser.

        Args:
            gho_token_address: Address of GHO variable debt token.
                              Defaults to mainnet address if not provided.
            token_type_mapping: Mapping of token addresses to their types.
                               Keys are token addresses, values are "aToken" or "vToken".
        """
        self.gho_token_address = gho_token_address or GHO_VARIABLE_DEBT_TOKEN_ADDRESS
        self.token_type_mapping = token_type_mapping or {}

    def parse(self, events: list[LogReceipt], tx_hash: HexBytes) -> TransactionOperations:
        """Parse events into operations."""
        if not events:
            return TransactionOperations(
                tx_hash=tx_hash,
                block_number=0,
                operations=[],
                unassigned_events=[],
            )

        block_number = events[0]["blockNumber"]

        # Step 1: Identify pool events (anchors for operations)
        pool_events = self._extract_pool_events(events)

        # Step 2: Identify and decode scaled token events
        scaled_events = self._extract_scaled_token_events(events)

        # Step 3: Group into operations
        operations: list[Operation] = []
        assigned_log_indices: set[int] = set()

        for i, pool_event in enumerate(pool_events):
            operation = self._create_operation_from_pool_event(
                operation_id=i,
                pool_event=pool_event,
                scaled_events=scaled_events,
                all_events=events,
                assigned_indices=assigned_log_indices,
            )
            if operation:
                operations.append(operation)
                # Track assigned events
                assigned_log_indices.update(operation.get_event_log_indices())

        # Step 4: Handle unassigned events
        unassigned_events = [
            e
            for e in events
            if e["logIndex"] not in assigned_log_indices
            and e["topics"][0]
            not in {
                TRANSFER_TOPIC,
            }
        ]

        # Step 5: Validate all operations
        for op in operations:
            self._validate_operation(op)

        return TransactionOperations(
            tx_hash=tx_hash,
            block_number=block_number,
            operations=operations,
            unassigned_events=unassigned_events,
        )

    def _extract_pool_events(self, events: list[LogReceipt]) -> list[LogReceipt]:
        """Extract pool-level events (SUPPLY, WITHDRAW, etc.)."""
        pool_topics = {
            AaveV3Event.SUPPLY.value,
            AaveV3Event.WITHDRAW.value,
            AaveV3Event.BORROW.value,
            AaveV3Event.REPAY.value,
            AaveV3Event.LIQUIDATION_CALL.value,
            AaveV3Event.DEFICIT_CREATED.value,
        }
        return sorted(
            [e for e in events if e["topics"][0] in pool_topics],
            key=lambda e: e["logIndex"],
        )

    def _extract_scaled_token_events(self, events: list[LogReceipt]) -> list[ScaledTokenEvent]:
        """Extract and decode scaled token events."""
        result = []

        for event in events:
            topic = event["topics"][0]

            if topic == AaveV3Event.SCALED_TOKEN_MINT.value:
                ev = self._decode_mint_event(event)
                if ev:
                    result.append(ev)

            elif topic == AaveV3Event.SCALED_TOKEN_BURN.value:
                ev = self._decode_burn_event(event)
                if ev:
                    result.append(ev)

            elif topic == AaveV3Event.SCALED_TOKEN_BALANCE_TRANSFER.value:
                ev = self._decode_balance_transfer_event(event)
                if ev:
                    result.append(ev)

        return sorted(result, key=lambda e: e.event["logIndex"])

    def _decode_mint_event(self, event: LogReceipt) -> ScaledTokenEvent | None:
        """Decode a Mint event."""
        try:
            caller = get_checksum_address("0x" + event["topics"][1].hex()[-40:])
            user = get_checksum_address("0x" + event["topics"][2].hex()[-40:])
            amount, balance_increase, index = eth_abi.decode(
                ["uint256", "uint256", "uint256"], event["data"]
            )

            # Determine event type based on token type
            token_address = get_checksum_address(event["address"])
            if token_address == self.gho_token_address:
                event_type = "GHO_DEBT_MINT"
            else:
                # Use token type mapping to determine if this is a collateral or debt mint
                token_type = self.token_type_mapping.get(token_address)
                if token_type == "aToken":
                    event_type = "COLLATERAL_MINT"
                elif token_type == "vToken":
                    event_type = "DEBT_MINT"
                else:
                    # Fallback for unknown tokens - default to collateral
                    event_type = "COLLATERAL_MINT"

            return ScaledTokenEvent(
                event=event,
                event_type=event_type,
                user_address=user,
                caller_address=caller,
                from_address=None,
                target_address=None,
                amount=amount,
                balance_increase=balance_increase,
                index=index,
            )
        except Exception:
            return None

    def _decode_burn_event(self, event: LogReceipt) -> ScaledTokenEvent | None:
        """Decode a Burn event."""
        try:
            from_addr = get_checksum_address("0x" + event["topics"][1].hex()[-40:])
            target = get_checksum_address("0x" + event["topics"][2].hex()[-40:])
            amount, balance_increase, index = eth_abi.decode(
                ["uint256", "uint256", "uint256"], event["data"]
            )

            # Determine event type based on token type
            token_address = get_checksum_address(event["address"])
            if token_address == self.gho_token_address:
                event_type = "GHO_DEBT_BURN"
            else:
                # Use token type mapping to determine if this is a collateral or debt burn
                token_type = self.token_type_mapping.get(token_address)
                if token_type == "aToken":
                    event_type = "COLLATERAL_BURN"
                elif token_type == "vToken":
                    event_type = "DEBT_BURN"
                else:
                    # Fallback for unknown tokens
                    event_type = "UNKNOWN_BURN"

            return ScaledTokenEvent(
                event=event,
                event_type=event_type,
                user_address=from_addr,
                caller_address=None,
                from_address=from_addr,
                target_address=target,
                amount=amount,
                balance_increase=balance_increase,
                index=index,
            )
        except Exception:
            return None

    def _decode_balance_transfer_event(self, event: LogReceipt) -> ScaledTokenEvent | None:
        """Decode a BalanceTransfer event.

        BalanceTransfer events represent internal scaled balance movements in aTokens.
        During liquidations, collateral may be transferred to the treasury instead of burned.
        """
        try:
            from_addr = get_checksum_address("0x" + event["topics"][1].hex()[-40:])
            to_addr = get_checksum_address("0x" + event["topics"][2].hex()[-40:])
            # BalanceTransfer data: amount, index
            amount, index = eth_abi.decode(["uint256", "uint256"], event["data"])

            # Determine event type based on token type
            token_address = get_checksum_address(event["address"])
            if token_address == self.gho_token_address:
                # GHO doesn't have BalanceTransfer events, but handle just in case
                event_type = "GHO_DEBT_TRANSFER"
            else:
                # Use token type mapping to determine if this is collateral or debt
                token_type = self.token_type_mapping.get(token_address)
                if token_type == "aToken":
                    event_type = "COLLATERAL_TRANSFER"
                elif token_type == "vToken":
                    event_type = "DEBT_TRANSFER"
                else:
                    # Fallback for unknown tokens
                    event_type = "UNKNOWN_TRANSFER"

            return ScaledTokenEvent(
                event=event,
                event_type=event_type,
                user_address=from_addr,  # The user whose balance decreased
                caller_address=None,
                from_address=from_addr,
                target_address=to_addr,
                amount=amount,
                balance_increase=0,  # BalanceTransfer doesn't have balanceIncrease
                index=index,
            )
        except Exception:
            return None

    def _create_operation_from_pool_event(
        self,
        operation_id: int,
        pool_event: LogReceipt,
        scaled_events: list[ScaledTokenEvent],
        all_events: list[LogReceipt],
        assigned_indices: set[int],
    ) -> Operation | None:
        """Create operation starting from a pool event."""
        topic = pool_event["topics"][0]

        if topic == AaveV3Event.SUPPLY.value:
            return self._create_supply_operation(
                operation_id, pool_event, scaled_events, all_events, assigned_indices
            )
        if topic == AaveV3Event.WITHDRAW.value:
            return self._create_withdraw_operation(
                operation_id, pool_event, scaled_events, all_events, assigned_indices
            )
        if topic == AaveV3Event.BORROW.value:
            return self._create_borrow_operation(
                operation_id, pool_event, scaled_events, all_events, assigned_indices
            )
        if topic == AaveV3Event.REPAY.value:
            return self._create_repay_operation(
                operation_id, pool_event, scaled_events, all_events, assigned_indices
            )
        if topic == AaveV3Event.LIQUIDATION_CALL.value:
            return self._create_liquidation_operation(
                operation_id, pool_event, scaled_events, all_events, assigned_indices
            )
        if topic == AaveV3Event.DEFICIT_CREATED.value:
            return self._create_deficit_operation(
                operation_id, pool_event, scaled_events, all_events, assigned_indices
            )

        return None

    def _create_supply_operation(
        self,
        operation_id: int,
        supply_event: LogReceipt,
        scaled_events: list[ScaledTokenEvent],
        all_events: list[LogReceipt],
        assigned_indices: set[int],
    ) -> Operation:
        """Create SUPPLY operation."""
        # Decode SUPPLY event
        reserve = self._decode_address(supply_event["topics"][1])
        user = self._decode_address(supply_event["topics"][2])
        caller, amount = eth_abi.decode(["address", "uint256"], supply_event["data"])

        # Find collateral mint for this user
        # For SUPPLY: look for mints where value > balance_increase (standard deposit)
        collateral_mint = None
        for ev in scaled_events:
            if ev.event_type == "COLLATERAL_MINT" and ev.user_address == user:
                if ev.event["logIndex"] not in assigned_indices:
                    # Only match mints that represent deposits (value > balance_increase)
                    # Mints where balance_increase > value are interest accrual for withdrawals
                    if ev.amount > ev.balance_increase:
                        collateral_mint = ev
                        break

        scaled_token_events = [collateral_mint] if collateral_mint else []

        return Operation(
            operation_id=operation_id,
            operation_type=OperationType.SUPPLY,
            pool_event=supply_event,
            scaled_token_events=scaled_token_events,
            transfer_events=[],
            balance_transfer_events=[],
        )

    def _create_withdraw_operation(
        self,
        operation_id: int,
        withdraw_event: LogReceipt,
        scaled_events: list[ScaledTokenEvent],
        all_events: list[LogReceipt],
        assigned_indices: set[int],
    ) -> Operation:
        """Create WITHDRAW operation."""
        # Decode WITHDRAW event
        reserve = self._decode_address(withdraw_event["topics"][1])
        user = self._decode_address(withdraw_event["topics"][2])
        amount = eth_abi.decode(["uint256"], withdraw_event["data"])[0]

        # Find collateral burn for this user
        collateral_burn = None
        for ev in scaled_events:
            if ev.event_type == "COLLATERAL_BURN" and ev.user_address == user:
                if ev.event["logIndex"] not in assigned_indices:
                    collateral_burn = ev
                    break

        scaled_token_events = [collateral_burn] if collateral_burn else []

        return Operation(
            operation_id=operation_id,
            operation_type=OperationType.WITHDRAW,
            pool_event=withdraw_event,
            scaled_token_events=scaled_token_events,
            transfer_events=[],
            balance_transfer_events=[],
        )

    def _create_borrow_operation(
        self,
        operation_id: int,
        borrow_event: LogReceipt,
        scaled_events: list[ScaledTokenEvent],
        all_events: list[LogReceipt],
        assigned_indices: set[int],
    ) -> Operation:
        """Create BORROW operation."""
        # Decode BORROW event
        reserve = self._decode_address(borrow_event["topics"][1])
        on_behalf_of = self._decode_address(borrow_event["topics"][2])
        caller, amount, interest_rate_mode, borrow_rate = eth_abi.decode(
            ["address", "uint256", "uint8", "uint256"], borrow_event["data"]
        )

        # Check if GHO
        is_gho = reserve == GHO_TOKEN_ADDRESS

        # Find debt mint
        debt_mint = None
        for ev in scaled_events:
            if ev.event["logIndex"] in assigned_indices:
                continue

            if (is_gho and ev.event_type == "GHO_DEBT_MINT") or (
                not is_gho and ev.event_type == "DEBT_MINT"
            ):
                if ev.user_address == on_behalf_of:
                    debt_mint = ev
                    break

        scaled_token_events = [debt_mint] if debt_mint else []
        op_type = OperationType.GHO_BORROW if is_gho else OperationType.BORROW

        return Operation(
            operation_id=operation_id,
            operation_type=op_type,
            pool_event=borrow_event,
            scaled_token_events=scaled_token_events,
            transfer_events=[],
            balance_transfer_events=[],
        )

    def _create_repay_operation(
        self,
        operation_id: int,
        repay_event: LogReceipt,
        scaled_events: list[ScaledTokenEvent],
        all_events: list[LogReceipt],
        assigned_indices: set[int],
    ) -> Operation:
        """Create REPAY operation."""
        # Decode REPAY event
        reserve = self._decode_address(repay_event["topics"][1])
        user = self._decode_address(repay_event["topics"][2])
        amount, use_a_tokens = eth_abi.decode(["uint256", "bool"], repay_event["data"])

        is_gho = reserve == GHO_TOKEN_ADDRESS

        # Find debt burn (normal case)
        debt_burn = None
        for ev in scaled_events:
            if ev.event["logIndex"] in assigned_indices:
                continue

            if is_gho:
                if ev.event_type == "GHO_DEBT_BURN":
                    if ev.user_address == user:
                        debt_burn = ev
                        break
            else:
                if ev.event_type == "DEBT_BURN":
                    if ev.user_address == user:
                        debt_burn = ev
                        break

        scaled_token_events = [debt_burn] if debt_burn else []

        # If use_a_tokens, also look for collateral burn
        if use_a_tokens and not is_gho:
            collateral_burn = None
            for ev in scaled_events:
                if ev.event["logIndex"] in assigned_indices:
                    continue
                if ev.event_type == "COLLATERAL_BURN" and ev.user_address == user:
                    collateral_burn = ev
                    break

            if collateral_burn:
                scaled_token_events.append(collateral_burn)
                # Note: We intentionally do NOT include debt_mint here.
                # The debt_mint is for interest accrual and should be a separate
                # operation or handled as unassigned, not grouped with this
                # repayWithATokens operation which should only have 1 debt event.
                op_type = OperationType.REPAY_WITH_ATOKENS
            else:
                op_type = OperationType.REPAY
        else:
            op_type = OperationType.GHO_REPAY if is_gho else OperationType.REPAY

        return Operation(
            operation_id=operation_id,
            operation_type=op_type,
            pool_event=repay_event,
            scaled_token_events=scaled_token_events,
            transfer_events=[],
            balance_transfer_events=[],
        )

    def _create_liquidation_operation(
        self,
        operation_id: int,
        liquidation_event: LogReceipt,
        scaled_events: list[ScaledTokenEvent],
        all_events: list[LogReceipt],
        assigned_indices: set[int],
    ) -> Operation:
        """Create LIQUIDATION operation."""
        # Decode LIQUIDATION_CALL
        collateral_asset = self._decode_address(liquidation_event["topics"][1])
        debt_asset = self._decode_address(liquidation_event["topics"][2])
        user = self._decode_address(liquidation_event["topics"][3])

        is_gho = debt_asset == GHO_TOKEN_ADDRESS

        # Find debt burn
        debt_burn = None
        for ev in scaled_events:
            if ev.event["logIndex"] in assigned_indices:
                continue

            if (is_gho and ev.event_type == "GHO_DEBT_BURN") or (
                not is_gho and ev.event_type == "DEBT_BURN"
            ):
                if ev.user_address == user:
                    debt_burn = ev
                    break

        # Find collateral burn or transfer
        # During liquidations, collateral may be burned OR transferred to treasury
        collateral_burn = None
        collateral_transfer = None
        for ev in scaled_events:
            if ev.event["logIndex"] in assigned_indices:
                continue

            if ev.event_type == "COLLATERAL_BURN":
                if ev.user_address == user:
                    collateral_burn = ev
                    break
            elif ev.event_type == "COLLATERAL_TRANSFER":
                if ev.user_address == user:
                    collateral_transfer = ev
                    break

        scaled_token_events = []
        if debt_burn:
            scaled_token_events.append(debt_burn)
        if collateral_burn:
            scaled_token_events.append(collateral_burn)
        elif collateral_transfer:
            # Collateral transferred to treasury during liquidation
            scaled_token_events.append(collateral_transfer)

        op_type = OperationType.GHO_LIQUIDATION if is_gho else OperationType.LIQUIDATION

        return Operation(
            operation_id=operation_id,
            operation_type=op_type,
            pool_event=liquidation_event,
            scaled_token_events=scaled_token_events,
            transfer_events=[],
            balance_transfer_events=[],
        )

    def _create_deficit_operation(
        self,
        operation_id: int,
        deficit_event: LogReceipt,
        scaled_events: list[ScaledTokenEvent],
        all_events: list[LogReceipt],
        assigned_indices: set[int],
    ) -> Operation:
        """Create DEFICIT_CREATED operation.

        DEFICIT_CREATED indicates bad debt write-off. When the asset is GHO,
        it's a GHO flash loan that requires a debt burn. For other assets,
        it's a standalone deficit event with no associated debt burn.
        """
        user = self._decode_address(deficit_event["topics"][1])
        asset = self._decode_address(deficit_event["topics"][2])

        # Check if this is a GHO deficit (flash loan) or non-GHO deficit
        is_gho_deficit = asset == GHO_TOKEN_ADDRESS

        scaled_token_events = []
        if is_gho_deficit:
            # Find GHO debt burn for GHO flash loans
            for ev in scaled_events:
                if ev.event["logIndex"] in assigned_indices:
                    continue

                if ev.event_type == "GHO_DEBT_BURN" and ev.user_address == user:
                    scaled_token_events.append(ev)
                    break

        return Operation(
            operation_id=operation_id,
            operation_type=OperationType.GHO_FLASH_LOAN
            if is_gho_deficit
            else OperationType.UNKNOWN,
            pool_event=deficit_event,
            scaled_token_events=scaled_token_events,
            transfer_events=[],
            balance_transfer_events=[],
        )

    def _validate_operation(self, op: Operation) -> None:
        """Strict validation of operation completeness."""
        errors = []

        validators = {
            OperationType.SUPPLY: self._validate_supply,
            OperationType.WITHDRAW: self._validate_withdraw,
            OperationType.BORROW: self._validate_borrow,
            OperationType.GHO_BORROW: self._validate_gho_borrow,
            OperationType.REPAY: self._validate_repay,
            OperationType.REPAY_WITH_ATOKENS: self._validate_repay_with_atokens,
            OperationType.GHO_REPAY: self._validate_gho_repay,
            OperationType.LIQUIDATION: self._validate_liquidation,
            OperationType.GHO_LIQUIDATION: self._validate_gho_liquidation,
            OperationType.GHO_FLASH_LOAN: self._validate_flash_loan,
        }

        validator = validators.get(op.operation_type)
        if validator:
            errors.extend(validator(op))

        # Set validation errors
        object.__setattr__(op, "validation_errors", errors)

    def _validate_supply(self, op: Operation) -> list[str]:
        """Validate SUPPLY operation."""
        errors = []

        if not op.pool_event:
            errors.append("Missing SUPPLY pool event")
            return errors

        # Should have exactly 1 collateral mint
        collateral_mints = [e for e in op.scaled_token_events if e.is_collateral]
        if len(collateral_mints) != 1:
            errors.append(f"Expected 1 collateral mint for SUPPLY, got {len(collateral_mints)}")

        return errors

    def _validate_withdraw(self, op: Operation) -> list[str]:
        """Validate WITHDRAW operation."""
        errors = []

        if not op.pool_event:
            errors.append("Missing WITHDRAW pool event")
            return errors

        # Should have exactly 1 collateral burn
        # Edge case: In complex vault/strategy transactions, a WITHDRAW may not have
        # a corresponding Burn event if the collateral is handled through an adapter
        # or intermediate contract.
        # See TX 0xe6811c1ee3be2981338d910c6e421d092b4f6e3c0b763a6319b2b7cd731e2fb9
        collateral_burns = [e for e in op.scaled_token_events if e.is_collateral]
        if len(collateral_burns) > 1:
            errors.append(
                f"Expected at most 1 collateral burn for WITHDRAW, got {len(collateral_burns)}"
            )
        # Note: len(collateral_burns) == 0 is allowed for edge cases like vault rebalances
        # where collateral may be handled through flash loans or adapter contracts

        return errors

    def _validate_borrow(self, op: Operation) -> list[str]:
        """Validate BORROW operation."""
        errors = []

        if not op.pool_event:
            errors.append("Missing BORROW pool event")
            return errors

        # Should have exactly 1 debt mint
        debt_mints = [e for e in op.scaled_token_events if e.is_debt]
        if len(debt_mints) != 1:
            errors.append(f"Expected 1 debt mint for BORROW, got {len(debt_mints)}")

        return errors

    def _validate_gho_borrow(self, op: Operation) -> list[str]:
        """Validate GHO BORROW operation."""
        errors = self._validate_borrow(op)

        # Additional GHO-specific validation
        gho_mints = [e for e in op.scaled_token_events if e.event_type == "GHO_DEBT_MINT"]
        if len(gho_mints) != 1:
            errors.append(f"Expected 1 GHO debt mint for GHO_BORROW, got {len(gho_mints)}")

        return errors

    def _validate_repay(self, op: Operation) -> list[str]:
        """Validate REPAY operation."""
        errors = []

        if not op.pool_event:
            errors.append("Missing REPAY pool event")
            return errors

        # Can have 0 or 1 debt burns (0 = interest-only repayment, 1 = principal repayment)
        debt_burns = [e for e in op.scaled_token_events if e.is_debt]
        if len(debt_burns) > 1:
            errors.append(f"Expected 0 or 1 debt burns for REPAY, got {len(debt_burns)}")

        return errors

    def _validate_repay_with_atokens(self, op: Operation) -> list[str]:
        """Validate REPAY_WITH_ATOKENS operation."""
        errors = []

        if not op.pool_event:
            errors.append("Missing REPAY pool event")
            return errors

        # Should have 0 or 1 debt events (burn or mint) and 1 collateral burn
        # Note: When interest exceeds repayment, debt mints instead of burns
        # Note: In some edge cases, debt burn may not be emitted if debt is fully covered by interest
        debt_events = [e for e in op.scaled_token_events if e.is_debt]
        collateral_burns = [e for e in op.scaled_token_events if e.is_collateral and e.is_burn]

        if len(debt_events) > 1:
            errors.append(
                f"Expected 0 or 1 debt events for REPAY_WITH_ATOKENS, got {len(debt_events)}"
            )
        if len(collateral_burns) != 1:
            errors.append(
                f"Expected 1 collateral burn for REPAY_WITH_ATOKENS, got {len(collateral_burns)}"
            )

        return errors

    def _validate_gho_repay(self, op: Operation) -> list[str]:
        """Validate GHO REPAY operation."""
        errors = self._validate_repay(op)

        # GHO repay can emit either BURN (debt reduction) or MINT (interest > repayment)
        # When interest accrued exceeds repayment amount, the debt token mints instead of burns
        gho_events = [
            e for e in op.scaled_token_events if e.event_type in {"GHO_DEBT_BURN", "GHO_DEBT_MINT"}
        ]
        if len(gho_events) > 1:
            errors.append(f"Expected 0 or 1 GHO debt event for GHO_REPAY, got {len(gho_events)}")

        return errors

    def _validate_liquidation(self, op: Operation) -> list[str]:
        """Validate LIQUIDATION operation."""
        errors = []

        if not op.pool_event:
            errors.append("Missing LIQUIDATION_CALL pool event")
            return errors

        # Should have 1 collateral event (burn or transfer) and 0 or 1 debt burns
        # Flash loan liquidations have 0 debt burns (debt repaid via flash loan)
        # Standard liquidations have 1 debt burn
        # Collateral may be burned OR transferred to treasury (BalanceTransfer)
        debt_burns = [e for e in op.scaled_token_events if e.is_debt]
        collateral_events = [e for e in op.scaled_token_events if e.is_collateral]

        if len(debt_burns) > 1:
            errors.append(
                f"Expected 0 or 1 debt burns for LIQUIDATION, got {len(debt_burns)}. "
                f"DEBUG NOTE: Check if debt/collateral events are being assigned to wrong operations. "
                f"Current debt burns: {[e.event['logIndex'] for e in debt_burns]}. "
                f"User in LIQUIDATION_CALL: {self._decode_address(op.pool_event['topics'][3])}"
            )

        if len(collateral_events) != 1:
            errors.append(
                f"Expected 1 collateral event (burn or transfer) for LIQUIDATION, got {len(collateral_events)}. "
                f"DEBUG NOTE: Check collateral asset matching and user address consistency. "
                f"Current collateral events: {[e.event['logIndex'] for e in collateral_events]}. "
                f"User in LIQUIDATION_CALL: {self._decode_address(op.pool_event['topics'][3])}"
            )

        return errors

    def _validate_gho_liquidation(self, op: Operation) -> list[str]:
        """Validate GHO LIQUIDATION operation."""
        errors = self._validate_liquidation(op)

        # Additional GHO-specific validation
        gho_burns = [e for e in op.scaled_token_events if e.event_type == "GHO_DEBT_BURN"]
        if len(gho_burns) != 1:
            errors.append(
                f"Expected 1 GHO debt burn for GHO_LIQUIDATION, got {len(gho_burns)}. "
                f"DEBUG NOTE: Verify GHO token address matching."
            )

        return errors

    def _validate_flash_loan(self, op: Operation) -> list[str]:
        """Validate FLASH_LOAN (DEFICIT_CREATED) operation."""
        errors = []

        if not op.pool_event:
            errors.append("Missing DEFICIT_CREATED pool event")
            return errors

        # Should have exactly 1 GHO debt burn
        gho_burns = [e for e in op.scaled_token_events if e.event_type == "GHO_DEBT_BURN"]
        if len(gho_burns) != 1:
            errors.append(
                f"Expected 1 GHO debt burn for FLASH_LOAN, got {len(gho_burns)}. "
                f"DEBUG NOTE: Flash loans should have exactly one debt burn."
            )

        return errors

    def _decode_address(self, topic: HexBytes) -> ChecksumAddress:
        """Decode topic as address."""
        return get_checksum_address("0x" + topic.hex()[-40:])


# ============================================================================
# TRANSACTION OPERATIONS CONTAINER
# ============================================================================


class TransactionOperations:
    """Container for all operations in a transaction."""

    def __init__(
        self,
        tx_hash: HexBytes,
        block_number: int,
        operations: list[Operation],
        unassigned_events: list[LogReceipt],
    ):
        self.tx_hash = tx_hash
        self.block_number = block_number
        self.operations = operations
        self.unassigned_events = unassigned_events

    def validate(self, all_events: list[LogReceipt]) -> None:
        """Strict validation - fails on any unmet expectation."""
        all_errors = []

        # Check all operations are valid
        for op in self.operations:
            if not op.is_valid():
                all_errors.extend([
                    f"Operation {op.operation_id} ({op.operation_type.name}): {err}"
                    for err in op.validation_errors
                ])

        # Check for unassigned required events
        required_unassigned = [e for e in self.unassigned_events if self._is_required_pool_event(e)]
        if required_unassigned:
            all_errors.append(
                f"{len(required_unassigned)} required pool events unassigned: "
                f"{[e['logIndex'] for e in required_unassigned]}. "
                f"DEBUG NOTE: Investigate why these events were not assigned to any operation. "
                f"They may need special handling or indicate a parsing bug."
            )

        # Check for ambiguous event assignments
        assigned_indices: dict[int, int] = {}  # logIndex -> operation_id
        for op in self.operations:
            for log_idx in op.get_event_log_indices():
                if log_idx in assigned_indices:
                    all_errors.append(
                        f"Event at logIndex {log_idx} assigned to multiple operations: "
                        f"{assigned_indices[log_idx]} and {op.operation_id}. "
                        f"DEBUG NOTE: This event may need to be reusable. "
                        f"Investigate whether it can match multiple operations "
                        f"(e.g., LIQUIDATION_CALL or REPAY with useATokens)."
                    )
                assigned_indices[log_idx] = op.operation_id

        if all_errors:
            raise TransactionValidationError(
                message="Transaction validation failed:\n" + "\n".join(all_errors),
                tx_hash=self.tx_hash,
                events=all_events,
                operations=self.operations,
            )

    def _is_required_pool_event(self, event: LogReceipt) -> bool:
        """Check if an event must be part of an operation."""
        pool_topics = {
            AaveV3Event.SUPPLY.value,
            AaveV3Event.WITHDRAW.value,
            AaveV3Event.BORROW.value,
            AaveV3Event.REPAY.value,
            AaveV3Event.LIQUIDATION_CALL.value,
            AaveV3Event.DEFICIT_CREATED.value,
        }
        return event["topics"][0] in pool_topics

    def get_operation_for_event(self, event: LogReceipt) -> Operation | None:
        """Find which operation contains a given event."""
        target_log_index = event["logIndex"]
        for op in self.operations:
            if target_log_index in op.get_event_log_indices():
                return op
        return None
