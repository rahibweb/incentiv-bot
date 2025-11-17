import os

def create_directories():
    directories = [
        'data',
        'logs',
        'src'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}/")


def create_data_files():
    files = {
        'data/farm.txt': '# Add your accounts here (one per line)\n# Format: private_key or {"private_key": "0x..."} or {"mnemonic": "word1 word2..."}\n',
        'data/proxies.txt': '# Add your proxies here (one per line)\n# Format: http://user:pass@ip:port or socks5://user:pass@ip:port\n',
        'data/register.txt': '# Add existing wallet private keys here for registration\n# Format: 0xprivatekey (one per line)\n',
        'data/ref_codes.txt': '# Add your referral code here (single line)\n'
    }

    for filepath, content in files.items():
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Created file: {filepath}")
        else:
            print(f"○ File already exists: {filepath}")


def check_settings():
    if not os.path.exists('settings.yaml'):
        print("\n⚠ WARNING: settings.yaml not found!")
        print("Please create settings.yaml file with your configuration.")
        print("See README.md for configuration details.")
        return False
    else:
        print("✓ settings.yaml found")
        return True


def main():
    print("=" * 60)
    print("Incentiv Testnet Bot - Setup Script")
    print("=" * 60)
    print()

    print("Setting up project structure...")
    print()

    create_directories()
    print()

    create_data_files()
    print()

    check_settings()
    print()

    print("=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Configure settings.yaml with your API keys")
    print("3. Add your accounts to data/farm.txt")
    print("4. (Optional) Add proxies to data/proxies.txt")
    print("5. Run the bot: python main.py")
    print()


if __name__ == "__main__":
    main()