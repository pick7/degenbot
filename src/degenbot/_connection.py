import tenacity
import web3

from degenbot.exceptions import DegenbotValueError
from degenbot.types import ChainId


class AsyncConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[ChainId, web3.AsyncWeb3] = {}
        self._default_chain_id: ChainId | None = None

    def get_web3(self, chain_id: ChainId) -> web3.AsyncWeb3:
        try:
            return self.connections[chain_id]
        except KeyError:
            raise DegenbotValueError(
                message="Chain ID does not have a registered Web3 instance."
            ) from None

    async def register_web3(self, w3: web3.AsyncWeb3, optimize_middleware: bool = True) -> None:
        async_w3_connected_check_with_retry = tenacity.AsyncRetrying(
            stop=tenacity.stop_after_delay(10),
            wait=tenacity.wait_exponential_jitter(),
            retry=tenacity.retry_if_result(lambda result: result is False),
        )
        try:
            await async_w3_connected_check_with_retry(w3.is_connected)
        except tenacity.RetryError as exc:
            raise DegenbotValueError(message="Web3 instance is not connected.") from exc

        if optimize_middleware:
            w3.middleware_onion.clear()
        self.connections[await w3.eth.chain_id] = w3

    def set_default_chain(self, chain_id: ChainId) -> None:
        self._default_chain_id = chain_id

    @property
    def default_chain_id(self) -> ChainId:
        if self._default_chain_id is None:
            raise DegenbotValueError(message="A default chain ID has not been provided.")
        return self._default_chain_id


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[ChainId, web3.Web3] = {}
        self._default_chain_id: ChainId | None = None

    def get_web3(self, chain_id: ChainId) -> web3.Web3:
        try:
            return self.connections[chain_id]
        except KeyError:
            raise DegenbotValueError(
                message="Chain ID does not have a registered Web3 instance."
            ) from None

    def register_web3(self, w3: web3.Web3, optimize_middleware: bool = True) -> None:
        w3_connected_check_with_retry = tenacity.Retrying(
            stop=tenacity.stop_after_delay(10),
            wait=tenacity.wait_exponential_jitter(),
            retry=tenacity.retry_if_result(lambda result: result is False),
        )
        try:
            w3_connected_check_with_retry(fn=w3.is_connected)
        except tenacity.RetryError as exc:
            raise DegenbotValueError(message="Web3 instance is not connected.") from exc

        if optimize_middleware:
            w3.middleware_onion.clear()
        self.connections[w3.eth.chain_id] = w3

    def set_default_chain(self, chain_id: ChainId) -> None:
        self._default_chain_id = chain_id

    @property
    def default_chain_id(self) -> ChainId:
        if self._default_chain_id is None:
            raise DegenbotValueError(message="A default Web3 instance has not been registered.")
        return self._default_chain_id


def get_web3() -> web3.Web3:
    return connection_manager.get_web3(chain_id=connection_manager.default_chain_id)


def set_web3(w3: web3.Web3, optimize_middleware: bool = True) -> None:
    w3_connected_check_with_retry = tenacity.Retrying(
        stop=tenacity.stop_after_delay(10),
        wait=tenacity.wait_exponential_jitter(),
        retry=tenacity.retry_if_result(lambda result: result is False),
    )
    try:
        w3_connected_check_with_retry(fn=w3.is_connected)
    except tenacity.RetryError as exc:
        raise DegenbotValueError(message="Web3 instance is not connected.") from exc

    connection_manager.register_web3(w3, optimize_middleware=optimize_middleware)
    connection_manager.set_default_chain(w3.eth.chain_id)


def get_async_web3() -> web3.AsyncWeb3:
    if async_connection_manager.default_chain_id is None:
        raise DegenbotValueError(
            message="A default Web3 instance has not been registered."
        ) from None
    return async_connection_manager.get_web3(chain_id=async_connection_manager.default_chain_id)


async def set_async_web3(w3: web3.AsyncWeb3, optimize_middleware: bool = True) -> None:
    async_w3_connected_check_with_retry = tenacity.AsyncRetrying(
        stop=tenacity.stop_after_delay(10),
        wait=tenacity.wait_exponential_jitter(),
        retry=tenacity.retry_if_result(lambda result: result is False),
    )
    try:
        await async_w3_connected_check_with_retry(w3.is_connected)
    except tenacity.RetryError as exc:
        raise DegenbotValueError(message="Web3 instance is not connected.") from exc

    await async_connection_manager.register_web3(w3, optimize_middleware=optimize_middleware)
    async_connection_manager.set_default_chain(await w3.eth.chain_id)


connection_manager = ConnectionManager()
async_connection_manager = AsyncConnectionManager()
