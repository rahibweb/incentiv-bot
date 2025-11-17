import asyncio
import random
import secrets
import ssl
import certifi
import hashlib
from typing import Optional, Dict, Any, List
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_hex
from aiohttp import ClientSession, ClientTimeout, ClientResponseError, BasicAuth, TCPConnector
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent

from database import Database
from src.logger import logger
from src.captcha import CaptchaSolver
from src.utils import get_random_delay, check_proxy_scheme, mask_proxy

class Register:

    def __init__(self, db: Database, settings: Dict[str, Any]):
        self.db = db
        self.settings = settings

        self.BASE_API = "https://api.testnet.incentiv.io"
        self.PAGE_URL = "https://testnet.incentiv.io"
        self.SITE_KEY = "0x4AAAAAABl4Ht6hzgSZ-Na3"

        try:
            self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            self.ssl_context = ssl.create_default_context()

        captcha_config = settings.get('CAPTCHA', {})
        provider = captcha_config.get('PROVIDER', '2captcha').lower()
        if provider == 'solvium':
            api_key = captcha_config.get('SOLVIUM_KEY', '')
        else:
            api_key = captcha_config.get('CAPTCHA_2CAPTCHA_KEY', '')
        self.captcha_solver = CaptchaSolver(provider=provider, api_key=api_key)

        self.BASE_HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}

        bot_settings = settings.get('SETTINGS', {})
        self.pause_between_attempts = bot_settings.get('PAUSE_BETWEEN_ATTEMPTS', [1, 3])
        self.pause_between_accounts = bot_settings.get('RANDOM_PAUSE_BETWEEN_ACCOUNTS', [1, 5])
        self.init_pause = bot_settings.get('RANDOM_INITIALIZATION_PAUSE', [1, 3])
        self.threads = bot_settings.get('THREADS', 1)

    def generate_fingerprint(self, address: str) -> str:
        random_data = f"{address}{secrets.token_hex(16)}"
        return hashlib.sha256(random_data.encode()).hexdigest()[:32]

    def build_proxy_config(self, proxy=None):
        if not proxy:
            return None, None, None

        if proxy.startswith("socks"):
            connector = ProxyConnector.from_url(proxy, ssl=self.ssl_context)
            return connector, None, None

        elif proxy.startswith("http"):
            import re
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

    def generate_username(self) -> str:
        vowels = "aiueo"
        consonants = "bcdfghjklmnpqrstvwxyz"
        length = random.randint(8, 12)
        username = []
        use_vowel = random.choice([True, False])

        for _ in range(length):
            if use_vowel:
                username.append(random.choice(vowels))
            else:
                username.append(random.choice(consonants))
            use_vowel = not use_vowel

        return "".join(username)

    def generate_payload(self, private_key: str, message: str, username: str, turnstile_token: str, ref_code: str) -> Dict[str, Any]:
        try:
            encoded_message = encode_defunct(text=message)
            signed_message = Account.sign_message(encoded_message, private_key=private_key)
            signature = to_hex(signed_message.signature)

            return {
                "type": "BROWSER_EXTENSION",
                "challenge": message,
                "signature": signature,
                "username": username,
                "verificationToken": turnstile_token,
                "refCode": ref_code
            }
        except Exception as e:
            raise Exception(f"Generate Payload Failed: {str(e)}")

    async def check_connection(self, proxy_url=None) -> bool:
        connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=10)) as session:
                async with session.get(url="https://api.ipify.org?format=json", proxy=proxy, proxy_auth=proxy_auth) as response:
                    response.raise_for_status()
                    return True
        except Exception:
            return False

    async def user_challenge(self, address: str, use_proxy: bool, retries=5) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_API}/api/user/challenge?type=BROWSER_EXTENSION&address={address}"

        for attempt in range(retries):
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)

            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.get(url=url, headers=self.BASE_HEADERS[address], proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except Exception as e:
                if attempt < retries - 1:
                    delay = get_random_delay(self.pause_between_attempts)
                    logger.debug(f"Challenge attempt {attempt + 1} failed, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"Fetch challenge failed: {str(e)}")
                return None

        return None

    async def user_signup(self, private_key: str, address: str, message: str, username: str,
                          turnstile_token: str, ref_code: str, use_proxy: bool, retries=5) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_API}/api/user/signup"
        import json
        data = json.dumps(self.generate_payload(private_key, message, username, turnstile_token, ref_code))
        headers = {
            **self.BASE_HEADERS[address],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }

        for attempt in range(retries):
            proxy_url = self.get_next_proxy_for_account(address) if use_proxy else None
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)

            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        if response.status == 400 or response.status == 409:
                            error_data = await response.json()
                            error_msg = error_data.get('error', {}).get('message', '') or error_data.get('message', '')

                            already_registered_messages = [
                                'already registered',
                                'already exists',
                                'user already exists',
                                'address already registered',
                                'account already exists',
                                'duplicate'
                            ]

                            if any(msg in error_msg.lower() for msg in already_registered_messages):
                                logger.warning(f"⚠️ Account already registered (API): {error_msg}")
                                return {"already_registered": True, "error": error_msg}

                        response.raise_for_status()
                        return await response.json()

            except ClientResponseError as e:
                if e.status in [400, 409]:
                    try:
                        error_data = await e.response.json() if hasattr(e, 'response') else {}
                        error_msg = error_data.get('error', {}).get('message', '') or error_data.get('message', '') or str(e)

                        already_registered_messages = [
                            'already registered',
                            'already exists',
                            'user already exists',
                            'address already registered',
                            'account already exists',
                            'duplicate'
                        ]

                        if any(msg in error_msg.lower() for msg in already_registered_messages):
                            logger.warning(f"⚠️ Account already registered (API): {error_msg}")
                            return {"already_registered": True, "error": error_msg}
                    except:
                        pass

                if attempt < retries - 1:
                    delay = get_random_delay(self.pause_between_attempts)
                    logger.debug(f"Signup attempt {attempt + 1} failed, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"Signup failed: {str(e)}")
                return None

            except Exception as e:
                if attempt < retries - 1:
                    delay = get_random_delay(self.pause_between_attempts)
                    logger.debug(f"Signup attempt {attempt + 1} failed, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"Signup failed: {str(e)}")
                return None

        return None

    async def process_single_registration(self, private_key: str, address: str, ref_code: str, use_proxy: bool, rotate_proxy: bool) -> tuple[bool, str]:
        try:
            existing_account = self.db.get_account(private_key)
            if existing_account:
                smart_account = existing_account.get('smart_account')
                username = existing_account.get('username')

                if smart_account:
                    logger.warning(f"⚠️ Account {address[:10]}... already in database")
                    logger.info(f"Smart Account: {smart_account}")
                    if username:
                        logger.info(f"Username: {username}")
                    logger.warning("⚠️ Skipping registration - saved to failed.txt")
                    return (False, 'already_registered')

            init_delay = get_random_delay(self.init_pause)
            logger.debug(f"⏳ Initial pause: {init_delay}s")
            await asyncio.sleep(init_delay)

            if use_proxy:
                proxy = self.get_next_proxy_for_account(address)
                if proxy:
                    logger.debug(f"Using proxy: {mask_proxy(proxy)}")

                is_valid = await self.check_connection(proxy)
                if not is_valid:
                    if rotate_proxy:
                        logger.warning("Connection failed, rotating proxy...")
                        proxy = self.rotate_proxy_for_account(address)
                        is_valid = await self.check_connection(proxy)
                    if not is_valid:
                        logger.error("Connection check failed")
                        return (False, 'failed')

            logger.info("Getting challenge...")
            challenge = await self.user_challenge(address, use_proxy)
            if not challenge:
                logger.error("Failed to get challenge")
                return (False, 'failed')

            message = challenge.get("result", {}).get("challenge")
            if not message:
                logger.error("No challenge message")
                return (False, 'failed')

            logger.info("Solving captcha...")
            turnstile_token = await self.captcha_solver.solve_turnstile(self.SITE_KEY, self.PAGE_URL)
            if not turnstile_token:
                logger.error("Failed to solve captcha")
                return (False, 'failed')

            username = self.generate_username()

            logger.info("Registering account...")
            signup = await self.user_signup(private_key, address, message, username, turnstile_token, ref_code, use_proxy)
            if not signup:
                logger.error("Registration failed")
                return (False, 'failed')

            if signup.get("already_registered"):
                logger.warning(f"⚠️ Account {address[:10]}... already registered (API)")
                logger.warning("⚠️ Saved to failed.txt")
                return (False, 'already_registered')

            result = signup.get("result", {})
            smart_account = result.get("address")

            if smart_account:
                logger.success(f"✓ Registered: {username}")
                logger.info(f"Smart Account: {smart_account}")

                fingerprint = self.generate_fingerprint(address)
                proxy = self.get_next_proxy_for_account(address) if use_proxy else None

                try:
                    account_id = self.db.add_account(private_key, address, fingerprint)
                    self.db.update_account(
                        private_key,
                        smart_account=smart_account,
                        username=username,
                        proxy=proxy
                    )
                    self.db.add_statistic(
                        account_id=account_id,
                        action_type="registration",
                        status="success",
                        details=f"Username: {username}, Smart Account: {smart_account}"
                    )
                    logger.debug("✓ Saved to database")
                except Exception as db_error:
                    logger.warning(f"Database save error: {str(db_error)}")

                return (True, 'success')
            else:
                logger.error(f"Registration response missing smart account: {signup}")
                return (False, 'failed')

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            import traceback
            traceback.print_exc()
            return (False, 'failed')

    async def register_new_accounts(self, count: int, ref_code: str, use_proxy: bool, rotate_proxy: bool):
        try:
            if use_proxy:
                from src.utils import load_proxies
                self.proxies = load_proxies()
                if not self.proxies:
                    logger.error("No proxies loaded")
                    use_proxy = False
                else:
                    logger.info(f"Loaded {len(self.proxies)} proxies")

            logger.info(f"Registering {count} new accounts...")
            logger.info(f"🔄 Using {self.threads} thread(s)")
            if ref_code:
                logger.info(f"Referral code: {ref_code}")
            logger.separator()

            success_count = 0
            already_registered_count = 0
            failed_count = 0

            success_accounts = []
            failed_accounts = []

            semaphore = asyncio.Semaphore(self.threads)

            async def process_account_with_semaphore(idx):
                async with semaphore:
                    try:
                        private_key_bytes = secrets.token_bytes(32)
                        private_key = to_hex(private_key_bytes)
                        account = Account.from_key(private_key)
                        address = account.address

                        logger.separator()
                        logger.account(idx, count, address)
                        logger.separator()

                        user_agent = FakeUserAgent().random
                        self.BASE_HEADERS[address] = {
                            "Accept": "*/*",
                            "Accept-Language": "en-US,en;q=0.9",
                            "Connection": "keep-alive",
                            "Host": "api.testnet.incentiv.io",
                            "Origin": "https://testnet.incentiv.io",
                            "Referer": "https://testnet.incentiv.io/",
                            "Sec-Fetch-Dest": "empty",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "same-site",
                            "User-Agent": user_agent
                        }

                        success, status = await self.process_single_registration(private_key, address, ref_code, use_proxy, rotate_proxy)
                        return (success, status, private_key)
                    except Exception as e:
                        logger.error(f"Error processing account {idx}: {str(e)}")
                        return (False, 'failed', None)

            tasks = []
            processed = 0
            total_batches = (count + self.threads - 1) // self.threads

            for idx in range(1, count + 1):
                tasks.append(process_account_with_semaphore(idx))

                if len(tasks) >= self.threads or idx == count:
                    processed += len(tasks)
                    batch_num = (processed + self.threads - 1) // self.threads
                    logger.info(f"🚀 Processing {len(tasks)} accounts (group {batch_num}/{total_batches})...")

                    results = await asyncio.gather(*tasks)

                    for success, status, pk in results:
                        if success and status == 'success' and pk:
                            success_count += 1
                            success_accounts.append(pk)
                        else:
                            if status == 'already_registered':
                                already_registered_count += 1
                            else:
                                failed_count += 1
                            if pk:
                                failed_accounts.append(pk)

                    tasks = []

                    if idx < count:
                        delay = get_random_delay(self.pause_between_accounts)
                        logger.info(f"✓ Group {batch_num} complete. Waiting {delay}s...")
                        logger.separator()
                        await asyncio.sleep(delay)

            import os
            results_dir = "results/register_new_accounts"
            os.makedirs(results_dir, exist_ok=True)

            if success_accounts:
                with open(os.path.join(results_dir, "success.txt"), 'w') as f:
                    f.write('\n'.join(success_accounts))
                logger.success(f"✓ Saved {len(success_accounts)} to success.txt")

            if failed_accounts:
                with open(os.path.join(results_dir, "failed.txt"), 'w') as f:
                    f.write('\n'.join(failed_accounts))
                logger.info(f"Saved {len(failed_accounts)} to failed.txt")

            logger.separator()
            logger.success(f"Registration complete:")
            logger.success(f"  ✓ Successfully registered: {success_count}/{count}")
            if already_registered_count > 0:
                logger.warning(f"  ⚠️ Already registered (skipped): {already_registered_count}/{count}")
            if failed_count > 0:
                logger.error(f"  ✗ Failed: {failed_count}/{count}")

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            import traceback
            traceback.print_exc()

    async def register_existing_wallets(self, wallets: List[str], ref_code: str, use_proxy: bool, rotate_proxy: bool):
        """Register existing wallets"""
        try:
            if use_proxy:
                from src.utils import load_proxies
                self.proxies = load_proxies()
                if not self.proxies:
                    logger.error("No proxies loaded")
                    use_proxy = False
                else:
                    logger.info(f"Loaded {len(self.proxies)} proxies")

            logger.info(f"Registering {len(wallets)} existing wallets...")
            logger.info(f"🔄 Using {self.threads} thread(s)")
            if ref_code:
                logger.info(f"Referral code: {ref_code}")
            logger.separator()

            success_count = 0
            already_registered_count = 0
            failed_count = 0

            success_accounts = []
            failed_accounts = []

            semaphore = asyncio.Semaphore(self.threads)

            async def process_account_with_semaphore(idx, private_key):
                async with semaphore:
                    try:
                        if not private_key.startswith('0x'):
                            private_key = '0x' + private_key

                        account = Account.from_key(private_key)
                        address = account.address

                        logger.separator()
                        logger.account(idx, len(wallets), address)
                        logger.separator()

                        user_agent = FakeUserAgent().random
                        self.BASE_HEADERS[address] = {
                            "Accept": "*/*",
                            "Accept-Language": "en-US,en;q=0.9",
                            "Connection": "keep-alive",
                            "Host": "api.testnet.incentiv.io",
                            "Origin": "https://testnet.incentiv.io",
                            "Referer": "https://testnet.incentiv.io/",
                            "Sec-Fetch-Dest": "empty",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "same-site",
                            "User-Agent": user_agent
                        }

                        success, status = await self.process_single_registration(private_key, address, ref_code, use_proxy, rotate_proxy)
                        return (success, status, private_key)
                    except Exception as e:
                        logger.error(f"Error processing wallet {idx}: {str(e)}")
                        return (False, 'failed', private_key if 'private_key' in locals() else None)

            tasks = []
            processed = 0
            total_groups = (len(wallets) + self.threads - 1) // self.threads

            for idx, private_key in enumerate(wallets, 1):
                tasks.append(process_account_with_semaphore(idx, private_key))

                if len(tasks) >= self.threads or idx == len(wallets):
                    processed += len(tasks)
                    group_num = (processed + self.threads - 1) // self.threads
                    logger.info(f"🚀 Processing {len(tasks)} wallets (group {group_num}/{total_groups})...")

                    results = await asyncio.gather(*tasks)

                    for success, status, pk in results:
                        if success and status == 'success' and pk:
                            success_count += 1
                            success_accounts.append(pk)
                        else:
                            if status == 'already_registered':
                                already_registered_count += 1
                            else:
                                failed_count += 1
                            if pk:
                                failed_accounts.append(pk)

                    tasks = []

                    if idx < len(wallets):
                        delay = get_random_delay(self.pause_between_accounts)
                        logger.info(f"✓ Group {group_num} complete. Waiting {delay}s...")
                        logger.separator()
                        await asyncio.sleep(delay)

            import os
            results_dir = "results/register_existing_wallets"
            os.makedirs(results_dir, exist_ok=True)

            if success_accounts:
                with open(os.path.join(results_dir, "success.txt"), 'w') as f:
                    f.write('\n'.join(success_accounts))
                logger.success(f"✓ Saved {len(success_accounts)} to success.txt")

            if failed_accounts:
                with open(os.path.join(results_dir, "failed.txt"), 'w') as f:
                    f.write('\n'.join(failed_accounts))
                logger.info(f"Saved {len(failed_accounts)} to failed.txt")

            logger.separator()
            logger.success(f"Registration complete:")
            logger.success(f"  ✓ Successfully registered: {success_count}/{len(wallets)}")
            if already_registered_count > 0:
                logger.warning(f"  ⚠️ Already registered (skipped): {already_registered_count}/{len(wallets)}")
            if failed_count > 0:
                logger.error(f"  ✗ Failed: {failed_count}/{len(wallets)}")

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            import traceback
            traceback.print_exc()