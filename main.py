import asyncio
import sys
from colorama import Fore, Style, init
from src.logger import logger
from database import Database
from src.utils import (
    load_settings, load_accounts, load_wallets,
    load_proxies, load_ref_code, create_data_directory,
    validate_settings
)

init(autoreset=True)


class CLI:

    def __init__(self):
        self.db = Database()
        self.settings = None

        create_data_directory()

        try:
            self.settings = load_settings()
            validate_settings(self.settings)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            sys.exit(1)

    def print_menu(self):

        logger.clear_terminal()
        logger.print_banner()

        menu = f"""
    {Fore.CYAN + Style.BRIGHT}╔══════════════════════════════════════════════╗
    ║              MAIN MENU                       ║
    ╠══════════════════════════════════════════════╣
    ║                                              ║
    ║  {Fore.GREEN}1.{Fore.CYAN} Run Bot (Farm Tasks)                     {Fore.CYAN}║
    ║  {Fore.GREEN}2.{Fore.CYAN} Register New Accounts                    {Fore.CYAN}║
    ║  {Fore.GREEN}3.{Fore.CYAN} Register Existing Wallets                {Fore.CYAN}║
    ║  {Fore.GREEN}4.{Fore.CYAN} View Statistics                          {Fore.CYAN}║
    ║  {Fore.GREEN}5.{Fore.CYAN} Export Statistics                        {Fore.CYAN}║
    ║  {Fore.GREEN}6.{Fore.CYAN} Remove All Proxies                       {Fore.CYAN}║
    ║  {Fore.GREEN}7.{Fore.CYAN} Database Info                            {Fore.CYAN}║
    ║  {Fore.GREEN}8.{Fore.CYAN} Settings                                 {Fore.CYAN}║
    ║  {Fore.GREEN}0.{Fore.CYAN} Exit                                     {Fore.CYAN}║
    ║                                              ║
    ╚══════════════════════════════════════════════╝{Style.RESET_ALL}
        """
        print(menu)

    def print_bot_menu(self):

        menu = f"""
    {Fore.CYAN + Style.BRIGHT}╔══════════════════════════════════════════════╗
    ║           BOT ACTION MENU                    ║
    ╠══════════════════════════════════════════════╣
    ║                                              ║
    ║  {Fore.GREEN}1.{Fore.CYAN} Claim Testnet Tokens                     {Fore.CYAN}║
    ║  {Fore.GREEN}2.{Fore.CYAN} Random Add Contact                       {Fore.CYAN}║
    ║  {Fore.GREEN}3.{Fore.CYAN} Random Transfer                          {Fore.CYAN}║
    ║  {Fore.GREEN}4.{Fore.CYAN} Random Swap                              {Fore.CYAN}║
    ║  {Fore.GREEN}5.{Fore.CYAN} Bundle Action                            {Fore.CYAN}║
    ║  {Fore.GREEN}6.{Fore.CYAN} Run All Features                         {Fore.CYAN}║
    ║  {Fore.GREEN}0.{Fore.CYAN} Back to Main Menu                        {Fore.CYAN}║
    ║                                              ║
    ╚══════════════════════════════════════════════╝{Style.RESET_ALL}
        """
        print(menu)

    def get_input(self, prompt: str) -> str:
        return input(f"{Fore.YELLOW + Style.BRIGHT}{prompt}{Style.RESET_ALL}").strip()

    def get_yes_no(self, prompt: str) -> bool:
        while True:
            response = self.get_input(f"{prompt} (y/n): ").lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                logger.error("Invalid input. Please enter 'y' or 'n'")

    def get_number(self, prompt: str, min_val: int = 0) -> int:
        while True:
            try:
                value = int(self.get_input(prompt))
                if value >= min_val:
                    return value
                else:
                    logger.error(f"Value must be >= {min_val}")
            except ValueError:
                logger.error("Invalid input. Please enter a number")

    async def run_bot(self):
        self.print_bot_menu()
        choice = self.get_input("Select option: ")

        if choice == '0':
            return

        try:
            from src.bot import IncentivBot

            use_proxy = self.get_yes_no("Use proxies?")
            rotate_proxy = False

            if use_proxy:
                rotate_proxy = self.get_yes_no("Rotate invalid proxies?")

            bot = IncentivBot(self.db, self.settings)
            await bot.run(int(choice), use_proxy, rotate_proxy, accounts_source="farm")

        except Exception as e:
            logger.error(f"Error running bot: {e}")
            import traceback
            traceback.print_exc()

        self.get_input("\nPress Enter to continue...")

    async def register_new_accounts(self):
        logger.clear_terminal()
        logger.print_banner()

        logger.info("Register New Accounts")
        logger.separator()

        ref_code = load_ref_code()
        if ref_code:
            logger.info(f"Loaded referral code: {ref_code}")
        else:
            logger.warning("No referral code found in data/ref_codes.txt")
            ref_code = self.get_input("Enter referral code (or press Enter to skip): ")

        count = self.get_number("How many accounts to register: ", min_val=1)
        use_proxy = self.get_yes_no("Use proxies?")
        rotate_proxy = False

        if use_proxy:
            rotate_proxy = self.get_yes_no("Rotate invalid proxies?")

        try:
            from src.register import Register

            register = Register(self.db, self.settings)
            await register.register_new_accounts(count, ref_code, use_proxy, rotate_proxy)

        except Exception as e:
            logger.error(f"Error during registration: {e}")
            import traceback
            traceback.print_exc()

        self.get_input("\nPress Enter to continue...")

    async def register_existing_wallets(self):
        logger.clear_terminal()
        logger.print_banner()

        logger.info("Register Existing Wallets")
        logger.separator()

        wallets = load_wallets()
        if not wallets:
            logger.error("No wallets found in data/wallets.txt")
            self.get_input("\nPress Enter to continue...")
            return

        logger.info(f"Found {len(wallets)} wallets")

        ref_code = load_ref_code()
        if ref_code:
            logger.info(f"Loaded referral code: {ref_code}")
        else:
            logger.warning("No referral code found in data/ref_codes.txt")
            ref_code = self.get_input("Enter referral code (or press Enter to skip): ")

        use_proxy = self.get_yes_no("Use proxies?")
        rotate_proxy = False

        if use_proxy:
            rotate_proxy = self.get_yes_no("Rotate invalid proxies?")

        try:
            from src.register import Register

            register = Register(self.db, self.settings)
            await register.register_existing_wallets(wallets, ref_code, use_proxy, rotate_proxy)

        except Exception as e:
            logger.error(f"Error during registration: {e}")
            import traceback
            traceback.print_exc()

        self.get_input("\nPress Enter to continue...")

    def view_statistics(self):
        logger.clear_terminal()
        logger.print_banner()

        logger.info("Statistics")
        logger.separator()

        stats = self.db.get_success_rate()
        logger.info(f"Total Actions: {stats['total']}")
        logger.success(f"Successful: {stats['success']}")
        logger.error(f"Failed: {stats['failed']}")
        logger.info(f"Success Rate: {stats['success_rate']:.2f}%")

        logger.separator()

        recent = self.db.get_statistics()[:10]
        if recent:
            logger.info("Recent Actions (Last 10):")
            for action in recent:
                status_color = Fore.GREEN if action[2] == 'success' else Fore.RED
                print(f"  {status_color}{action[1]}: {action[2]}{Style.RESET_ALL} - {action[5]}")

        self.get_input("\nPress Enter to continue...")

    def export_statistics(self):
        logger.clear_terminal()
        logger.print_banner()

        filename = self.get_input("Enter filename (default: statistics_export.json): ")
        if not filename:
            filename = "statistics_export.json"

        try:
            count = self.db.export_statistics(filename)
            logger.success(f"Exported {count} records to {filename}")
        except Exception as e:
            logger.error(f"Failed to export statistics: {e}")

        self.get_input("\nPress Enter to continue...")

    def remove_all_proxies(self):
        logger.clear_terminal()
        logger.print_banner()

        confirm = self.get_yes_no("Are you sure you want to remove all proxies from all accounts?")

        if confirm:
            try:
                count = self.db.remove_all_proxies()
                logger.success(f"Removed proxies from {count} accounts")
            except Exception as e:
                logger.error(f"Failed to remove proxies: {e}")
        else:
            logger.info("Operation cancelled")

        self.get_input("\nPress Enter to continue...")

    def database_info(self):
        logger.clear_terminal()
        logger.print_banner()

        logger.info("Database Information")
        logger.separator()

        count = self.db.get_account_count()
        logger.info(f"Total Accounts: {count}")

        stats = self.db.get_success_rate()
        logger.info(f"Total Actions: {stats['total']}")

        self.get_input("\nPress Enter to continue...")

    def show_settings(self):
        logger.clear_terminal()
        logger.print_banner()

        logger.info("Current Settings")
        logger.separator()

        settings = self.settings.get('SETTINGS', {})
        logger.info(f"Threads: {settings.get('THREADS', 1)}")
        logger.info(f"Attempts: {settings.get('ATTEMPTS', 3)}")
        logger.info(f"Shuffle Wallets: {settings.get('SHUFFLE_WALLETS', False)}")

        captcha = self.settings.get('CAPTCHA', {})
        logger.info(f"Captcha Provider: {captcha.get('PROVIDER', 'N/A')}")

        self.get_input("\nPress Enter to continue...")

    async def main_loop(self):
        while True:
            self.print_menu()
            choice = self.get_input("Select option: ")

            if choice == '1':
                await self.run_bot()
            elif choice == '2':
                await self.register_new_accounts()
            elif choice == '3':
                await self.register_existing_wallets()
            elif choice == '4':
                self.view_statistics()
            elif choice == '5':
                self.export_statistics()
            elif choice == '6':
                self.remove_all_proxies()
            elif choice == '7':
                self.database_info()
            elif choice == '8':
                self.show_settings()
            elif choice == '0':
                logger.info("Goodbye!")
                break
            else:
                logger.error("Invalid option. Please try again.")
                self.get_input("\nPress Enter to continue...")


def main():
    try:
        cli = CLI()
        asyncio.run(cli.main_loop())
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Exiting...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()