import os
import random
import yaml
from typing import List, Dict, Any, Optional


def mask_proxy(proxy: str) -> str:
    if not proxy:
        return "No proxy"

    try:
        if "@" in proxy:
            protocol_auth, host_port = proxy.rsplit("@", 1)

            if "://" in protocol_auth:
                protocol, auth = protocol_auth.split("://", 1)
                if ":" in auth:
                    user, password = auth.split(":", 1)
                    masked_user = user[0] + "***" if len(user) > 0 else "***"
                    masked_pass = password[0] + "***" if len(password) > 0 else "***"
                    masked_auth = f"{masked_user}:{masked_pass}"
                else:
                    masked_auth = auth[0] + "***"
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
                else:
                    return f"{protocol}://{host_port[:3]}***"
            else:
                return proxy[:10] + "***"
    except Exception:
        return proxy[:10] + "***" if len(proxy) > 10 else "***"


def load_settings(filename: str = "settings.yaml") -> Dict[str, Any]:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        try:
            import toml
            if os.path.exists("config.toml"):
                return toml.load("config.toml")
        except ImportError:
            pass
        raise Exception(f"Settings file '{filename}' not found")
    except yaml.YAMLError as e:
        raise Exception(f"Error parsing settings file: {e}")


def load_accounts(filename: str = "data/farm.txt") -> List[Dict[str, str]]:
    accounts = []

    if not os.path.exists(filename):
        raise FileNotFoundError(f"File '{filename}' not found")

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith('{'):
                import json
                accounts.append(json.loads(line))
            elif line.startswith('0x'):
                accounts.append({"private_key": line})
            else:
                accounts.append({"mnemonic": line})

    return accounts


def load_register_accounts() -> List[Dict[str, str]]:
    try:
        return load_accounts("data/register.txt")
    except FileNotFoundError:
        return []


def load_farm_accounts() -> List[Dict[str, str]]:
    try:
        return load_accounts("data/farm.txt")
    except FileNotFoundError:
        return []


def load_wallets(filename: str = "data/wallets.txt") -> List[str]:
    if not os.path.exists(filename):
        return []

    wallets = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                wallets.append(line)

    return wallets


def load_proxies(filename: str = "data/proxies.txt") -> List[str]:
    if not os.path.exists(filename):
        return []

    proxies = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                proxies.append(line)

    return proxies


def load_ref_code(filename: str = "data/ref_codes.txt") -> Optional[str]:
    if not os.path.exists(filename):
        return None

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                return line
    return None


def save_private_key(private_key: str, filename: str = "ref_wallets.txt"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        lines = []

    if private_key not in lines:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(private_key + "\n")


def filter_accounts(accounts: List[Any], settings: Dict[str, Any]) -> List[Any]:
    settings_section = settings.get('SETTINGS', {})

    accounts_range = settings_section.get('ACCOUNTS_RANGE', [0, 0])
    exact_accounts = settings_section.get('EXACT_ACCOUNTS_TO_USE', [])
    shuffle = settings_section.get('SHUFFLE_WALLETS', False)

    account_filter = settings.get('ACCOUNT_FILTER', {})
    if account_filter:
        start = account_filter.get('START_ACCOUNT')
        end = account_filter.get('END_ACCOUNT')
        if start is not None or end is not None:
            start = start - 1 if start else 0
            end = end if end else len(accounts)
            return accounts[start:end]

    if exact_accounts:
        filtered = [accounts[i-1] for i in exact_accounts if 0 < i <= len(accounts)]

    elif accounts_range != [0, 0]:
        start, end = accounts_range
        filtered = accounts[start-1:end] if start > 0 else accounts
    else:
        filtered = accounts

    if shuffle:
        random.shuffle(filtered)

    return filtered


def get_random_delay(delay_range: List[int]) -> int:
    return random.randint(delay_range[0], delay_range[1])


def format_address(address: str) -> str:
    return f"{address[:6]}...{address[-4:]}"


def check_proxy_scheme(proxy: str) -> str:
    schemes = ["http://", "https://", "socks4://", "socks5://"]
    if any(proxy.startswith(scheme) for scheme in schemes):
        return proxy
    return f"http://{proxy}"


def create_data_directory():
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    files = [
        "data/proxies.txt",
        "data/ref_codes.txt",
        "data/wallets.txt",
        "data/register.txt",
        "data/farm.txt"
    ]

    for file in files:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                if 'register.txt' in file:
                    f.write("# Register.txt - New accounts for registration\n")
                    f.write("# Add private keys or mnemonics, one per line\n\n")
                elif 'farm.txt' in file:
                    f.write("# Farm.txt - Accounts for farming (already registered)\n")
                    f.write("# Add private keys or mnemonics, one per line\n\n")


def validate_settings(settings: Dict[str, Any]) -> bool:
    required_sections = ['SETTINGS', 'CAPTCHA', 'TRANSFER', 'SWAP', 'BUNDLE']

    for section in required_sections:
        if section not in settings:
            raise Exception(f"Missing required section '{section}' in settings.yaml")

    return True