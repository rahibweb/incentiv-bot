from eth_utils import to_hex
from eth_account import Account
from eth_account.messages import encode_defunct
from aiohttp import ClientResponseError, ClientSession, ClientTimeout, BasicAuth, TCPConnector
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import *
from typing import Optional
from httpx import AsyncClient
import asyncio, random, json, re, os, pytz, yaml, ssl, certifi, sqlite3

almaty = pytz.timezone('Asia/Almaty')


# Простая Database для корневого register.py
class SimpleDatabase:
    def __init__(self, db_path="database.sqlite3"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS accounts (
                                                               id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                               private_key TEXT UNIQUE NOT NULL,
                                                               address TEXT NOT NULL,
                                                               smart_account TEXT,
                                                               username TEXT,
                                                               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
                       ''')
        conn.commit()
        conn.close()

    def is_registered(self, private_key: str) -> bool:
        """Проверка, зарегистрирован ли уже аккаунт"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM accounts WHERE private_key = ?', (private_key,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def save_account(self, private_key: str, address: str, smart_account: str, username: str):
        """Сохранение аккаунта в базу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                           INSERT INTO accounts (private_key, address, smart_account, username)
                           VALUES (?, ?, ?, ?)
                           ''', (private_key, address, smart_account, username))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Уже существует
        finally:
            conn.close()



def mask_proxy(proxy: str) -> str:
    """Mask proxy URL for logging"""
    if not proxy:
        return "No proxy"
    try:
        if "@" in proxy:
            protocol_auth, host_port = proxy.rsplit("@", 1)
            if "://" in protocol_auth:
                protocol, auth = protocol_auth.split("://", 1)
                if ":" in auth:
                    user, password = auth.split(":", 1)
                    masked_auth = f"{user[0]}***:{password[0]}***"
                else:
                    masked_auth = auth[:3] + "***"
            else:
                masked_auth = protocol_auth[:3] + "***"
            if ":" in host_port:
                ip, port = host_port.rsplit(":", 1)
                parts = ip.split(".")
                if len(parts) == 4:
                    masked_ip = f"{parts[0]}.{parts[1]}.***"
                else:
                    masked_ip = ip[:3] + "***"
                masked_host = f"{masked_ip}:{port}"
            else:
                masked_host = host_port[:3] + "***"
            return f"{protocol}://{masked_auth}@{masked_host}"
        else:
            if "://" in proxy:
                protocol, host_port = proxy.split("://", 1)
                if ":" in host_port:
                    ip, port = host_port.rsplit(":", 1)
                    parts = ip.split(".")
                    if len(parts) == 4:
                        masked_ip = f"{parts[0]}.{parts[1]}.***"
                    else:
                        masked_ip = ip[:3] + "***"
                    return f"{protocol}://{masked_ip}:{port}"
            return proxy[:10] + "***"
    except:
        return proxy[:10] + "***" if len(proxy) > 10 else "***"


def get_random_delay(delay_range):
    """Get random delay from range (как в bot.py)"""
    return random.randint(delay_range[0], delay_range[1])


class Solvium:
    def __init__(self, api_key: str, session: AsyncClient, proxy: Optional[str] = None):
        self.api_key = api_key
        self.proxy = proxy
        self.base_url = "https://captcha.solvium.io/api/v1"
        self.session = session

    def _format_proxy(self, proxy: str) -> str:
        if not proxy:
            return None
        if "@" in proxy:
            return proxy
        return f"http://{proxy}"

    async def create_turnstile_task(self, sitekey: str, pageurl: str) -> Optional[str]:
        """Creates a Turnstile captcha solving task"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/task/turnstile?url={pageurl}&sitekey={sitekey}&ref=starlabs"
        try:
            response = await self.session.get(url, headers=headers, timeout=30)
            result = response.json()
            if result.get("message") == "Task created" and "task_id" in result:
                return result["task_id"]
            print(f"Error creating Turnstile task with Solvium: {result}")
            return None
        except Exception as e:
            print(f"Error creating Turnstile task with Solvium: {e}")
            return None

    async def get_task_result(self, task_id: str) -> Optional[str]:
        """Gets the result of the captcha solution"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        max_attempts = 30
        for _ in range(max_attempts):
            try:
                response = await self.session.get(
                    f"{self.base_url}/task/status/{task_id}",
                    headers=headers,
                    timeout=30,
                )
                result = response.json()
                if result.get("status") == "completed" and result.get("result") and result["result"].get("solution"):
                    solution = result["result"]["solution"]
                    if re.match(r'^[a-zA-Z0-9\.\-_]+$', solution):
                        return solution
                    else:
                        print(f"Invalid solution format from Solvium: {solution}")
                        return None
                elif result.get("status") in ["running", "pending"]:
                    await asyncio.sleep(5)
                    continue
                else:
                    print(f"Error getting result with Solvium: {result}")
                    return None
            except Exception as e:
                print(f"Error getting result with Solvium: {e}")
                return None
        print("Max polling attempts reached without getting a result with Solvium")
        return None

    async def solve_captcha(self, sitekey: str, pageurl: str) -> Optional[str]:
        """Solves Cloudflare Turnstile captcha and returns token"""
        task_id = await self.create_turnstile_task(sitekey, pageurl)
        if not task_id:
            return None
        return await self.get_task_result(task_id)


class IncentivTestnet:
    def __init__(self) -> None:
        self.BASE_API = "https://api.testnet.incentiv.io"
        self.RPC_URL = "https://rpc1.testnet.incentiv.io/"
        self.BUNDLER_URL = "https://bundler.rpc1.testnet.incentiv.io/"
        self.EXPLORER = "https://explorer-testnet.incentiv.io/op/"
        self.PAGE_URL = "https://testnet.incentiv.io"
        self.SITE_KEY = "0x4AAAAAABl4Ht6hzgSZ-Na3"
        self.REF_CODE = "mUyNWvs8rzF6ssue38uepw"
        self.CAPTCHA_KEY = None
        self.CAPTCHA_PROVIDER = "2captcha"
        self.BASE_HEADERS = {}
        self.BUNDLER_HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.success = 0
        self.settings = {}

        # База данных для проверки дубликатов
        self.db = SimpleDatabase()

        # Настройки задержек (как в bot.py) - будут загружены из settings.yaml
        self.pause_between_accounts = [5, 20]  # По умолчанию
        self.pause_between_attempts = [5, 8]
        self.init_pause = [5, 10]

        # SSL context for Windows (как в bot.py)
        try:
            self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            self.ssl_context = ssl.create_default_context()

    def load_settings(self, filename="settings.yaml"):
        """Загрузка настроек из YAML файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.settings = config or {}

            # Загрузка настроек капчи
            captcha_config = self.settings.get('CAPTCHA', {})
            self.CAPTCHA_PROVIDER = captcha_config.get('PROVIDER', '2captcha').lower()

            if self.CAPTCHA_PROVIDER == 'solvium':
                self.CAPTCHA_KEY = captcha_config.get('SOLVIUM_KEY', '')
            elif self.CAPTCHA_PROVIDER == '2captcha':
                self.CAPTCHA_KEY = captcha_config.get('CAPTCHA_2CAPTCHA_KEY', '')

            # Загрузка настроек задержек (как в bot.py)
            bot_settings = self.settings.get('SETTINGS', {})
            self.pause_between_accounts = bot_settings.get('RANDOM_PAUSE_BETWEEN_ACCOUNTS', [5, 20])
            self.pause_between_attempts = bot_settings.get('PAUSE_BETWEEN_ATTEMPTS', [5, 8])
            self.init_pause = bot_settings.get('RANDOM_INITIALIZATION_PAUSE', [5, 10])

            if self.CAPTCHA_KEY:
                self.log(
                    f"{Fore.GREEN + Style.BRIGHT}Captcha Provider: {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{self.CAPTCHA_PROVIDER.upper()}{Style.RESET_ALL}"
                )
            else:
                self.log(
                    f"{Fore.YELLOW + Style.BRIGHT}Warning: No Captcha Key Found in settings.yaml{Style.RESET_ALL}"
                )
            return True
        except FileNotFoundError:
            self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
            return False
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Settings: {e}{Style.RESET_ALL}")
            return False

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(almaty).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(
            f"""
        {Fore.GREEN + Style.BRIGHT}Incentiv Testnet{Fore.BLUE + Style.BRIGHT} Auto BOT
            """
            f"""
        {Fore.GREEN + Style.BRIGHT}Rey? {Fore.YELLOW + Style.BRIGHT}<INI WATERMARK>
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    def save_private_key(self, private_key, filename="results/new_accounts/success.txt"):
        """Сохранение приватного ключа в results/new_accounts/success.txt"""
        # Создаём директорию если её нет
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            lines = []
        if private_key not in lines:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(private_key + "\n")

    def save_failed_key(self, private_key, filename="results/new_accounts/failed.txt"):
        """Сохранение failed приватного ключа"""
        # Создаём директорию если её нет
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            lines = []
        if private_key not in lines:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(private_key + "\n")

    def load_ref_code(self):
        try:
            with open("data/ref_codes.txt", 'r') as file:
                ref_code = file.read().strip()
            return ref_code
        except Exception as e:
            return None

    async def load_proxies(self):
        filename = "data/proxies.txt"
        try:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                return
            with open(filename, 'r') as f:
                self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return
            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Loaded {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
                f"{Fore.GREEN + Style.BRIGHT} proxies{Style.RESET_ALL}"
            )
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, account):
        if account not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def rotate_proxy_for_account(self, account):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[account] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy

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

    def generate_wallets(self):
        try:
            private_key = os.urandom(32).hex()
            account = Account.from_key(private_key)
            address = account.address
            return private_key, address
        except Exception as e:
            return None, None

    def generate_username(self):
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

    def generate_payload(self, private_key: str, message: str, username: str, turnstile_token: str):
        try:
            encoded_message = encode_defunct(text=message)
            signed_message = Account.sign_message(encoded_message, private_key=private_key)
            signature = to_hex(signed_message.signature)
            payload = {
                "type":"BROWSER_EXTENSION",
                "challenge": message,
                "signature": signature,
                "username": username,
                "verificationToken": turnstile_token,
                "refCode": self.REF_CODE
            }
            return payload
        except Exception as e:
            raise Exception(f"Generate Req Payload Failed: {str(e)}")

    def print_question(self):
        while True:
            try:
                ref_count = int(input(f"{Fore.YELLOW + Style.BRIGHT}Enter Referral Count -> {Style.RESET_ALL}").strip())
                if ref_count > 0:
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Count must be greater than 0.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number.{Style.RESET_ALL}")

        while True:
            try:
                print(f"{Fore.WHITE + Style.BRIGHT}1. Run With Proxy{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}2. Run Without Proxy{Style.RESET_ALL}")
                proxy_choice = int(input(f"{Fore.BLUE + Style.BRIGHT}Choose [1/2] -> {Style.RESET_ALL}").strip())
                if proxy_choice in [1, 2]:
                    proxy_type = "With" if proxy_choice == 1 else "Without"
                    print(f"{Fore.GREEN + Style.BRIGHT}Run {proxy_type} Proxy Selected.{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Please enter either 1 or 2.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number (1 or 2).{Style.RESET_ALL}")

        rotate_proxy = False
        if proxy_choice == 1:
            while True:
                rotate_proxy = input(f"{Fore.BLUE + Style.BRIGHT}Rotate Invalid Proxy? [y/n] -> {Style.RESET_ALL}").strip()
                if rotate_proxy in ["y", "n"]:
                    rotate_proxy = rotate_proxy == "y"
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter 'y' or 'n'.{Style.RESET_ALL}")

        # Добавляем выбор потоков
        while True:
            try:
                threads = int(input(f"{Fore.YELLOW + Style.BRIGHT}Enter number of threads (1-10) -> {Style.RESET_ALL}").strip())
                if 1 <= threads <= 10:
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Threads must be between 1 and 10.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number.{Style.RESET_ALL}")

        return ref_count, proxy_choice, rotate_proxy, threads

    async def solve_cf_turnstile_2captcha(self, retries=5):
        """Решение капчи через 2Captcha"""
        for attempt in range(retries):
            try:
                connector = TCPConnector(ssl=self.ssl_context)
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    if self.CAPTCHA_KEY is None:
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Message{Style.RESET_ALL}"
                            f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                            f"{Fore.RED+Style.BRIGHT} Turnstile Not Solved{Style.RESET_ALL}"
                            f"{Fore.MAGENTA+Style.BRIGHT} - {Style.RESET_ALL}"
                            f"{Fore.YELLOW+Style.BRIGHT}2Captcha Key Is None{Style.RESET_ALL}"
                        )
                        return None

                    url = f"http://2captcha.com/in.php?key={self.CAPTCHA_KEY}&method=turnstile&sitekey={self.SITE_KEY}&pageurl={self.PAGE_URL}"
                    async with session.get(url=url) as response:
                        response.raise_for_status()
                        result = await response.text()

                        if 'OK|' not in result:
                            self.log(
                                f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                                f"{Fore.CYAN+Style.BRIGHT}Message{Style.RESET_ALL}"
                                f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                                f"{Fore.YELLOW + Style.BRIGHT} {result} {Style.RESET_ALL}"
                            )
                            await asyncio.sleep(5)
                            continue

                        request_id = result.split('|')[1]
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Req Id{Style.RESET_ALL}"
                            f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT} {request_id} {Style.RESET_ALL}"
                        )

                        for _ in range(30):
                            res_url = f"http://2captcha.com/res.php?key={self.CAPTCHA_KEY}&action=get&id={request_id}"
                            async with session.get(url=res_url) as res_response:
                                res_response.raise_for_status()
                                res_result = await res_response.text()

                                if 'OK|' in res_result:
                                    turnstile_token = res_result.split('|')[1]
                                    self.log(
                                        f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                                        f"{Fore.CYAN+Style.BRIGHT}Message{Style.RESET_ALL}"
                                        f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                                        f"{Fore.GREEN+Style.BRIGHT} Turnstile Solved Successfully {Style.RESET_ALL}"
                                    )
                                    return turnstile_token

                                elif res_result == "CAPCHA_NOT_READY":
                                    self.log(
                                        f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                                        f"{Fore.CYAN+Style.BRIGHT}Message{Style.RESET_ALL}"
                                        f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                                        f"{Fore.YELLOW + Style.BRIGHT} Captcha Not Ready {Style.RESET_ALL}"
                                    )
                                    await asyncio.sleep(5)
                                    continue
                                else:
                                    break

            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT}Message{Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Turnstile Not Solved{Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT} - {Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT}{str(e)}{Style.RESET_ALL}"
                )
        return None

    async def solve_cf_turnstile_solvium(self, retries=5):
        """Решение капчи через Solvium"""
        for attempt in range(retries):
            try:
                if self.CAPTCHA_KEY is None:
                    self.log(
                        f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}Message{Style.RESET_ALL}"
                        f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                        f"{Fore.RED+Style.BRIGHT} Turnstile Not Solved{Style.RESET_ALL}"
                        f"{Fore.MAGENTA+Style.BRIGHT} - {Style.RESET_ALL}"
                        f"{Fore.YELLOW+Style.BRIGHT}Solvium Key Is None{Style.RESET_ALL}"
                    )
                    return None

                async with AsyncClient(timeout=60) as client:
                    solvium = Solvium(api_key=self.CAPTCHA_KEY, session=client)

                    self.log(
                        f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}Message{Style.RESET_ALL}"
                        f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                        f"{Fore.YELLOW + Style.BRIGHT} Solving Captcha with Solvium... {Style.RESET_ALL}"
                    )

                    turnstile_token = await solvium.solve_captcha(
                        sitekey=self.SITE_KEY,
                        pageurl=self.PAGE_URL
                    )

                    if turnstile_token:
                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                            f"{Fore.CYAN+Style.BRIGHT}Message{Style.RESET_ALL}"
                            f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                            f"{Fore.GREEN+Style.BRIGHT} Turnstile Solved Successfully {Style.RESET_ALL}"
                        )
                        return turnstile_token
                    else:
                        if attempt < retries - 1:
                            await asyncio.sleep(5)
                            continue
                        return None

            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT}[ {Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT}Message{Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT} ]{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Turnstile Not Solved{Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT} - {Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT}{str(e)}{Style.RESET_ALL}"
                )
        return None

    async def solve_cf_turnstile(self, retries=5):
        """Универсальный метод для решения капчи"""
        if self.CAPTCHA_PROVIDER == "solvium":
            return await self.solve_cf_turnstile_solvium(retries)
        elif self.CAPTCHA_PROVIDER == "2captcha":
            return await self.solve_cf_turnstile_2captcha(retries)
        else:
            self.log(f"{Fore.RED + Style.BRIGHT}Unknown captcha provider: {self.CAPTCHA_PROVIDER}{Style.RESET_ALL}")
            return None

    async def check_connection(self, proxy_url=None):
        connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=10)) as session:
                async with session.get(url="https://api.ipify.org?format=json", proxy=proxy, proxy_auth=proxy_auth) as response:
                    response.raise_for_status()
                    return True
        except (Exception, ClientResponseError) as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Connection Not 200 OK {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None

    async def user_challange(self, address: str, use_proxy: bool, retries=5):
        url = f"{self.BASE_API}/api/user/challenge?type=BROWSER_EXTENSION&address={address}"
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
                    delay = get_random_delay(self.pause_between_attempts)
                    await asyncio.sleep(delay)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Fetch Challenge Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        return None

    async def user_signup(self, private_key: str, address: str, message: str, username: str, turnstile_token: str, use_proxy: bool, retries=5):
        url = f"{self.BASE_API}/api/user/signup"
        data = json.dumps(self.generate_payload(private_key, message, username, turnstile_token))
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
                        # Получаем ответ API независимо от статуса
                        response_text = await response.text()

                        try:
                            response_json = json.loads(response_text)
                        except:
                            response_json = {"raw": response_text}

                        # Проверяем на ошибки в ответе API
                        if response.status != 200:
                            # Логируем полный ответ для анализа
                            self.log(
                                f"{Fore.YELLOW+Style.BRIGHT}API Response ({response.status}):{Style.RESET_ALL}"
                                f"{Fore.WHITE+Style.BRIGHT} {response_text[:200]}{Style.RESET_ALL}"
                            )

                            # Проверяем специфичные ошибки
                            error_msg = str(response_json.get("error", response_json.get("message", "")))
                            if "already" in error_msg.lower() or "duplicate" in error_msg.lower() or "exists" in error_msg.lower():
                                self.log(
                                    f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                                    f"{Fore.YELLOW+Style.BRIGHT} Account Already Registered (API) {Style.RESET_ALL}"
                                )
                                # Возвращаем специальный маркер
                                return {"already_registered": True, "error": error_msg}

                            response.raise_for_status()

                        return response_json

            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    delay = get_random_delay(self.pause_between_attempts)
                    await asyncio.sleep(delay)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Signup Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        return None

    async def process_check_connection(self, address: str, use_proxy: bool, rotate_proxy: bool):
        while True:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None
            # Маскируем прокси в логах
            if proxy:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Proxy   :{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {mask_proxy(proxy)} {Style.RESET_ALL}"
                )

            is_valid = await self.check_connection(proxy)
            if not is_valid:
                if rotate_proxy:
                    proxy = self.rotate_proxy_for_account(address)
                    await asyncio.sleep(1)
                    continue
                return False
            return True

    async def process_accounts(self, private_key: str, address: str, use_proxy: bool, rotate_proxy: bool):
        # ===== ПРОВЕРКА НА ДУБЛИКАТЫ =====
        if self.db.is_registered(private_key):
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Already Registered - Skipping {Style.RESET_ALL}"
            )
            return True  # Уже зарегистрирован, считаем успехом

        # 🎯 ИНДИВИДУАЛЬНАЯ задержка для каждого аккаунта (важно для threads > 1)
        init_delay = get_random_delay(self.init_pause)
        self.log(
            f"{Fore.CYAN+Style.BRIGHT}Initial :{Style.RESET_ALL}"
            f"{Fore.YELLOW+Style.BRIGHT} Waiting {init_delay}s...{Style.RESET_ALL}"
        )
        await asyncio.sleep(init_delay)

        is_valid = await self.process_check_connection(address, use_proxy, rotate_proxy)
        if is_valid:
            challange = await self.user_challange(address, use_proxy)
            if not challange:
                return False

            message = challange.get("result", {}).get("challenge")
            self.log(f"{Fore.CYAN+Style.BRIGHT}Captcha :{Style.RESET_ALL}")

            turnstile_token = await self.solve_cf_turnstile()
            if not turnstile_token:
                return False

            username = self.generate_username()
            signup = await self.user_signup(private_key, address, message, username, turnstile_token, use_proxy)
            if not signup:
                return False

            # Проверяем, не вернул ли API сообщение о дубликате
            if signup.get("already_registered"):
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} Already Registered (Backend Check) {Style.RESET_ALL}"
                )
                # Уже зарегистрирован по данным API - пропускаем
                return True

            smart_account = signup.get("result", {}).get("address")
            if not smart_account:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Signup Failed - No Smart Account in Response {Style.RESET_ALL}"
                )
                return False

            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                f"{Fore.GREEN+Style.BRIGHT} Signup Success {Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Username:{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {username} {Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Address :{Style.RESET_ALL}"
                f"{Fore.BLUE+Style.BRIGHT} {smart_account} {Style.RESET_ALL}"
            )

            # Сохраняем в файл и в базу данных
            self.save_private_key(private_key)
            self.db.save_account(private_key, address, smart_account, username)
            self.success += 1
            return True
        else:
            return False

    async def main(self):
        try:
            # Загружаем настройки из YAML
            self.load_settings()

            ref_code = self.load_ref_code()
            if ref_code:
                self.REF_CODE = ref_code

            ref_count, proxy_choice, rotate_proxy, threads = self.print_question()

            self.clear_terminal()
            self.welcome()
            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Account's Total: {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{ref_count}{Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Referral Code  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{self.REF_CODE}{Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Threads        : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{threads}{Style.RESET_ALL}"
            )

            use_proxy = True if proxy_choice == 1 else False
            if use_proxy:
                await self.load_proxies()

            separator = "=" * 25

            # Обработка с потоками
            tasks = []
            task_keys = []  # Связь между задачами и ключами

            for idx in range(ref_count):
                private_key, address = self.generate_wallets()

                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}{separator}[{Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT} {idx+1} {Style.RESET_ALL}"
                    f"{Fore.CYAN + Style.BRIGHT}Of{Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT} {ref_count} {Style.RESET_ALL}"
                    f"{Fore.CYAN + Style.BRIGHT}]{separator}{Style.RESET_ALL}"
                )

                if not private_key or not address:
                    self.log(
                        f"{Fore.CYAN + Style.BRIGHT}Status  :{Style.RESET_ALL}"
                        f"{Fore.RED + Style.BRIGHT} Library Version Not Supported {Style.RESET_ALL}"
                    )
                    # Сохраняем как failed если не удалось создать кошелёк
                    if private_key:
                        self.save_failed_key(private_key)
                    continue

                user_agent = FakeUserAgent().random

                self.BASE_HEADERS[address] = {
                    "Accept": "*/*",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Connection": "keep-alive",
                    "Host": "api.testnet.incentiv.io",
                    "Origin": "https://testnet.incentiv.io",
                    "Referer": "https://testnet.incentiv.io/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "User-Agent": user_agent
                }

                self.BUNDLER_HEADERS[address] = {
                    "Accept": "*/*",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Connection": "keep-alive",
                    "Host": "bundler.rpc1.testnet.incentiv.io",
                    "Origin": "https://testnet.incentiv.io",
                    "Referer": "https://testnet.incentiv.io/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "User-Agent": user_agent
                }

                # Создаем задачу
                task = self.process_accounts(private_key, address, use_proxy, rotate_proxy)
                tasks.append(task)
                task_keys.append(private_key)

                # Когда накопилось нужное количество потоков или последняя итерация
                if len(tasks) >= threads or idx == ref_count - 1:
                    # Запускаем параллельно
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Обрабатываем результаты
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            # Ошибка выполнения - сохраняем как failed
                            self.save_failed_key(task_keys[i])
                        elif result is False or result is None:
                            # Регистрация не удалась - сохраняем как failed
                            self.save_failed_key(task_keys[i])
                        # Успешные уже сохранены в process_accounts

                    tasks = []
                    task_keys = []
                    # Пауза между батчами (как в bot.py)
                    if idx < ref_count - 1:
                        delay = get_random_delay(self.pause_between_accounts)
                        self.log(
                            f"{Fore.CYAN + Style.BRIGHT}Waiting:{Style.RESET_ALL}"
                            f"{Fore.YELLOW + Style.BRIGHT} {delay}s before next group...{Style.RESET_ALL}"
                        )
                        await asyncio.sleep(delay)

            self.log(f"{Fore.CYAN + Style.BRIGHT}={Style.RESET_ALL}"*72)
            self.log(
                f"{Fore.CYAN + Style.BRIGHT}Success:{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {self.success} {Style.RESET_ALL}"
                f"{Fore.MAGENTA + Style.BRIGHT}Of{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {ref_count} {Style.RESET_ALL}"
            )

        except Exception as e:
            self.log(f"{Fore.RED+Style.BRIGHT}Error: {e}{Style.RESET_ALL}")
            raise e

if __name__ == "__main__":
    try:
        bot = IncentivTestnet()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(almaty).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] Incentiv Testnet - BOT{Style.RESET_ALL}                                       "
        )