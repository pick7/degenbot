"""Structured JSON logging for Aave updater debugging.

Provides machine-parseable debug output for autonomous agent analysis.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from hexbytes import HexBytes

if TYPE_CHECKING:
    from eth_typing import ChainId
    from web3.types import LogReceipt

    from degenbot.cli.aave import TransactionContext


class AaveDebugLogger:
    """Structured debug logger for Aave event processing.

    Outputs JSON Lines format for machine-parseable debugging.
    Each log entry includes timestamp, level, context, and structured data.
    """

    _instance: ClassVar[AaveDebugLogger | None] = None
    _initialized: bool = False

    def __new__(cls) -> AaveDebugLogger:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._output_path: Path | None = None
        self._file_handle: Any = None
        self._chain_id: ChainId | None = None
        self._market_id: int | None = None
        self._buffer: list[dict[str, Any]] = []
        self._buffer_size: int = 100
        self._enabled: bool = False

    def configure(
        self,
        output_path: Path | str | None = None,
        chain_id: ChainId | None = None,
        market_id: int | None = None,
    ) -> bool:
        """Configure the debug logger.

        Args:
            output_path: Path to write JSONL debug output. If None, uses env var
                or existing path if already configured.
            chain_id: Chain ID for context
            market_id: Market ID for context

        Returns:
            True if logging is enabled, False otherwise
        """
        if output_path is None:
            output_path = os.environ.get("DEGENBOT_DEBUG_OUTPUT")

        # If already configured with a path, just update context
        if self._output_path is not None and output_path is None:
            if chain_id is not None:
                self._chain_id = chain_id
            if market_id is not None:
                self._market_id = market_id
            return self._enabled

        if not output_path:
            self._enabled = False
            return False

        # Close existing file if reconfiguring with new path
        if self._file_handle is not None:
            self.close()

        self._output_path = Path(output_path)
        self._chain_id = chain_id
        self._market_id = market_id
        self._enabled = True

        # Ensure parent directory exists
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        # Open file for writing (append mode)
        self._file_handle = self._output_path.open("a", buffering=1, encoding="utf-8")

        # Write header entry
        self._write_entry({
            "type": "session_start",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "chain_id": chain_id.value if chain_id else None,
            "market_id": market_id,
        })

        return True

    def is_enabled(self) -> bool:
        """Check if debug logging is enabled."""
        return self._enabled

    def _write_entry(self, entry: dict[str, Any]) -> None:
        """Write a single log entry to the file."""
        if not self._enabled or self._file_handle is None:
            return

        entry["_chain_id"] = self._chain_id.value if self._chain_id else None
        entry["_market_id"] = self._market_id

        try:
            self._file_handle.write(json.dumps(entry, default=str) + "\n")
        except OSError as e:
            # Log to stderr if file write fails
            sys.stderr.write(f"Failed to write debug log: {e}\n")

    def log_event(
        self,
        *,
        level: str,
        message: str,
        tx_hash: HexBytes | str | None = None,
        block_number: int | None = None,
        user_address: str | None = None,
        event_type: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log a structured event.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Human-readable message
            tx_hash: Transaction hash for correlation
            block_number: Block number for correlation
            user_address: User address for correlation
            event_type: Type of event being processed
            context: Additional structured context data
        """
        if not self._enabled:
            return

        entry = {
            "type": "log",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": level.upper(),
            "message": message,
            "tx_hash": tx_hash.hex() if isinstance(tx_hash, HexBytes) else tx_hash,
            "block_number": block_number,
            "user_address": user_address,
            "event_type": event_type,
            "context": context or {},
        }

        self._write_entry(entry)

    def log_transaction_start(
        self,
        *,
        tx_hash: HexBytes | str,
        block_number: int,
        event_count: int,
        context: TransactionContext | None = None,
    ) -> None:
        """Log the start of transaction processing.

        Args:
            tx_hash: Transaction hash
            block_number: Block number
            event_count: Number of events in transaction
            context: Transaction context for detailed logging
        """
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "transaction_start",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "tx_hash": tx_hash.hex() if isinstance(tx_hash, HexBytes) else tx_hash,
            "block_number": block_number,
            "event_count": event_count,
        }

        if context is not None:
            entry["tx_context"] = self._serialize_tx_context(context)

        self._write_entry(entry)

    def log_transaction_end(
        self,
        *,
        tx_hash: HexBytes | str,
        block_number: int,
        success: bool,
        duration_ms: float | None = None,
    ) -> None:
        """Log the end of transaction processing.

        Args:
            tx_hash: Transaction hash
            block_number: Block number
            success: Whether processing succeeded
            duration_ms: Processing duration in milliseconds
        """
        if not self._enabled:
            return

        entry = {
            "type": "transaction_end",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "tx_hash": tx_hash.hex() if isinstance(tx_hash, HexBytes) else tx_hash,
            "block_number": block_number,
            "success": success,
            "duration_ms": duration_ms,
        }

        self._write_entry(entry)

    def log_exception(
        self,
        *,
        exc: Exception,
        tx_context: TransactionContext | None = None,
        event: LogReceipt | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> None:
        """Log an exception with full context for replay.

        Args:
            exc: The exception that was raised
            tx_context: Transaction context at time of exception
            event: The event being processed when exception occurred
            extra_context: Additional context data
        """
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "exception",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
        }

        if tx_context is not None:
            entry["tx_context"] = self._serialize_tx_context(tx_context)

        if event is not None:
            entry["event"] = self._serialize_event(event)

        if extra_context is not None:
            entry["extra_context"] = extra_context

        self._write_entry(entry)

    def _serialize_tx_context(self, context: TransactionContext) -> dict[str, Any]:
        """Serialize TransactionContext to a JSON-serializable dict."""
        event_topics: list[str] = []
        for event in context.events:
            topics = event.get("topics", [])
            if topics:
                first_topic = topics[0]
                if isinstance(first_topic, HexBytes):
                    event_topics.append(first_topic.hex())
                else:
                    event_topics.append(str(first_topic))

        return {
            "tx_hash": context.tx_hash.hex()
            if isinstance(context.tx_hash, HexBytes)
            else str(context.tx_hash),
            "block_number": context.block_number,
            "event_count": len(context.events),
            "event_topics": event_topics,
            "user_discounts_count": len(context.user_discounts),
            "discount_updates_count": len(context.discount_updates_by_log_index),
        }

    def _serialize_event(self, event: LogReceipt) -> dict[str, Any]:
        """Serialize a LogReceipt event to JSON-serializable dict."""
        if event is None:
            return {}

        return {
            "address": event.get("address"),
            "blockNumber": event.get("blockNumber"),
            "blockHash": event.get("blockHash").hex()
            if isinstance(event.get("blockHash"), HexBytes)
            else event.get("blockHash"),
            "transactionHash": event.get("transactionHash").hex()
            if isinstance(event.get("transactionHash"), HexBytes)
            else event.get("transactionHash"),
            "logIndex": event.get("logIndex"),
            "topics": [
                t.hex() if isinstance(t, HexBytes) else str(t) for t in event.get("topics", [])
            ],
            "data": event.get("data").hex()
            if isinstance(event.get("data"), (HexBytes, bytes))
            else event.get("data"),
        }

    def log_block_boundary(
        self,
        *,
        block_number: int,
        event_count: int,
        user_count: int,
    ) -> None:
        """Log block boundary processing.

        Args:
            block_number: Block number
            event_count: Number of events in block
            user_count: Number of users affected in block
        """
        if not self._enabled:
            return

        entry = {
            "type": "block_boundary",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "block_number": block_number,
            "event_count": event_count,
            "user_count": user_count,
        }

        self._write_entry(entry)

    def close(self) -> None:
        """Close the debug log file and write session end marker."""
        if not self._enabled or self._file_handle is None:
            return

        self._write_entry({
            "type": "session_end",
            "timestamp": datetime.now(tz=UTC).isoformat(),
        })

        self._file_handle.close()
        self._file_handle = None
        self._enabled = False


# Global instance
aave_debug_logger = AaveDebugLogger()
