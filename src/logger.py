import os
import sys
from datetime import datetime
from colorama import Fore, Style, init
import pytz

init(autoreset=True)

ALMATY = pytz.timezone('Asia/Almaty')


class Logger:
    def __init__(self, log_to_file: bool = True, log_dir: str = "logs"):
        self.log_to_file = log_to_file
        self.log_dir = log_dir

        if log_to_file:
            os.makedirs(log_dir, exist_ok=True)
            self.log_file = os.path.join(
                log_dir,
                f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )

    def _get_timestamp(self) -> str:
        return datetime.now().astimezone(ALMATY).strftime('%Y-%m-%d %X %Z')

    def _write_to_file(self, message: str):
        if self.log_to_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                clean_message = message
                for code in [Fore.CYAN, Fore.GREEN, Fore.RED, Fore.YELLOW,
                             Fore.BLUE, Fore.MAGENTA, Fore.WHITE, Style.BRIGHT, Style.RESET_ALL]:
                    clean_message = clean_message.replace(code, '')
                f.write(f"{self._get_timestamp()} | {clean_message}\n")

    def info(self, message: str):
        log_msg = (
            f"{Fore.CYAN + Style.BRIGHT}[INFO]{Style.RESET_ALL} "
            f"{Fore.WHITE}{message}{Style.RESET_ALL}"
        )
        print(log_msg, flush=True)
        self._write_to_file(f"[INFO] {message}")

    def success(self, message: str):
        log_msg = (
            f"{Fore.GREEN + Style.BRIGHT}[SUCCESS]{Style.RESET_ALL} "
            f"{Fore.WHITE}{message}{Style.RESET_ALL}"
        )
        print(log_msg, flush=True)
        self._write_to_file(f"[SUCCESS] {message}")

    def error(self, message: str):
        log_msg = (
            f"{Fore.RED + Style.BRIGHT}[ERROR]{Style.RESET_ALL} "
            f"{Fore.WHITE}{message}{Style.RESET_ALL}"
        )
        print(log_msg, flush=True)
        self._write_to_file(f"[ERROR] {message}")

    def warning(self, message: str):
        log_msg = (
            f"{Fore.YELLOW + Style.BRIGHT}[WARNING]{Style.RESET_ALL} "
            f"{Fore.WHITE}{message}{Style.RESET_ALL}"
        )
        print(log_msg, flush=True)
        self._write_to_file(f"[WARNING] {message}")

    def debug(self, message: str):
        log_msg = (
            f"{Fore.MAGENTA + Style.BRIGHT}[DEBUG]{Style.RESET_ALL} "
            f"{Fore.WHITE}{message}{Style.RESET_ALL}"
        )
        print(log_msg, flush=True)
        self._write_to_file(f"[DEBUG] {message}")

    def action(self, action_name: str, details: str = ""):
        log_msg = (
            f"{Fore.BLUE + Style.BRIGHT}[{action_name}]{Style.RESET_ALL} "
            f"{Fore.WHITE}{details}{Style.RESET_ALL}"
        )
        print(log_msg, flush=True)
        self._write_to_file(f"[{action_name}] {details}")

    def account(self, account_num: int, total: int, address: str):
        separator = "=" * 25
        log_msg = (
            f"\n{Fore.CYAN + Style.BRIGHT}{separator}[ "
            f"{Fore.WHITE + Style.BRIGHT}Account {account_num}/{total}{Fore.CYAN + Style.BRIGHT} "
            f"]{separator}{Style.RESET_ALL}\n"
            f"{Fore.CYAN + Style.BRIGHT}Address:{Style.RESET_ALL} "
            f"{Fore.BLUE + Style.BRIGHT}{address[:8]}...{address[-6:]}{Style.RESET_ALL}"
        )
        print(log_msg, flush=True)
        self._write_to_file(f"\n{'='*70}\nAccount {account_num}/{total} | Address: {address}")

    def separator(self):
        sep = "=" * 70
        print(f"{Fore.CYAN + Style.BRIGHT}{sep}{Style.RESET_ALL}")
        self._write_to_file(sep)

    @staticmethod
    def clear_terminal():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def print_banner():
        banner = f"""
{Fore.BLUE + Style.BRIGHT}╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   {Fore.CYAN + Style.BRIGHT}██████╗  █████╗ ██╗  ██╗██╗██████╗ ██╗    ██╗███████╗██████╗{Fore.BLUE}    ║
║   {Fore.CYAN + Style.BRIGHT}██╔══██╗██╔══██╗██║  ██║██║██╔══██╗██║    ██║██╔════╝██╔══██╗{Fore.BLUE}   ║
║   {Fore.CYAN + Style.BRIGHT}██████╔╝███████║███████║██║██████╔╝██║ █╗ ██║█████╗  ██████╔╝{Fore.BLUE}   ║
║   {Fore.CYAN + Style.BRIGHT}██╔══██╗██╔══██║██╔══██║██║██╔══██╗██║███╗██║██╔══╝  ██╔══██╗{Fore.BLUE}   ║
║   {Fore.CYAN + Style.BRIGHT}██║  ██║██║  ██║██║  ██║██║██████╔╝╚███╔███╔╝███████╗██████╔╝{Fore.BLUE}   ║
║   {Fore.CYAN + Style.BRIGHT}╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═════╝  ╚══╝╚══╝ ╚══════╝╚═════╝{Fore.BLUE}    ║
║                                                                   ║
║              {Fore.WHITE + Style.BRIGHT}INCENTIV TESTNET BOT v1.1{Fore.BLUE}                            ║
║                                                                   ║
║              {Fore.WHITE}Developed by {Fore.CYAN + Style.BRIGHT}RAHIBWEB{Fore.BLUE}                                ║
║              {Fore.CYAN}https://github.com/rahibweb{Fore.BLUE}                          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)

logger = Logger()