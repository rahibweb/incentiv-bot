import asyncio
import random
import secrets
import time
import json
import re
import ssl
import certifi
from typing import Optional, Dict, Any, List
from web3 import Web3
from eth_abi.abi import encode
from eth_utils import to_hex
from eth_account import Account
from eth_account.messages import encode_defunct
from aiohttp import ClientResponseError, ClientSession, ClientTimeout, BasicAuth, TCPConnector
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from datetime import datetime

from database import Database
from src.logger import logger
from src.captcha import CaptchaSolver
from src.utils import get_random_delay, check_proxy_scheme

class IncentivBot:
    def __init__(self, db: Database, settings: Dict[str, Any]):
        self.db = db
        self.settings = settings
        self.BASE_API = "https://api.testnet.incentiv.io"
        self.RPC_URL = "https://rpc1.testnet.incentiv.io/"
        self.BUNDLER_URL = "https://bundler-testnet.incentiv.io/"
        self.EXPLORER = "https://explorer-testnet.incentiv.io/op/"
        self.PAGE_URL = "https://testnet.incentiv.io"
        self.SITE_KEY = "0x4AAAAAABl4Ht6hzgSZ-Na3"
        self.TCENT_CONTRACT_ADDRESS = "0x0000000000000000000000000000000000000000"
        self.WCENT_CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
        self.SMPL_CONTRACT_ADDRESS = "0x0165878A594ca255338adfa4d48449f69242Eb8F"
        self.BULL_CONTRACT_ADDRESS = "0x8A791620dd6260079BF849Dc5567aDC3F2FdC318"
        self.FLIP_CONTRACT_ADDRESS = "0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0"
        self.SWAP_ROUTER_ADDRESS = "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0"
        self.ENTRYPOINT_ADDRESS = "0x9b5d240EF1bc8B4930346599cDDFfBD7d7D56db9"
        self.RECOVERY_MAP_ADDRESS = "0x01e509511762ea0aa52763657D0b295517Bceb12"
        self.PAYMASTER_ADDRESS = "0xc11c6C51AAB2d88C38F39069E1B1d9e2BbA3e54b"
        self.CONTRACT_ABI = [{"inputs": [{"internalType": "address", "name": "", "type": "address"}], "name": "recoveryToAccount", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "getNonce", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "address", "name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"components": [{"internalType": "address", "name": "sender", "type": "address"}, {"internalType": "uint256", "name": "nonce", "type": "uint256"}, {"internalType": "bytes", "name": "initCode", "type": "bytes"}, {"internalType": "bytes", "name": "callData", "type": "bytes"}, {"internalType": "bytes32", "name": "accountGasLimits", "type": "bytes32"}, {"internalType": "uint256", "name": "preVerificationGas", "type": "uint256"}, {"internalType": "bytes32", "name": "gasFees", "type": "bytes32"}, {"internalType": "bytes", "name": "paymasterAndData", "type": "bytes"}, {"internalType": "bytes", "name": "signature", "type": "bytes"}], "internalType": "struct PackedUserOperation", "name": "userOp", "type": "tuple"}], "name": "getUserOpHash", "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "stateMutability": "view", "type": "function"}]

        captcha_config = settings.get('CAPTCHA', {})

        try:
            self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            self.ssl_context = ssl.create_default_context()
        provider = captcha_config.get('PROVIDER', '2captcha').lower()
        if provider == 'solvium':
            api_key = captcha_config.get('SOLVIUM_KEY', '')
        else:
            api_key = captcha_config.get('CAPTCHA_2CAPTCHA_KEY', '')
        self.captcha_solver = CaptchaSolver(provider=provider, api_key=api_key)

        self.BASE_HEADERS = {}
        self.BUNDLER_HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.account_types = {}
        self.private_keys = {}
        self.access_tokens = {}
        self.smart_accounts = {}
        self.used_nonce = {}
        self.faucet_times = {}
        self.account_prefixes = {}

        def parse_amount_range(value, default=0.001):
            if isinstance(value, list) and len(value) == 2:
                return value
            elif isinstance(value, (int, float)):
                return [value, value]
            return [default, default]

        transfer_settings = settings.get('TRANSFER', {})
        self.tcent_transfer_amount_range = parse_amount_range(transfer_settings.get('TCENT_TRANSFER_AMOUNT', 0.001))
        self.smpl_transfer_amount_range = parse_amount_range(transfer_settings.get('SMPL_TRANSFER_AMOUNT', 0.001))
        self.bull_transfer_amount_range = parse_amount_range(transfer_settings.get('BULL_TRANSFER_AMOUNT', 0.001))
        self.flip_transfer_amount_range = parse_amount_range(transfer_settings.get('FLIP_TRANSFER_AMOUNT', 0.001))

        swap_settings = settings.get('SWAP', {})
        self.tcent_swap_amount_range = parse_amount_range(swap_settings.get('TCENT_SWAP_AMOUNT', 0.001))
        self.smpl_swap_amount_range = parse_amount_range(swap_settings.get('SMPL_SWAP_AMOUNT', 0.001))
        self.bull_swap_amount_range = parse_amount_range(swap_settings.get('BULL_SWAP_AMOUNT', 0.001))
        self.flip_swap_amount_range = parse_amount_range(swap_settings.get('FLIP_SWAP_AMOUNT', 0.001))

        bundle_settings = settings.get('BUNDLE', {})
        self.bundle_action_amount_range = parse_amount_range(bundle_settings.get('BUNDLE_ACTION_AMOUNT', 0.001))

        actions_count = settings.get('ACTIONS_COUNT', {})
        def get_count_value(value, default):
            if isinstance(value, list) and len(value) == 2:
                return value
            elif isinstance(value, int):
                return [value, value]
            return [default, default]

        self.add_contact_count_range = get_count_value(actions_count.get('ADD_CONTACTS'), 3)
        self.transfer_count_range = get_count_value(actions_count.get('TRANSFERS'), 3)
        self.swap_count_range = get_count_value(actions_count.get('SWAPS'), 3)
        self.bundle_count_range = get_count_value(actions_count.get('BUNDLE_ACTIONS'), 1)

        unified_token_settings = settings.get('UNIFIED_TOKEN_GAS', {})
        self.unified_token_enabled = unified_token_settings.get('ENABLED', False)
        self.unified_token_min_balance = unified_token_settings.get('MIN_TOKEN_BALANCE', 0.01)
        self.unified_token_gas_tokens = unified_token_settings.get('GAS_TOKENS', ['SMPL', 'BULL', 'FLIP'])
        self.unified_token_randomize = unified_token_settings.get('RANDOMIZE_TOKEN', True)

        bot_settings = settings.get('SETTINGS', {})
        self.pause_between_actions = bot_settings.get('RANDOM_PAUSE_BETWEEN_ACTIONS', [1, 3])
        self.pause_between_swaps = bot_settings.get('PAUSE_BETWEEN_SWAPS', [3, 10])
        self.pause_between_attempts = bot_settings.get('PAUSE_BETWEEN_ATTEMPTS', [1, 3])
        self.pause_between_accounts = bot_settings.get('RANDOM_PAUSE_BETWEEN_ACCOUNTS', [1, 5])
        self.init_pause = bot_settings.get('RANDOM_INITIALIZATION_PAUSE', [1, 3])
        self.attempts = bot_settings.get('ATTEMPTS', 5)
        self.threads = bot_settings.get('THREADS', 1)
        self.nonce_check_timeout = bot_settings.get('NONCE_CHECK_TIMEOUT', 12)
        self.nonce_check_attempts_before = bot_settings.get('NONCE_CHECK_ATTEMPTS_BEFORE_DEPLOY', 1)
        self.nonce_check_initial_wait = bot_settings.get('NONCE_CHECK_INITIAL_WAIT_AFTER_DEPLOY', 10)
        self.nonce_check_attempts_after = bot_settings.get('NONCE_CHECK_ATTEMPTS_AFTER_DEPLOY', 4)
        self.nonce_check_delay = bot_settings.get('NONCE_CHECK_PROGRESSIVE_DELAY', 2)

    def _log_prefix(self, address: str) -> str:
        if address not in self.account_prefixes:
            self.account_prefixes[address] = f"{address[:6]}...{address[-4:]}"
        return f"[{self.account_prefixes[address]}]"

    def _get_random_amount(self, amount_range: list) -> float:
        min_amount, max_amount = amount_range
        amount = random.uniform(min_amount, max_amount)
        return round(amount, 6)

    async def ensure_valid_token(self, private_key: str, address: str, use_proxy: bool, rotate_proxy: bool) -> bool:
        if address in self.access_tokens and self.access_tokens[address]:
            if self.db.is_token_valid(private_key):
                logger.debug("Using cached valid token")
                return True
        logger.info("Getting new access token...")
        return await self.refresh_token(private_key, address, use_proxy, rotate_proxy)

    async def refresh_token(self, private_key: str, address: str, use_proxy: bool, rotate_proxy: bool) -> bool:
        prefix = self._log_prefix(address)

        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                if self.account_types.get(private_key) == "private_key":
                    challenge_type = "BROWSER_EXTENSION"
                else:
                    challenge_type = "RECOVERY_EOA"

                logger.debug(f"{prefix} Fetching challenge (attempt {attempt}/{max_attempts})...")
                challenge = await self.user_challenge(address, challenge_type, use_proxy)
                if not challenge:
                    logger.error(f"{prefix} Failed to get challenge")
                    if attempt < max_attempts:
                        await asyncio.sleep(get_random_delay(self.pause_between_attempts))
                        continue
                    return False

                message = challenge.get("result", {}).get("challenge")
                if not message:
                    logger.error(f"{prefix} No challenge message in response")
                    if attempt < max_attempts:
                        await asyncio.sleep(get_random_delay(self.pause_between_attempts))
                        continue
                    return False

                logger.debug(f"{prefix} Logging in...")
                login = await self.user_login(private_key, address, challenge_type, message, use_proxy)
                if not login:
                    logger.error(f"{prefix} Login request failed")
                    if attempt < max_attempts:
                        await asyncio.sleep(get_random_delay(self.pause_between_attempts))
                        if rotate_proxy and use_proxy:
                            new_proxy = self.rotate_proxy_for_account(address)
                            logger.debug(f"{prefix} Rotated proxy to: {new_proxy}")
                        continue
                    return False

                result = login.get("result", {})
                token = result.get("token")
                smart_account = result.get("address")

                if not token:
                    logger.error(f"{prefix} Login response missing token. Response: {login}")
                    if attempt < max_attempts:
                        await asyncio.sleep(get_random_delay(self.pause_between_attempts))
                        continue
                    return False

                self.access_tokens[address] = token
                self.smart_accounts[address] = smart_account

                self.db.save_token(private_key, token, expires_in_hours=24)
                self.db.update_account(private_key, smart_account=smart_account)

                logger.success(f"{prefix} ✅ Token obtained successfully")
                logger.debug(f"{prefix} Smart Account: {smart_account}")

                return True

            except Exception as e:
                logger.error(f"{prefix} Error refreshing token (attempt {attempt}/{max_attempts}): {str(e)}")
                if attempt < max_attempts:
                    await asyncio.sleep(get_random_delay(self.pause_between_attempts))
                    continue
                import traceback
                traceback.print_exc()
                return False

        return False

    def build_proxy_config(self, proxy=None):
        if not proxy:
            return None, None, None
        if proxy.startswith("socks"):
            connector = ProxyConnector.from_url(proxy, ssl=self.ssl_context)
            return connector, None, None
        elif proxy.startswith("http"):
            match = re.match(r"http://(.*?):(.*?)@(.*)", proxy)
            if match:
                username, password, host_port = match.groups()
                clean_url = f"http://{host_port}"
                auth = BasicAuth(username, password)
                connector = TCPConnector(ssl=self.ssl_context)
                return connector, clean_url, auth
            else:
                connector = TCPConnector(ssl=self.ssl_context)
                return connector, proxy, None
        raise Exception("Unsupported Proxy Type.")
    def get_next_proxy_for_account(self, account: str) -> Optional[str]:
        if account not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = check_proxy_scheme(self.proxies[self.proxy_index])
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def rotate_proxy_for_account(self, account: str) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = check_proxy_scheme(self.proxies[self.proxy_index])
        self.account_proxies[account] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy

    def generate_pk_from_mnemonic(self, mnemonic: str) -> str:
        try:
            Account.enable_unaudited_hdwallet_features()
            acc = Account.from_mnemonic(mnemonic, account_path="m/44'/60'/0'/0/0")
            return acc.key.hex()
        except Exception as e:
            raise Exception(f"Generate Private Key From Mnemonic Failed: {str(e)}")

    def generate_address(self, private_key: str) -> Optional[str]:
        try:
            acc = Account.from_key(private_key)
            return acc.address
        except Exception as e:
            logger.error(f"Generate Address Failed: {str(e)}")
            return None

    def generate_payload(self, private_key: str, challenge_type: str, message: str) -> Dict[str, Any]:
        try:
            encoded_message = encode_defunct(text=message)
            signed_message = Account.sign_message(encoded_message, private_key=private_key)
            signature = to_hex(signed_message.signature)
            return {"type": challenge_type, "challenge": message, "signature": signature}
        except Exception as e:
            raise Exception(f"Generate Req Payload Failed: {str(e)}")

    def generate_random_recipient(self) -> Optional[str]:
        try:
            private_key_bytes = secrets.token_bytes(32)
            private_key_hex = to_hex(private_key_bytes)
            account = Account.from_key(private_key_hex)
            return account.address
        except Exception as e:
            return None

    def generate_transfer_data(self):
        """Generate random transfer data with random amount"""
        tokens = [
            ("native", "TCENT", self.TCENT_CONTRACT_ADDRESS, self.tcent_transfer_amount_range),
            ("erc20", "SMPL", self.SMPL_CONTRACT_ADDRESS, self.smpl_transfer_amount_range),
            ("erc20", "BULL", self.BULL_CONTRACT_ADDRESS, self.bull_transfer_amount_range),
            ("erc20", "FLIP", self.FLIP_CONTRACT_ADDRESS, self.flip_transfer_amount_range)
        ]
        token_type, ticker, contract_address, amount_range = random.choice(tokens)
        amount = self._get_random_amount(amount_range)
        return token_type, ticker, contract_address, amount

    def generate_swap_data(self):
        """Generate random swap data with random amount - returns TCENT to random ERC20"""
        options = [
            ("native to erc20", "TCENT", "SMPL", self.TCENT_CONTRACT_ADDRESS, self.SMPL_CONTRACT_ADDRESS, self.tcent_swap_amount_range),
            ("native to erc20", "TCENT", "BULL", self.TCENT_CONTRACT_ADDRESS, self.BULL_CONTRACT_ADDRESS, self.tcent_swap_amount_range),
            ("native to erc20", "TCENT", "FLIP", self.TCENT_CONTRACT_ADDRESS, self.FLIP_CONTRACT_ADDRESS, self.tcent_swap_amount_range),
        ]
        swap_type, from_ticker, to_ticker, from_token, to_token, amount_range = random.choice(options)
        amount = self._get_random_amount(amount_range)
        return swap_type, from_ticker, to_ticker, from_token, to_token, amount

    def get_reverse_swap_data(self, from_ticker: str, from_token: str):
        """Get reverse swap data to swap ERC20 back to TCENT with random amount"""
        amount_range_map = {
            "SMPL": self.smpl_swap_amount_range,
            "BULL": self.bull_swap_amount_range,
            "FLIP": self.flip_swap_amount_range,
        }

        amount_range = amount_range_map.get(from_ticker, self.smpl_swap_amount_range)
        amount = self._get_random_amount(amount_range)

        return (
            "erc20 to native",
            from_ticker,
            "TCENT",
            from_token,
            self.TCENT_CONTRACT_ADDRESS,
            amount
        )

    async def get_web3_with_check(self, address: str, use_proxy: bool, retries=5, timeout=None):
        if timeout is None:
            timeout = 90 if use_proxy else 60
        request_kwargs = {"timeout": timeout}
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        if use_proxy and proxy:
            request_kwargs["proxies"] = {"http": proxy, "https": proxy}
        for attempt in range(retries):
            try:
                web3 = Web3(Web3.HTTPProvider(self.RPC_URL, request_kwargs=request_kwargs))
                web3.eth.get_block_number()
                return web3
            except Exception as e:
                logger.debug(f"Connection attempt {attempt + 1}/{retries} failed: {str(e)}")
                if attempt < retries - 1:
                    if use_proxy:
                        logger.debug("Rotating proxy...")
                        proxy = self.rotate_proxy_for_account(address)
                        if proxy:
                            request_kwargs["proxies"] = {"http": proxy, "https": proxy}
                    await asyncio.sleep(3)
                    continue
                raise Exception(f"Failed to Connect to RPC after {retries} attempts: {str(e)}")

    async def is_contract_deployed(self, address: str, use_proxy: bool) -> bool:
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)
            smart_account = web3.to_checksum_address(self.smart_accounts[address])
            code = web3.eth.get_code(smart_account)
            is_deployed = len(code) > 2
            logger.debug(f"Contract code length: {len(code)} bytes, deployed: {is_deployed}")
            return is_deployed
        except Exception as e:
            logger.debug(f"Check contract deployment error: {str(e)}")
            return False

    async def get_nonce(self, address: str, use_proxy: bool) -> Optional[int]:
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)
            smart_account = web3.to_checksum_address(self.smart_accounts[address])
            token_contract = web3.eth.contract(address=smart_account, abi=self.CONTRACT_ABI)
            nonce = token_contract.functions.getNonce().call()
            return nonce
        except Exception as e:
            logger.debug(f"Get nonce error (expected for new accounts): {str(e)}")
            return None

    async def get_token_balance(self, address: str, contract_address: str, use_proxy: bool) -> Optional[float]:
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)
            smart_account = web3.to_checksum_address(self.smart_accounts[address])
            if contract_address == self.TCENT_CONTRACT_ADDRESS:
                balance = web3.eth.get_balance(smart_account)
            else:
                asset_address = web3.to_checksum_address(contract_address)
                token_contract = web3.eth.contract(address=asset_address, abi=self.CONTRACT_ABI)
                balance = token_contract.functions.balanceOf(smart_account).call()
            return balance / (10 ** 18)
        except Exception as e:
            logger.error(f"Get Token Balance Failed: {str(e)}")
            return None

    def pack_account_gas_limits(self, call_gas_limit: str, verification_gas_limit: str) -> bytes:
        call_val = int(call_gas_limit, 16)
        verif_val = int(verification_gas_limit, 16)
        call_hex = call_val.to_bytes(16, "big")
        verif_hex = verif_val.to_bytes(16, "big")
        return verif_hex + call_hex

    def pack_gas_fees(self, max_priority_fee_per_gas: int, max_fee_per_gas: int) -> bytes:
        prio_hex = max_priority_fee_per_gas.to_bytes(16, "big")
        max_hex = max_fee_per_gas.to_bytes(16, "big")
        return prio_hex + max_hex

    def build_transfer_calldata(self, token_type: str, contract_address: str, recipient: str, amount: float) -> bytes:
        try:
            amount_to_wei = int(amount * (10**18))
            transfer_prefix = bytes.fromhex("a9059cbb")
            execute_batch_prefix = bytes.fromhex("47e1da2a")

            if token_type == "native":
                execute_batch_data = encode(
                    ["address[]", "uint256[]", "bytes[]"],
                    [[recipient], [amount_to_wei], [b""]]
                )
                calldata_bytes = execute_batch_prefix + execute_batch_data

            elif token_type == "erc20":
                transfer_data = encode(["address", "uint256"], [recipient, amount_to_wei])
                func_bytes = transfer_prefix + transfer_data
                execute_batch_data = encode(
                    ["address[]", "uint256[]", "bytes[]"],
                    [[contract_address], [0], [func_bytes]]
                )
                calldata_bytes = execute_batch_prefix + execute_batch_data

            return calldata_bytes
        except Exception as e:
            raise Exception(f"Build Calldata Failed: {str(e)}")

    def build_swap_calldata(self, address: str, swap_type: str, from_token: str, route: list, amount: float) -> bytes:
        try:
            amount_to_wei = int(amount * (10**18))
            deadline = int(time.time()) + 600
            eth_for_tokens_prefix = bytes.fromhex("7ff36ab5")
            tokens_for_eth_prefix = bytes.fromhex("18cbafe5")
            tokens_for_tokens_prefix = bytes.fromhex("38ed1739")
            approve_prefix = bytes.fromhex("095ea7b3")
            execute_prefix = bytes.fromhex("b61d27f6")
            execute_batch_prefix = bytes.fromhex("47e1da2a")
            if swap_type == "native to erc20":
                eth_for_tokens_bytes = encode(["uint256", "address[]", "address", "uint256"], [0, route, self.smart_accounts[address], deadline])
                func_bytes = eth_for_tokens_prefix + eth_for_tokens_bytes

                execute_batch_data = encode(
                    ["address[]", "uint256[]", "bytes[]"],
                    [[self.SWAP_ROUTER_ADDRESS], [amount_to_wei], [func_bytes]]
                )
                calldata_bytes = execute_batch_prefix + execute_batch_data
            elif swap_type == "erc20 to native":
                approve_bytes = encode(["address", "uint256"], [self.SWAP_ROUTER_ADDRESS, amount_to_wei])
                tokens_for_eth_bytes = encode(["uint256", "uint256", "address[]", "address", "uint256"], [amount_to_wei, 0, route, self.smart_accounts[address], deadline])
                func_bytes = [approve_prefix + approve_bytes, tokens_for_eth_prefix + tokens_for_eth_bytes]
                execute_batch_data = encode(["address[]", "uint256[]", "bytes[]"], [[from_token, self.SWAP_ROUTER_ADDRESS], [0, 0], func_bytes])
                calldata_bytes = execute_batch_prefix + execute_batch_data
            elif swap_type == "erc20 to erc20":
                approve_bytes = encode(["address", "uint256"], [self.SWAP_ROUTER_ADDRESS, amount_to_wei])
                tokens_for_tokens_bytes = encode(["uint256", "uint256", "address[]", "address", "uint256"], [amount_to_wei, 0, route, self.smart_accounts[address], deadline])
                func_bytes = [approve_prefix + approve_bytes, tokens_for_tokens_prefix + tokens_for_tokens_bytes]
                execute_batch_data = encode(["address[]", "uint256[]", "bytes[]"], [[from_token, self.SWAP_ROUTER_ADDRESS], [0, 0], func_bytes])
                calldata_bytes = execute_batch_prefix + execute_batch_data
            return calldata_bytes
        except Exception as e:
            raise Exception(f"Build Calldata Failed: {str(e)}")

    def build_bundle_actions_calldata(self, address: str, route_1: list, route_2: list, route_3: list, amount: float) -> bytes:
        try:
            amount_to_wei = int(amount * (10**18))
            deadline = int(time.time()) + 600
            eth_for_tokens_prefix = bytes.fromhex("7ff36ab5")
            execute_batch_prefix = bytes.fromhex("47e1da2a")
            eth_for_tokens_bytes_1 = encode(["uint256", "address[]", "address", "uint256"], [0, route_1, self.smart_accounts[address], deadline])
            eth_for_tokens_bytes_2 = encode(["uint256", "address[]", "address", "uint256"], [0, route_2, self.smart_accounts[address], deadline])
            eth_for_tokens_bytes_3 = encode(["uint256", "address[]", "address", "uint256"], [0, route_3, self.smart_accounts[address], deadline])
            func_bytes = [eth_for_tokens_prefix + eth_for_tokens_bytes_1, eth_for_tokens_prefix + eth_for_tokens_bytes_2, eth_for_tokens_prefix + eth_for_tokens_bytes_3]
            execute_batch_data = encode(["address[]", "uint256[]", "bytes[]"], [[self.SWAP_ROUTER_ADDRESS, self.SWAP_ROUTER_ADDRESS, self.SWAP_ROUTER_ADDRESS], [amount_to_wei, amount_to_wei, amount_to_wei], func_bytes])
            calldata_bytes = execute_batch_prefix + execute_batch_data
            return calldata_bytes
        except Exception as e:
            raise Exception(f"Build Calldata Failed: {str(e)}")

    async def get_estimate_gas(self, address: str, calldata: bytes, use_proxy: bool) -> Optional[Dict[str, Any]]:
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)
            user_operation = {"sender": web3.to_checksum_address(self.smart_accounts[address]), "nonce": to_hex(self.used_nonce[address]), "callData": to_hex(calldata), "signature": "0xfffffffffffffffffffffffffffffff0000000000000000000000000000000007aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1c"}
            gas_data = await self.send_transaction(address, "eth_estimateUserOperationGas", user_operation, use_proxy)
            if gas_data:
                if "result" in gas_data:
                    return gas_data.get("result")
                elif "error" in gas_data:
                    err_msg = gas_data.get("error", {}).get("message", "Unknown Error")
                    logger.error(f"Fetch Estimate Gas Failed: {err_msg}")
            return None
        except Exception as e:
            logger.error(f"Get Estimate Gas Error: {str(e)}")
            return None

    async def get_estimate_gas_with_paymaster(self, address: str, calldata: bytes, use_proxy: bool) -> Optional[Dict[str, Any]]:
        """Get estimated gas WITH paymaster for ERC20 gas transactions"""
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)

            user_operation = {
                "sender": web3.to_checksum_address(self.smart_accounts[address]),
                "nonce": to_hex(self.used_nonce[address]),
                "paymaster": web3.to_checksum_address(self.PAYMASTER_ADDRESS),
                "paymasterData": "0x",
                "callData": to_hex(calldata),
                "signature": "0xfffffffffffffffffffffffffffffff0000000000000000000000000000000007aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1c"
            }

            gas_data = await self.send_transaction(address, "eth_estimateUserOperationGas", user_operation, use_proxy)
            if gas_data:
                if "result" in gas_data:
                    return gas_data.get("result")
                elif "error" in gas_data:
                    err_msg = gas_data.get("error", {}).get("message", "Unknown Error")
                    logger.error(f"Fetch Estimate Gas with Paymaster Failed: {err_msg}")
            return None
        except Exception as e:
            logger.error(f"Get Estimate Gas with Paymaster Error: {str(e)}")
            return None

    async def get_user_op_hash(self, private_key: str, address: str, calldata: bytes, gas: dict, use_proxy: bool) -> Optional[str]:
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)
            account_gas_limits = self.pack_account_gas_limits(gas["callGasLimit"], gas["verificationGasLimit"])
            max_priority_fee = web3.to_wei(1.5, "gwei")
            max_fee = max_priority_fee
            gas_fees = self.pack_gas_fees(max_priority_fee, max_fee)
            if isinstance(gas["preVerificationGas"], str):
                pre_verif_gas = int(gas["preVerificationGas"], 16)
            else:
                pre_verif_gas = int(gas["preVerificationGas"])
            packed_user_operation = (web3.to_checksum_address(self.smart_accounts[address]), int(self.used_nonce[address]), b"", calldata, account_gas_limits, pre_verif_gas, gas_fees, b"", b"")
            entrypoint = web3.to_checksum_address(self.ENTRYPOINT_ADDRESS)
            token_contract = web3.eth.contract(address=entrypoint, abi=self.CONTRACT_ABI)
            signature = token_contract.functions.getUserOpHash(packed_user_operation).call()
            acct = Account.from_key(private_key)
            signed = acct.sign_message(encode_defunct(primitive=signature))
            raw_sig = to_hex(signed.signature)
            sig_with_mode = "0x000001" + raw_sig[2:]
            return sig_with_mode
        except Exception as e:
            logger.error(f"Get User Op Hash Error: {str(e)}")
            return None

    async def check_connection(self, proxy_url=None) -> bool:
        connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get(url="https://api.ipify.org?format=json", proxy=proxy, proxy_auth=proxy_auth) as response:
                    response.raise_for_status()
                    return True
        except (Exception, ClientResponseError) as e:
            logger.error(f"Connection Failed: {str(e)}")
            return False

    async def user_challenge(self, address: str, challenge_type: str, use_proxy: bool, retries=5) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_API}/api/user/challenge?type={challenge_type}&address={address}"
        for attempt in range(retries):
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.get(url=url, headers=self.BASE_HEADERS[address], proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                logger.error(f"Fetch Challenge Failed: {str(e)}")
        return None

    async def user_login(self, private_key: str, address: str, challenge_type: str, message: str, use_proxy: bool, retries=5) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_API}/api/user/login"
        data = json.dumps(self.generate_payload(private_key, challenge_type, message))
        headers = {**self.BASE_HEADERS[address], "Content-Length": str(len(data)), "Content-Type": "application/json"}
        for attempt in range(retries):
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                logger.error(f"Login Failed: {str(e)}")
        return None

    async def user_data(self, address: str, use_proxy: bool, retries=10) -> Optional[Dict[str, Any]]:
        prefix = self._log_prefix(address)
        url = f"{self.BASE_API}/api/user"

        for attempt in range(retries):
            headers = {**self.BASE_HEADERS[address], "Authorization": f"Bearer {self.access_tokens.get(address) or ''}", "Token": self.access_tokens.get(address) or ''}
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)

            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.get(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        if response.status == 401:
                            logger.warning(f"{prefix} 401 Unauthorized - token expired, refreshing...")
                            private_key = self.private_keys.get(address)

                            if private_key:
                                for refresh_attempt in range(3):
                                    logger.debug(f"{prefix} Refresh attempt {refresh_attempt + 1}/3")
                                    refreshed = await self.refresh_token(private_key, address, use_proxy, False)

                                    if refreshed:
                                        logger.success(f"{prefix} ✅ Token refreshed, retrying request...")
                                        await asyncio.sleep(2)
                                        break
                                    elif refresh_attempt < 2:
                                        logger.warning(f"{prefix} Refresh failed, attempt {refresh_attempt + 1}/3")
                                        await asyncio.sleep(3)

                                if refreshed:
                                    continue
                                else:
                                    logger.error(f"{prefix} ❌ Failed to refresh token after 3 attempts")
                                    return None

                        response.raise_for_status()
                        return await response.json()

            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    logger.debug(f"{prefix} Request attempt {attempt + 1} failed: {str(e)}")
                    await asyncio.sleep(5)
                    continue
                logger.error(f"{prefix} Fetch User Data Failed: {str(e)}")

        return None

    async def claim_faucet(self, address: str, turnstile_token: str, use_proxy: bool, retries=5) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_API}/api/user/faucet"
        data = json.dumps({"verificationToken": turnstile_token})
        for attempt in range(retries):
            headers = {**self.BASE_HEADERS[address], "Authorization": f"Bearer {self.access_tokens.get(address) or ''}", "Content-Length": str(len(data)), "Content-Type": "application/json", "Token": self.access_tokens.get(address) or ''}
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        if response.status == 401:
                            logger.warning("401 Unauthorized - token expired, refreshing...")
                            private_key = self.private_keys.get(address)
                            if private_key and attempt < retries - 1:
                                refreshed = await self.refresh_token(private_key, address, use_proxy, False)
                                if refreshed:
                                    await asyncio.sleep(2)
                                    continue
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                logger.error(f"Claim Faucet Failed: {str(e)}")
        return None

    async def add_contacts(self, address: str, contact_name: str, contact_address: str, use_proxy: bool, retries=5) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_API}/api/user/contacts"
        data = json.dumps({"name": contact_name, "address": contact_address})
        for attempt in range(retries):
            headers = {**self.BASE_HEADERS[address], "Content-Length": str(len(data)), "Content-Type": "application/json", "Token": self.access_tokens.get(address) or ''}
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        if response.status == 401:
                            logger.warning("401 Unauthorized - token expired, refreshing...")
                            private_key = self.private_keys.get(address)
                            if private_key and attempt < retries - 1:
                                refreshed = await self.refresh_token(private_key, address, use_proxy, False)
                                if refreshed:
                                    await asyncio.sleep(2)
                                    continue
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                logger.error(f"Add Contact Failed: {str(e)}")
        return None

    async def swap_route(self, address: str, from_token: str, to_token: str, use_proxy: bool, retries=10) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_API}/api/user/swap-route?from={from_token}&to={to_token}"
        for attempt in range(retries):
            headers = {**self.BASE_HEADERS[address], "Token": self.access_tokens.get(address) or ''}
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.get(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        if response.status == 401:
                            logger.warning("401 Unauthorized - token expired, refreshing...")
                            private_key = self.private_keys.get(address)
                            if private_key and attempt < retries - 1:
                                refreshed = await self.refresh_token(private_key, address, use_proxy, False)
                                if refreshed:
                                    await asyncio.sleep(2)
                                    continue
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                logger.error(f"Fetch Swap Route Failed: {str(e)}")
        return None

    async def send_transaction(self, address: str, method_name: str, user_operation: dict, use_proxy: bool, retries=5) -> Optional[Dict[str, Any]]:
        data = json.dumps({"method": method_name, "params": [user_operation, self.ENTRYPOINT_ADDRESS], "id": 1, "jsonrpc": "2.0"})
        headers = {**self.BUNDLER_HEADERS[address], "Content-Length": str(len(data)), "Content-Type": "application/json"}
        for attempt in range(retries):
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.post(url=self.BUNDLER_URL, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                logger.error(f"{method_name} Failed: {str(e)}")
        return None

    async def transaction_badge(self, address: str, tx_hash: str, badge_key: str, use_proxy: bool, retries=50) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_API}/api/user/transaction-badge"
        data = json.dumps({"txHash": tx_hash, "badgeKey": badge_key})
        for attempt in range(retries):
            headers = {**self.BASE_HEADERS[address], "Content-Length": str(len(data)), "Content-Type": "application/json", "Token": self.access_tokens.get(address) or ''}
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        if response.status == 401:
                            logger.warning("401 Unauthorized - token expired, refreshing...")
                            private_key = self.private_keys.get(address)
                            if private_key and attempt < retries - 1:
                                refreshed = await self.refresh_token(private_key, address, use_proxy, False)
                                if refreshed:
                                    await asyncio.sleep(2)
                                    continue
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                logger.error(f"Submit Transaction Badge Failed: {str(e)}")
        return None

    async def perform_transaction(self, private_key: str, address: str, calldata: bytes, use_proxy: bool) -> Optional[str]:
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)
            gas = await self.get_estimate_gas(address, calldata, use_proxy)
            if gas is None:
                return None
            signature = await self.get_user_op_hash(private_key, address, calldata, gas, use_proxy)
            if signature is None:
                return None
            max_priority_fee = web3.to_wei(1.5, "gwei")
            max_fee = max_priority_fee
            user_operation = {"sender": web3.to_checksum_address(self.smart_accounts[address]), "nonce": to_hex(self.used_nonce[address]), "callData": to_hex(calldata), "callGasLimit": gas["callGasLimit"], "verificationGasLimit": gas["verificationGasLimit"], "maxFeePerGas": to_hex(max_priority_fee), "maxPriorityFeePerGas": to_hex(max_fee), "preVerificationGas": gas["preVerificationGas"], "signature": signature}
            send_operation = await self.send_transaction(address, "eth_sendUserOperation", user_operation, use_proxy)
            if send_operation:
                if "result" in send_operation:
                    result = send_operation.get("result")
                    self.used_nonce[address] += 1
                    return result
                elif "error" in send_operation:
                    err_msg = send_operation.get("error", {}).get("message", "Unknown Error")
                    logger.error(f"Send Transaction Failed: {err_msg}")
            return None
        except Exception as e:
            logger.error(f"Perform Transaction Error: {str(e)}")
            return None

    def get_token_address(self, ticker: str) -> str:
        """Get contract address by token ticker"""
        token_map = {
            'TCENT': self.TCENT_CONTRACT_ADDRESS,
            'SMPL': self.SMPL_CONTRACT_ADDRESS,
            'BULL': self.BULL_CONTRACT_ADDRESS,
            'FLIP': self.FLIP_CONTRACT_ADDRESS,
            'WCENT': self.WCENT_CONTRACT_ADDRESS
        }
        return token_map.get(ticker, self.TCENT_CONTRACT_ADDRESS)

    async def select_best_gas_token(self, address: str, use_proxy: bool, transaction_index: int = 0) -> tuple[Optional[str], Optional[str]]:
        """
        Smart gas token selection - tries all available tokens before falling back to TCENT

        Returns:
            (token_ticker, token_address) or (None, None) if no suitable token found
        """
        prefix = self._log_prefix(address)

        if self.unified_token_randomize:
            import random
            token_list = self.unified_token_gas_tokens.copy()
            random.shuffle(token_list)
        else:
            token_list = self.unified_token_gas_tokens

        logger.debug(f"{prefix} 🔍 Searching for suitable gas token...")

        for token_ticker in token_list:
            token_address = self.get_token_address(token_ticker)

            token_balance = await self.get_token_balance(address, token_address, use_proxy)

            if token_balance is not None and token_balance >= self.unified_token_min_balance:
                logger.info(f"{prefix} ✅ Found {token_ticker} for gas: {token_balance:.4f}")
                return token_ticker, token_address
            else:
                balance_str = f"{token_balance:.4f}" if token_balance else "0"
                logger.debug(f"{prefix} ⚠️  {token_ticker} insufficient: {balance_str} < {self.unified_token_min_balance}")

        logger.debug(f"{prefix} 💡 No ERC20 token available for gas, using native TCENT")
        return None, None

    async def perform_transaction_with_erc20_gas(
            self,
            private_key: str,
            address: str,
            calldata: bytes,
            gas_token_address: str,
            use_proxy: bool
    ) -> Optional[str]:
        """Perform transaction with ERC20 token as gas payment using paymaster"""
        prefix = self._log_prefix(address)
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)

            gas = await self.get_estimate_gas(address, calldata, use_proxy)
            if gas is None:
                logger.error(f"{prefix} Failed to get gas estimation")
                return None

            paymaster_address = web3.to_checksum_address(self.PAYMASTER_ADDRESS)

            max_priority_fee = web3.to_wei(1.5, "gwei")
            max_fee = max_priority_fee

            if isinstance(gas["preVerificationGas"], str):
                pre_verif_gas_value = int(gas["preVerificationGas"], 16)
            else:
                pre_verif_gas_value = int(gas["preVerificationGas"])

            if isinstance(gas["callGasLimit"], str):
                call_gas_value = int(gas["callGasLimit"], 16)
            else:
                call_gas_value = int(gas["callGasLimit"])

            if isinstance(gas["verificationGasLimit"], str):
                verif_gas_value = int(gas["verificationGasLimit"], 16)
            else:
                verif_gas_value = int(gas["verificationGasLimit"])

            logger.debug(f"{prefix} Gas from regular estimate:")
            logger.debug(f"{prefix}   preVerificationGas: {pre_verif_gas_value}")
            logger.debug(f"{prefix}   callGasLimit: {call_gas_value}")
            logger.debug(f"{prefix}   verificationGasLimit: {verif_gas_value}")

            pre_verif_gas_increased = int(pre_verif_gas_value * 1.3)
            call_gas_increased = int(call_gas_value * 1.3)
            verif_gas_increased = int(verif_gas_value * 1.3)

            logger.debug(f"{prefix} Gas increased for paymaster:")
            logger.debug(f"{prefix}   preVerificationGas: {pre_verif_gas_increased}")
            logger.debug(f"{prefix}   callGasLimit: {call_gas_increased}")
            logger.debug(f"{prefix}   verificationGasLimit: {verif_gas_increased}")

            gas_for_signature = {
                "callGasLimit": to_hex(call_gas_increased),
                "verificationGasLimit": to_hex(verif_gas_increased),
                "preVerificationGas": pre_verif_gas_increased
            }

            paymaster_data_bytes = b''

            signature = await self.get_user_op_hash_with_paymaster(
                private_key, address, calldata, gas_for_signature,
                paymaster_address, paymaster_data_bytes, use_proxy
            )
            if signature is None:
                logger.error(f"{prefix} Failed to generate signature with paymaster")
                return None

            user_operation = {
                "sender": web3.to_checksum_address(self.smart_accounts[address]),
                "nonce": to_hex(self.used_nonce[address]),
                "callData": to_hex(calldata),
                "callGasLimit": to_hex(call_gas_increased),
                "verificationGasLimit": to_hex(verif_gas_increased),
                "maxFeePerGas": to_hex(max_priority_fee),
                "maxPriorityFeePerGas": to_hex(max_fee),
                "preVerificationGas": to_hex(pre_verif_gas_increased),
                "paymaster": paymaster_address,
                "paymasterPostOpGasLimit": "1000000",
                "paymasterVerificationGasLimit": "1000000",
                "paymasterData": to_hex(paymaster_data_bytes),
                "signature": signature
            }

            logger.debug(f"{prefix} Sending transaction with ERC20 gas via paymaster...")
            send_operation = await self.send_transaction(
                address, "eth_sendUserOperation", user_operation, use_proxy
            )

            if send_operation:
                if "result" in send_operation:
                    result = send_operation.get("result")
                    self.used_nonce[address] += 1
                    logger.success(f"{prefix} ✅ Transaction sent with ERC20 gas: {result[:16]}...")
                    return result
                elif "error" in send_operation:
                    err_msg = send_operation.get("error", {}).get("message", "Unknown Error")
                    err_code = send_operation.get("error", {}).get("code", "N/A")
                    logger.error(f"{prefix} ❌ Paymaster transaction failed: {err_msg} (code: {err_code})")
                    logger.debug(f"{prefix} Full error: {send_operation.get('error')}")
                    return None

            logger.error(f"{prefix} ❌ No response from bundler for paymaster transaction")
            return None

        except Exception as e:
            logger.error(f"{prefix} ERC20 Gas Transaction Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    async def get_user_op_hash_with_paymaster(
            self,
            private_key: str,
            address: str,
            calldata: bytes,
            gas: dict,
            paymaster_address: str,
            paymaster_data: bytes,
            use_proxy: bool
    ) -> Optional[str]:
        """Get user operation hash with paymaster

        Args:
            paymaster_address: Address of the paymaster contract
            paymaster_data: Additional data for paymaster (can be token address)
        """
        prefix = self._log_prefix(address)
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)

            account_gas_limits = self.pack_account_gas_limits(
                gas["callGasLimit"], gas["verificationGasLimit"]
            )

            max_priority_fee = web3.to_wei(1.5, "gwei")
            max_fee = max_priority_fee
            gas_fees = self.pack_gas_fees(max_priority_fee, max_fee)

            if isinstance(gas["preVerificationGas"], str):
                pre_verif_gas = int(gas["preVerificationGas"], 16)
            else:
                pre_verif_gas = int(gas["preVerificationGas"])

            paymaster_address_bytes = bytes.fromhex(paymaster_address[2:] if paymaster_address.startswith('0x') else paymaster_address)
            paymaster_and_data = paymaster_address_bytes + paymaster_data

            packed_user_operation = (
                web3.to_checksum_address(self.smart_accounts[address]),
                int(self.used_nonce[address]),
                b"",
                calldata,
                account_gas_limits,
                pre_verif_gas,
                gas_fees,
                paymaster_and_data,
                b""
            )

            entrypoint = web3.to_checksum_address(self.ENTRYPOINT_ADDRESS)
            token_contract = web3.eth.contract(address=entrypoint, abi=self.CONTRACT_ABI)
            user_op_hash = token_contract.functions.getUserOpHash(packed_user_operation).call()

            acct = Account.from_key(private_key)
            signed = acct.sign_message(encode_defunct(primitive=user_op_hash))

            raw_sig = to_hex(signed.signature)
            sig_with_mode = "0x000001" + raw_sig[2:]

            logger.debug(f"{prefix} Generated signature with paymaster")
            return sig_with_mode

        except Exception as e:
            logger.error(f"{prefix} Get UserOp Hash with Paymaster Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    async def process_check_connection(self, address: str, use_proxy: bool, rotate_proxy: bool) -> bool:
        while True:
            proxy = self.rotate_proxy_for_account(address) if use_proxy else None
            if proxy:
                logger.info(f"Using proxy: {proxy}")
            is_valid = await self.check_connection(proxy)
            if not is_valid:
                if rotate_proxy:
                    logger.warning("Rotating to next proxy...")
                    proxy = self.rotate_proxy_for_account(address)
                    await asyncio.sleep(1)
                    continue
                return False
            return True

    async def process_user_login(self, private_key: str, address: str, use_proxy: bool, rotate_proxy: bool) -> bool:
        """Process user login with retries"""
        prefix = self._log_prefix(address)

        max_attempts = self.attempts

        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(f"{prefix} Login attempt {attempt}/{max_attempts}")

                if await self.ensure_valid_token(private_key, address, use_proxy, rotate_proxy):
                    logger.success(f"{prefix} ✅ Authentication successful")
                    return True

                if attempt < max_attempts:
                    delay = get_random_delay(self.pause_between_attempts)
                    logger.warning(f"{prefix} ⚠️ Login attempt {attempt} failed, retrying in {delay}s...")
                    await asyncio.sleep(delay)

                    if rotate_proxy and use_proxy:
                        new_proxy = self.rotate_proxy_for_account(address)
                        logger.info(f"{prefix} 🔄 Rotating proxy to: {new_proxy}")
                else:
                    logger.error(f"{prefix} ❌ All {max_attempts} login attempts failed")
                    return False

            except Exception as e:
                logger.error(f"{prefix} Login attempt {attempt} error: {str(e)}")
                if attempt < max_attempts:
                    delay = get_random_delay(self.pause_between_attempts)
                    await asyncio.sleep(delay)
                else:
                    return False

        return False

    async def process_faucet_claim(self, private_key: str, address: str, account_id: int, use_proxy: bool, is_first_claim: bool = False):
        prefix = self._log_prefix(address)
        import pytz

        if is_first_claim:
            logger.action("ACCOUNT ACTIVATION", f"{prefix} Deploying smart account contract...")
        else:
            logger.action("FAUCET CLAIM", f"{prefix} Checking faucet availability...")

        now_time = int(time.time()) * 1000
        claim_time = self.faucet_times.get(address)

        if not is_first_claim and claim_time and claim_time > now_time:
            almaty = pytz.timezone('Asia/Almaty')
            formatted_time = datetime.fromtimestamp(claim_time / 1000).astimezone(almaty).strftime('%Y-%m-%d %H:%M:%S')
            logger.warning(f"{prefix} Faucet not ready. Next claim at: {formatted_time}")
            time_until_next = (claim_time - now_time) / 1000
            hours = int(time_until_next // 3600)
            minutes = int((time_until_next % 3600) // 60)
            logger.warning(f"{prefix} ⏳ Wait time: {hours}h {minutes}m")
            return False

        if is_first_claim:
            logger.info(f"{prefix} 🔐 Solving captcha for deployment...")
        else:
            logger.info(f"{prefix} 🔐 Solving captcha...")

        turnstile_token = await self.captcha_solver.solve_turnstile(self.SITE_KEY, self.PAGE_URL)
        if not turnstile_token:
            logger.error(f"{prefix} ❌ Failed to solve captcha")
            self.db.add_statistic(account_id, "faucet_claim", "failed", "Captcha solving failed")
            if is_first_claim:
                logger.error(f"{prefix} ❌ Cannot deploy without captcha. Skipping account.")
            return False

        if is_first_claim:
            logger.info(f"{prefix} 📤 Executing deployment transaction...")

        claim = await self.claim_faucet(address, turnstile_token, use_proxy)
        if claim:
            amount = claim.get("result", {}).get("amount")
            if is_first_claim:
                logger.success(f"{prefix} ✅ Smart account deployed successfully!")
                logger.success(f"{prefix} ✅ Received {amount} TCENT as activation bonus")
                self.used_nonce[address] = 1
                logger.info(f"{prefix} ✅ Contract deployed, starting nonce set to 1")
                if self.smart_accounts.get(address):
                    self.db.update_account(private_key, smart_account=self.smart_accounts[address])
                    logger.debug(f"{prefix} Smart account saved to DB: {self.smart_accounts[address]}")
            else:
                logger.success(f"{prefix} ✅ Claimed {amount} TCENT from faucet")

            self.db.add_statistic(account_id, "faucet_claim", "success", f"Claimed {amount} TCENT")

            user = await self.user_data(address, use_proxy)
            if user:
                next_claim_time = user.get("result", {}).get("nextFaucetRequestTimestamp")
                if next_claim_time:
                    self.faucet_times[address] = next_claim_time
                    almaty = pytz.timezone('Asia/Almaty')
                    formatted_time = datetime.fromtimestamp(next_claim_time / 1000).astimezone(almaty).strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"{prefix} ⏰ Next faucet claim available at: {formatted_time}")
                    time_until_next = (next_claim_time - now_time) / 1000
                    hours = int(time_until_next // 3600)
                    minutes = int((time_until_next % 3600) // 60)
                    logger.info(f"{prefix} ⏳ Time until next claim: {hours}h {minutes}m")

            return True
        else:
            if is_first_claim:
                logger.error(f"{prefix} ❌ Failed to deploy smart account")
            else:
                logger.error(f"{prefix} ❌ Faucet claim failed")
            self.db.add_statistic(account_id, "faucet_claim", "failed")
            return False

    async def process_add_contacts(self, address: str, account_id: int, count: int, use_proxy: bool):
        prefix = self._log_prefix(address)

        logger.action("ADD CONTACTS", f"{prefix} Adding {count} random contacts...")
        for i in range(count):
            logger.info(f"{prefix} Contact {i+1}/{count}")
            contact_name = f"Contact-{int(time.time())}"
            contact_address = self.generate_random_recipient()
            logger.debug(f"{prefix} Name: {contact_name}, Address: {contact_address[:10]}...")

            result = await self.add_contacts(address, contact_name, contact_address, use_proxy)
            if result and result.get("code") == 201:
                logger.success(f"{prefix} Contact added successfully")
                self.db.add_statistic(account_id, "add_contact", "success", contact_name)
            else:
                logger.error(f"{prefix} Failed to add contact")
                self.db.add_statistic(account_id, "add_contact", "failed", contact_name)

            if i < count - 1:
                delay = get_random_delay(self.pause_between_actions)
                logger.info(f"{prefix} ⏳ Waiting {delay}s before next contact...")
                await asyncio.sleep(delay)

    async def process_transfers(self, private_key: str, address: str, account_id: int, count: int, use_proxy: bool):
        prefix = self._log_prefix(address)

        logger.action("TRANSFERS", f"{prefix} Performing {count} random transfers...")
        for i in range(count):
            logger.info(f"{prefix} 📤 Transfer {i+1}/{count}")
            recipient = self.generate_random_recipient()
            token_type, ticker, contract_address, amount = self.generate_transfer_data()
            logger.debug(f"{prefix} Token: {ticker}, Amount: {amount}, To: {recipient[:10]}...")

            balance = await self.get_token_balance(address, contract_address, use_proxy)
            logger.info(f"{prefix} 💰 Balance: {balance} {ticker}")

            if balance is None or balance < amount:
                logger.warning(f"{prefix} ⚠️ Insufficient {ticker} balance: {balance}")
                self.db.add_statistic(account_id, "transfer", "failed", f"Insufficient {ticker} balance")
                continue

            calldata = self.build_transfer_calldata(token_type, contract_address, recipient, amount)

            gas_type = "TCENT"
            tx_hash = None

            if self.unified_token_enabled and ticker == "TCENT":
                gas_token_ticker, gas_token_address = await self.select_best_gas_token(address, use_proxy, i)

                if gas_token_ticker and gas_token_address:
                    logger.info(f"{prefix} ⛽ Using {gas_token_ticker} for gas payment")
                    tx_hash = await self.perform_transaction_with_erc20_gas(
                        private_key, address, calldata, gas_token_address, use_proxy
                    )
                    if tx_hash:
                        gas_type = gas_token_ticker
                else:
                    tx_hash = await self.perform_transaction(private_key, address, calldata, use_proxy)
            else:
                tx_hash = await self.perform_transaction(private_key, address, calldata, use_proxy)

            if tx_hash:
                logger.success(f"{prefix} ✅ Transfer successful: {tx_hash}")
                if gas_type != "TCENT":
                    logger.success(f"{prefix} 🎯 Gas paid with {gas_type} (UnifiedToken)")
                logger.info(f"{prefix} 🔗 Explorer: {self.EXPLORER}{tx_hash}")
                await self.transaction_badge(address, tx_hash, "FIRST_TRANSFER", use_proxy)
                self.db.add_statistic(account_id, "transfer", "success", f"{amount} {ticker} (gas: {gas_type})", tx_hash)
            else:
                logger.error(f"{prefix} ❌ Transfer failed")
                self.db.add_statistic(account_id, "transfer", "failed", f"{amount} {ticker}")

            if i < count - 1:
                delay = get_random_delay(self.pause_between_swaps)
                logger.info(f"{prefix} ⏳ Waiting {delay}s before next transfer...")
                await asyncio.sleep(delay)

    async def process_swaps(self, private_key: str, address: str, account_id: int, count: int, use_proxy: bool):
        prefix = self._log_prefix(address)

        logger.action("SWAPS", f"{prefix} Performing {count} paired swaps (TCENT→Token→TCENT)...")
        for i in range(count):
            logger.info(f"{prefix} ━━━━━ Swap Pair {i+1}/{count} ━━━━━")

            swap_type, from_ticker, to_ticker, from_token, to_token, amount = self.generate_swap_data()
            logger.info(f"{prefix} 📊 Swap Pair: {from_ticker} → {to_ticker}")
            logger.info(f"{prefix} 💰 Amount: {amount} {from_ticker}")

            balance = await self.get_token_balance(address, from_token, use_proxy)
            logger.info(f"{prefix} 💳 Balance: {balance} {from_ticker}")

            if balance is None or balance < amount:
                logger.warning(f"{prefix} ⚠️ Insufficient {from_ticker} balance")
                self.db.add_statistic(account_id, "swap", "failed", f"Insufficient {from_ticker} balance")
                continue

            route_data = await self.swap_route(address, from_token, to_token, use_proxy)
            if not route_data:
                logger.error(f"{prefix} ❌ Failed to get swap route")
                self.db.add_statistic(account_id, "swap", "failed", "Route fetch failed")
                continue

            route = route_data["result"][0]["route"]
            calldata = self.build_swap_calldata(address, swap_type, from_token, route, amount)

            gas_type = "TCENT"
            tx_hash = None

            if self.unified_token_enabled:
                gas_token_ticker, gas_token_address = await self.select_best_gas_token(address, use_proxy, i)

                if gas_token_ticker and gas_token_address:
                    logger.info(f"{prefix} ⛽ Using {gas_token_ticker} for gas payment")
                    tx_hash = await self.perform_transaction_with_erc20_gas(
                        private_key, address, calldata, gas_token_address, use_proxy
                    )
                    if tx_hash:
                        gas_type = gas_token_ticker
                else:
                    tx_hash = await self.perform_transaction(private_key, address, calldata, use_proxy)
            else:
                tx_hash = await self.perform_transaction(private_key, address, calldata, use_proxy)

            if tx_hash:
                logger.success(f"{prefix} ✅ Step 1 Success")
                if gas_type != "TCENT":
                    logger.success(f"{prefix} 🎯 Gas paid with {gas_type} (UnifiedToken)")
                logger.info(f"{prefix} 🔗 Tx Hash: {tx_hash}")
                logger.info(f"{prefix} 🔗 Explorer: {self.EXPLORER}{tx_hash}")
                await self.transaction_badge(address, tx_hash, "FIRST_SWAP", use_proxy)
                self.db.add_statistic(account_id, "swap", "success", f"{from_ticker} -> {to_ticker} (gas: {gas_type})", tx_hash)
            else:
                logger.error(f"{prefix} ❌ Step 1 Failed - skipping reverse swap")
                self.db.add_statistic(account_id, "swap", "failed", f"{from_ticker} -> {to_ticker}")
                continue

            delay = get_random_delay(self.pause_between_actions)
            logger.info(f"{prefix} ⏳ Waiting {delay}s before reverse swap...")
            await asyncio.sleep(delay)

            reverse_swap_type, reverse_from_ticker, reverse_to_ticker, reverse_from_token, reverse_to_token, reverse_amount = self.get_reverse_swap_data(to_ticker, to_token)
            logger.info(f"{prefix} 📊 Reverse Swap: {reverse_from_ticker} → {reverse_to_ticker}")
            logger.info(f"{prefix} 💰 Amount: {reverse_amount} {reverse_from_ticker}")

            reverse_balance = await self.get_token_balance(address, reverse_from_token, use_proxy)
            logger.info(f"{prefix} 💳 Balance: {reverse_balance} {reverse_from_ticker}")

            if reverse_balance is None or reverse_balance < reverse_amount:
                logger.warning(f"{prefix} ⚠️ Insufficient {reverse_from_ticker} balance for reverse swap")
                self.db.add_statistic(account_id, "swap", "failed", f"Insufficient {reverse_from_ticker} for reverse")
            else:
                reverse_route_data = await self.swap_route(address, reverse_from_token, reverse_to_token, use_proxy)
                if not reverse_route_data:
                    logger.error(f"{prefix} ❌ Failed to get reverse swap route")
                    self.db.add_statistic(account_id, "swap", "failed", "Reverse route fetch failed")
                else:
                    reverse_route = reverse_route_data["result"][0]["route"]
                    reverse_calldata = self.build_swap_calldata(address, reverse_swap_type, reverse_from_token, reverse_route, reverse_amount)

                    reverse_gas_type = "TCENT"
                    reverse_tx_hash = None

                    if self.unified_token_enabled:
                        reverse_gas_token_ticker, reverse_gas_token_address = await self.select_best_gas_token(address, use_proxy, i + 1000)

                        if reverse_gas_token_ticker and reverse_gas_token_address:
                            logger.info(f"{prefix} ⛽ Using {reverse_gas_token_ticker} for gas payment")
                            reverse_tx_hash = await self.perform_transaction_with_erc20_gas(
                                private_key, address, reverse_calldata, reverse_gas_token_address, use_proxy
                            )
                            if reverse_tx_hash:
                                reverse_gas_type = reverse_gas_token_ticker
                        else:
                            reverse_tx_hash = await self.perform_transaction(private_key, address, reverse_calldata, use_proxy)
                    else:
                        reverse_tx_hash = await self.perform_transaction(private_key, address, reverse_calldata, use_proxy)

                    if reverse_tx_hash:
                        logger.success(f"{prefix} ✅ Step 2 Success")
                        if reverse_gas_type != "TCENT":
                            logger.success(f"{prefix} 🎯 Gas paid with {reverse_gas_type} (UnifiedToken)")
                        logger.info(f"{prefix} 🔗 Tx Hash: {reverse_tx_hash}")
                        logger.info(f"{prefix} 🔗 Explorer: {self.EXPLORER}{reverse_tx_hash}")
                        await self.transaction_badge(address, reverse_tx_hash, "FIRST_SWAP", use_proxy)
                        self.db.add_statistic(account_id, "swap", "success", f"{reverse_from_ticker} -> {reverse_to_ticker} (gas: {reverse_gas_type})", reverse_tx_hash)
                        logger.success(f"{prefix} ✅ Swap Pair Completed: {from_ticker}→{to_ticker}→{from_ticker}")
                    else:
                        logger.error(f"{prefix} ❌ Step 2 Failed")
                        self.db.add_statistic(account_id, "swap", "failed", f"{reverse_from_ticker} -> {reverse_to_ticker}")

            if i < count - 1:
                delay = get_random_delay(self.pause_between_swaps)
                logger.info(f"{prefix} ⏳ Waiting {delay}s before next swap pair...")
                await asyncio.sleep(delay)

    async def process_bundle_actions(self, private_key: str, address: str, account_id: int, count: int, use_proxy: bool):
        prefix = self._log_prefix(address)

        logger.action("BUNDLE ACTIONS", f"{prefix} Performing {count} bundle actions...")
        for i in range(count):
            logger.info(f"{prefix} Bundle {i+1}/{count}")
            bundle_amount = self._get_random_amount(self.bundle_action_amount_range)
            total_amount = bundle_amount * 3
            logger.debug(f"{prefix} Bundle: TCENT->SMPL, TCENT->BULL, TCENT->FLIP (Total: {total_amount} TCENT)")

            balance = await self.get_token_balance(address, self.TCENT_CONTRACT_ADDRESS, use_proxy)
            logger.info(f"{prefix} 💰 Balance: {balance} TCENT")

            if balance is None or balance < total_amount:
                logger.warning(f"{prefix} ⚠️ Insufficient TCENT balance: {balance}")
                self.db.add_statistic(account_id, "bundle_action", "failed", "Insufficient TCENT balance")
                continue

            route_1 = (await self.swap_route(address, self.TCENT_CONTRACT_ADDRESS, self.SMPL_CONTRACT_ADDRESS, use_proxy))["result"][0]["route"]
            route_2 = (await self.swap_route(address, self.TCENT_CONTRACT_ADDRESS, self.BULL_CONTRACT_ADDRESS, use_proxy))["result"][0]["route"]
            route_3 = (await self.swap_route(address, self.TCENT_CONTRACT_ADDRESS, self.FLIP_CONTRACT_ADDRESS, use_proxy))["result"][0]["route"]

            calldata = self.build_bundle_actions_calldata(address, route_1, route_2, route_3, bundle_amount)

            gas_type = "TCENT"
            tx_hash = None

            if self.unified_token_enabled:
                gas_token_ticker, gas_token_address = await self.select_best_gas_token(address, use_proxy, i)

                if gas_token_ticker and gas_token_address:
                    logger.info(f"{prefix} ⛽ Using {gas_token_ticker} for gas payment")
                    tx_hash = await self.perform_transaction_with_erc20_gas(
                        private_key, address, calldata, gas_token_address, use_proxy
                    )
                    if tx_hash:
                        gas_type = gas_token_ticker
                else:
                    tx_hash = await self.perform_transaction(private_key, address, calldata, use_proxy)
            else:
                tx_hash = await self.perform_transaction(private_key, address, calldata, use_proxy)

            if tx_hash:
                logger.success(f"{prefix} ✅ Bundle action successful: {tx_hash}")
                if gas_type != "TCENT":
                    logger.success(f"{prefix} 🎯 Gas paid with {gas_type} (UnifiedToken)")
                logger.info(f"{prefix} 🔗 Explorer: {self.EXPLORER}{tx_hash}")
                await self.transaction_badge(address, tx_hash, "MULTIPLE_ACTIONS", use_proxy)
                self.db.add_statistic(account_id, "bundle_action", "success", f"3 swaps bundled (gas: {gas_type})", tx_hash)
            else:
                logger.error(f"{prefix} ❌ Bundle action failed")
                self.db.add_statistic(account_id, "bundle_action", "failed")

            if i < count - 1:
                delay = get_random_delay(self.pause_between_swaps)
                logger.info(f"{prefix} ⏳ Waiting {delay}s before next bundle...")
                await asyncio.sleep(delay)

    async def process_account(self, private_key: str, address: str, action_type: int, use_proxy: bool, rotate_proxy: bool):
        """Process single account"""
        self.private_keys[address] = private_key
        prefix = self._log_prefix(address)

        init_delay = get_random_delay(self.init_pause)
        logger.debug(f"{prefix} ⏳ Initial pause: {init_delay}s")
        await asyncio.sleep(init_delay)

        account_data = self.db.get_account(private_key)
        if not account_data:
            account_id = self.db.add_account(private_key, address)
            account_data = self.db.get_account(private_key)
        else:
            account_id = account_data['id']

        user_agent = FakeUserAgent().random
        self.BASE_HEADERS[address] = {"Accept": "*/*", "Accept-Language": "en-US,en;q=0.9", "Connection": "keep-alive", "Host": "api.testnet.incentiv.io", "Origin": "https://testnet.incentiv.io", "Referer": "https://testnet.incentiv.io/", "User-Agent": user_agent}
        self.BUNDLER_HEADERS[address] = {**self.BASE_HEADERS[address], "Host": "bundler-testnet.incentiv.io"}

        logger.info(f"{prefix} 🔐 Logging in...")
        logged_in = await self.process_user_login(private_key, address, use_proxy, rotate_proxy)

        if not logged_in:
            logger.warning(f"{prefix} ⚠️ Initial login failed, trying one more time...")
            await asyncio.sleep(5)

            if use_proxy:
                new_proxy = self.rotate_proxy_for_account(address)
                logger.info(f"{prefix} 🔄 Using new proxy: {new_proxy}")

            logged_in = await self.process_user_login(private_key, address, use_proxy, rotate_proxy)

            if not logged_in:
                logger.error(f"{prefix} ❌ Login failed after all attempts, skipping account")
                return

        logger.success(f"{prefix} ✅ Successfully logged in")

        logger.info(f"{prefix} 📊 Fetching user data...")
        user = await self.user_data(address, use_proxy)
        if user:
            points = user.get("result", {}).get("xp", {}).get("points", 0)
            self.faucet_times[address] = user.get("result", {}).get("nextFaucetRequestTimestamp")
            logger.info(f"{prefix} 💎 Points: {points} XP")
        else:
            logger.warning(f"{prefix} ⚠️ Failed to fetch user data")
            points = 0

        logger.info(f"{prefix} 🔍 Checking contract deployment status...")
        try:
            check_timeout = 15 if use_proxy else 10
            is_deployed = await asyncio.wait_for(self.is_contract_deployed(address, use_proxy), timeout=check_timeout)
        except Exception as e:
            logger.debug(f"{prefix} Contract check failed: {str(e)}")
            is_deployed = False

        if not is_deployed:
            logger.warning(f"{prefix} ⚠️ Smart account contract not deployed!")
            logger.info(f"{prefix} 📋 Deploying contract via faucet claim...")
            deploy_success = await self.process_faucet_claim(private_key, address, account_id, use_proxy, is_first_claim=True)
            if not deploy_success:
                logger.error(f"{prefix} ❌ Deployment failed")
                logger.info(f"{prefix} 💡 Deploy manually at https://testnet.incentiv.io")
                logger.info(f"{prefix}    Connect wallet → Claim faucet once → Run bot again")
                return
            logger.info(f"{prefix} ⏳ Waiting {self.nonce_check_initial_wait}s for deployment confirmation...")
            await asyncio.sleep(self.nonce_check_initial_wait)

            is_deployed = False
            nonce = None
            for attempt in range(self.nonce_check_attempts_after):
                try:
                    timeout = self.nonce_check_timeout * 2 if use_proxy else self.nonce_check_timeout
                    is_deployed = await asyncio.wait_for(self.is_contract_deployed(address, use_proxy), timeout=timeout)
                    if is_deployed:
                        logger.success(f"{prefix} ✅ Contract deployed on-chain!")
                        nonce = await asyncio.wait_for(self.get_nonce(address, use_proxy), timeout=timeout)
                        if nonce is not None:
                            logger.success(f"{prefix} ✅ Deployment confirmed! Nonce: {nonce}")
                            break
                        else:
                            logger.debug(f"{prefix} Contract deployed but nonce not readable, using 1")
                            nonce = 1
                            break
                    else:
                        logger.debug(f"{prefix} Contract not yet deployed (attempt {attempt+1})")
                except Exception as e:
                    logger.debug(f"{prefix} Deployment check attempt {attempt+1} failed: {str(e)}")
                if attempt < self.nonce_check_attempts_after - 1:
                    delay = self.nonce_check_delay * (attempt + 1)
                    logger.debug(f"{prefix} ⏳ Waiting {delay}s before next check...")
                    await asyncio.sleep(delay)

            if not is_deployed or nonce is None:
                nonce = 1
                logger.warning(f"{prefix} ⚠️ Could not confirm deployment, starting with nonce 1")
            self.used_nonce[address] = nonce
            logger.success(f"{prefix} ✅ Ready to farm with nonce: {nonce}")
        else:
            logger.success(f"{prefix} ✅ Contract already deployed on-chain")
            try:
                check_timeout = 10 if use_proxy else 5
                nonce = await asyncio.wait_for(self.get_nonce(address, use_proxy), timeout=check_timeout)
                if nonce is not None:
                    logger.info(f"{prefix} ✅ Current nonce: {nonce}")
                else:
                    logger.debug(f"{prefix} Could not read nonce, starting with 1")
                    nonce = 1
            except Exception as e:
                logger.debug(f"{prefix} Nonce check failed: {str(e)}")
                nonce = 1
            self.used_nonce[address] = nonce

            balance = await self.get_token_balance(address, self.TCENT_CONTRACT_ADDRESS, use_proxy)
            logger.info(f"{prefix} 💰 TCENT Balance: {balance if balance else 0}")
            if balance is None or balance < 0.01:
                logger.warning(f"{prefix} ⚠️ Low TCENT balance, claiming faucet...")
                await self.process_faucet_claim(private_key, address, account_id, use_proxy, is_first_claim=False)

        add_contact_count = random.randint(self.add_contact_count_range[0], self.add_contact_count_range[1])
        transfer_count = random.randint(self.transfer_count_range[0], self.transfer_count_range[1])
        swap_count = random.randint(self.swap_count_range[0], self.swap_count_range[1])
        bundle_count = random.randint(self.bundle_count_range[0], self.bundle_count_range[1])

        if action_type == 2:
            logger.separator()
            logger.info(f"{prefix} 📊 Action plan: Add {add_contact_count} contacts")
            logger.separator()
        elif action_type == 3:
            logger.separator()
            logger.info(f"{prefix} 📊 Action plan: {transfer_count} transfers")
            logger.separator()
        elif action_type == 4:
            logger.separator()
            logger.info(f"{prefix} 📊 Action plan: {swap_count} swap pairs")
            logger.separator()
        elif action_type == 5:
            logger.separator()
            logger.info(f"{prefix} 📊 Action plan: {bundle_count} bundle actions")
            logger.separator()
        elif action_type == 6:
            logger.separator()
            logger.info(f"{prefix} 📊 Full action plan:")
            logger.info(f"{prefix}    • Contacts: {add_contact_count}")
            logger.info(f"{prefix}    • Transfers: {transfer_count}")
            logger.info(f"{prefix}    • Swaps: {swap_count}")
            logger.info(f"{prefix}    • Bundles: {bundle_count}")
            logger.separator()

        if action_type == 1:
            is_deployed = await self.is_contract_deployed(address, use_proxy)
            if not is_deployed:
                logger.info(f"{prefix} 🚀 Contract not deployed, deploying via faucet...")
                await self.process_faucet_claim(private_key, address, account_id, use_proxy, is_first_claim=True)
            else:
                logger.info(f"{prefix} ✅ Contract already deployed, claiming faucet...")
                await self.process_faucet_claim(private_key, address, account_id, use_proxy, is_first_claim=False)
        elif action_type == 2:
            await self.process_add_contacts(address, account_id, add_contact_count, use_proxy)
        elif action_type == 3:
            await self.process_transfers(private_key, address, account_id, transfer_count, use_proxy)
        elif action_type == 4:
            await self.process_swaps(private_key, address, account_id, swap_count, use_proxy)
        elif action_type == 5:
            await self.process_bundle_actions(private_key, address, account_id, bundle_count, use_proxy)
        elif action_type == 6:
            if nonce > 1:
                await self.process_faucet_claim(private_key, address, account_id, use_proxy, is_first_claim=False)
                delay = get_random_delay(self.pause_between_actions)
                logger.info(f"{prefix} ⏳ Waiting {delay}s before next action...")
                await asyncio.sleep(delay)

            await self.process_add_contacts(address, account_id, add_contact_count, use_proxy)
            delay = get_random_delay(self.pause_between_actions)
            logger.info(f"{prefix} ⏳ Waiting {delay}s before next action...")
            await asyncio.sleep(delay)

            await self.process_transfers(private_key, address, account_id, transfer_count, use_proxy)
            delay = get_random_delay(self.pause_between_actions)
            logger.info(f"{prefix} ⏳ Waiting {delay}s before next action...")
            await asyncio.sleep(delay)

            await self.process_swaps(private_key, address, account_id, swap_count, use_proxy)
            delay = get_random_delay(self.pause_between_actions)
            logger.info(f"{prefix} ⏳ Waiting {delay}s before next action...")
            await asyncio.sleep(delay)

            await self.process_bundle_actions(private_key, address, account_id, bundle_count, use_proxy)

    async def run(self, action_type: int, use_proxy: bool, rotate_proxy: bool, accounts_source: str = "accounts"):
        """Main run method"""
        from src.utils import load_accounts, load_register_accounts, load_farm_accounts, load_proxies, filter_accounts

        logger.separator()
        if accounts_source == "register":
            logger.info("📂 Loading accounts from register.txt...")
            accounts = load_register_accounts()
        elif accounts_source == "farm":
            logger.info("🚜 Loading accounts from farm.txt...")
            accounts = load_farm_accounts()
        else:
            logger.info("📂 Loading accounts from accounts.txt...")
            accounts = load_accounts()

        if not accounts:
            logger.error(f"❌ ERROR: No accounts found in {accounts_source}.txt!")
            logger.separator()
            return

        accounts = filter_accounts(accounts, self.settings)
        if not accounts:
            logger.error(f"❌ No accounts to process after filtering!")
            return

        logger.info(f"✅ Total accounts to process: {len(accounts)}")
        logger.info(f"🔄 Using {self.threads} thread(s)")

        if use_proxy:
            self.proxies = load_proxies()
            if not self.proxies:
                logger.warning("No proxies loaded")
                use_proxy = False
            else:
                logger.info(f"🔄 Loaded {len(self.proxies)} proxies")

        semaphore = asyncio.Semaphore(self.threads)

        async def process_account_with_semaphore(idx, account):
            async with semaphore:
                try:
                    private_key = account.get("private_key")
                    if not private_key:
                        mnemonic = account.get("mnemonic")
                        if mnemonic:
                            private_key = self.generate_pk_from_mnemonic(mnemonic)
                            self.account_types[private_key] = "mnemonic"
                        else:
                            logger.error(f"Account {idx}: Invalid account data")
                            return
                    else:
                        self.account_types[private_key] = "private_key"

                    address = self.generate_address(private_key)
                    if not address:
                        return

                    logger.separator()
                    logger.account(idx, len(accounts), address)
                    logger.separator()

                    await self.process_account(private_key, address, action_type, use_proxy, rotate_proxy)

                except Exception as e:
                    logger.error(f"Account {idx}: Error processing account: {str(e)}")
                    import traceback
                    traceback.print_exc()

        if self.threads == 1:
            for idx, account in enumerate(accounts, 1):
                await process_account_with_semaphore(idx, account)

                if idx < len(accounts):
                    delay = get_random_delay(self.pause_between_accounts)
                    logger.info(f"⏳ Waiting {delay}s before next account...")
                    logger.separator()
                    await asyncio.sleep(delay)
        else:
            logger.info(f"🚀 Starting parallel processing with {self.threads} threads...")
            logger.warning(f"⚠️  Note: Account delays don't apply in parallel mode")

            tasks = [process_account_with_semaphore(idx, account) for idx, account in enumerate(accounts, 1)]
            await asyncio.gather(*tasks)

        logger.separator()
        logger.success("All accounts processed!")