# Incentiv Testnet Bot 🚀

<div align="center">

[![Telegram Channel](https://img.shields.io/badge/Telegram-Channel-blue?style=for-the-badge&logo=telegram)](https://t.me/hashycash)
[![Telegram Chat](https://img.shields.io/badge/Telegram-Chat-blue?style=for-the-badge&logo=telegram)](https://t.me/hasycashtalks)
[![GitHub](https://img.shields.io/badge/GitHub-rahibweb-black?style=for-the-badge&logo=github)](https://github.com/rahibweb)

</div>

**Version 1.1** | Powerful automation suite for Incentiv Testnet with registration, farming, and multi-token operations.

---

## ✨ About Me

Hi, I'm **RAHIBWEB** - a blockchain developer and automation specialist focused on building efficient tools for Web3 ecosystems.

I create open-source bots and utilities to help the crypto community participate in testnets, airdrops, and blockchain projects more effectively. My tools emphasize reliability, security, and ease of use.

**What I do:**
- 🔧 Develop automation tools for blockchain testnets
- 🤖 Build multi-account management solutions
- 📊 Create analytics and monitoring systems
- 🛡️ Focus on security and best practices

**Why I share:**
- 💡 Believe in open-source and community collaboration
- 🌐 Want to make Web3 accessible to everyone
- 📚 Enjoy teaching and helping others learn
- 🚀 Passionate about decentralized technologies

Follow my channels for updates, new tools, and Web3 insights!

---
## 💰 Donate

<div align="center">

### 💚 Support Development

Your support makes me excited to code + farm airdrops every day 🎁

| 💎 Blockchain | 📌 Address |
|--------------|-----------|
| **💎 EVM** | `0x67f349976d15afa315548914476542576b4F711F` |
| **🔷 TON** | `UQC_JVSuizxwnLczTgkEPAVxsfJXBj1ndMYluX609Q-e0lUo` |
| **🟣 Solana** | `8ufRUkRAzreJZGr3t47zfgEcZgVEUFwsAwvWdy69Kons` |

**Every donation helps me create more tools and keep them free!** 🙏

</div>

---


## ✨ Key Features

### 🎯 Account Management
- **Smart Registration System** - Create unlimited new accounts or register existing wallets
- **Automatic Deployment Detection** - Identifies deployed smart contracts
- **Database Tracking** - SQLite storage for accounts, tokens, and statistics
- **Referral System** - Automated referral code application

### 🤖 Intelligent Automation
- **Multi-threaded Processing** - Concurrent account operations
- **Proxy Rotation** - HTTP/SOCKS5 with automatic failover
- **Captcha Solving** - Solvium and 2Captcha integration
- **Smart Retry Logic** - Exponential backoff with configurable attempts
- **Random Delays** - Human-like behavior patterns

### 💰 Token Operations
- **Multi-Token Support** - TCENT, SMPL, BULL, FLIP tokens
- **Random Transfers** - Automated token distribution
- **Smart Swaps** - Native ↔ ERC20 token exchanges
- **Bundle Actions** - Multiple swaps in single transaction
- **UnifiedToken Gas** - Pay fees with ERC20 tokens

### 📊 Advanced Features
- **Customizable Ranges** - Configure min/max amounts for all operations
- **Account Filtering** - Range selection and exact account targeting
- **Statistics Export** - JSON export for analytics
- **Live Logging** - Real-time operation tracking with timezone support
- **Contact Management** - Random contact addition

---

## 🛠️ Requirements

### 💎 Recommended: NodeMaven Proxies

<div align="center">

![NodeMaven](assets/nodemaven.png)

<h3>Premium Residential Proxies for Professional Automation</h3>

<p>
<a href="https://go.nodemaven.com/RAHIBWEB">
<img src="https://img.shields.io/badge/Get_NodeMaven-Proxies-0066cc?style=for-the-badge&logo=proxy&logoColor=white" alt="Get NodeMaven Proxies"/>
</a>
</p>

</div>

<table align="center">
<tr>
<td align="center" width="33%">

### 🎁 Exclusive Promo Codes

<table>
<tr>
<td><b>Code</b></td>
<td><b>Benefit</b></td>
</tr>
<tr>
<td><code>RAHIB</code></td>
<td>+12 GB Bonus Traffic</td>
</tr>
<tr>
<td><code>RAHIB50</code></td>
<td>50% OFF Any Plan</td>
</tr>
<tr>
<td><code>RAHIB100</code></td>
<td>Double Traffic (100GB→200GB)</td>
</tr>
</table>

</td>
<td align="center" width="33%">

### ⚡ Key Features

<table>
<tr>
<td>🚀</td>
<td><b>High-Speed Residential</b></td>
</tr>
<tr>
<td>🔓</td>
<td><b>No KYC Required</b></td>
</tr>
<tr>
<td>💯</td>
<td><b>Genuine Bonuses</b></td>
</tr>
<tr>
<td>🎯</td>
<td><b>Multi-Account Ready</b></td>
</tr>
<tr>
<td>🛡️</td>
<td><b>Low Ban Rate</b></td>
</tr>
</table>

</td>
<td align="center" width="33%">

### 📊 Why Choose NodeMaven?

✓ **Tested & Verified**<br/>
Real performance, not promises

✓ **Automation Optimized**<br/>
Built for botting & farming

✓ **Instant Activation**<br/>
Start using immediately

✓ **24/7 Uptime**<br/>
Reliable infrastructure

✓ **Community Trusted**<br/>
Recommended by top farmers

</td>
</tr>
</table>

---

## 📥 Installation

**1. Clone the repository:**
```bash
git clone https://github.com/rahibweb/incentiv-testnet-bot.git
cd incentiv-testnet-bot
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Run setup:**
```bash
python setup.py
```

---

## ⚙️ Configuration

### 1. Edit Settings

Open `settings.yaml` and configure:

- **Threads & Delays** - Concurrent processing and timing
- **Captcha Provider** - Solvium or 2Captcha API key
- **Action Counts** - How many operations per account
- **Transfer/Swap Amounts** - Min-Max ranges for transactions

### 2. Add Your Data

**Accounts** (`data/farm.txt`):
```
0xYourPrivateKey
```

**Proxies** (`data/proxies.txt`):
```
http://user:pass@ip:port
socks5://user:pass@ip:port
```

**Referral** (`data/ref_codes.txt`):
```
YOUR_REF_CODE
```

> 💡 **See `settings.yaml` for full configuration options and detailed comments**

---


# Option 2: Import existing wallets
# Add keys to data/wallets.txt
python main.py
> Select: 3 (Register Existing Wallets)
```

### ⚠️ CRITICAL: Post-Registration Steps

**After registration, follow these steps exactly:**

**1. Claim Testnet Tokens (via Bot)**
- Menu: `Run Bot → Claim Testnet Tokens`
- Bot automatically requests tokens for all accounts
- Wait for tokens to arrive

**2. Deploy Smart Account (MANUAL - REQUIRED)**
- Visit https://testnet.incentiv.io
- Make **ONE manual transaction** from each account
- Can be a simple transfer or swap
- This deploys the smart contract on-chain
- **⚠️ Bot will NOT work without deployment!**

**3. Start Automation**
- After manual deployment, run the bot normally
- Bot detects deployed accounts automatically
- Full automation now available

**Why manual deployment?**
- Smart accounts need on-chain initialization
- Ensures proper contract setup
- Prevents automation errors

---

## 💡 Advanced Features

### UnifiedToken Gas (ERC20 Gas Payment)

Pay transaction fees with ERC20 tokens instead of native TCENT:

```yaml
UNIFIED_TOKEN_GAS:
  ENABLED: true
  MIN_TOKEN_BALANCE: 0.01
  TRANSFER_AMOUNT: [0.001, 0.005]
  GAS_TOKENS: ["SMPL", "BULL", "FLIP"]
  RANDOMIZE_TOKEN: true
```

**How it works:**
1. Bot selects random ERC20 token (SMPL/BULL/FLIP)
2. Checks sufficient token balance
3. Executes TCENT transfer
4. Pays gas fee in selected ERC20 token
5. Auto-fallback to TCENT if insufficient balance

### Bundle Actions

Execute multiple swaps in a single transaction:
- Saves on gas fees
- Faster execution
- Higher point rewards
- Configurable swap count

### Smart Swap Cycles

Automated round-trip swaps:
```
TCENT → Random ERC20 → TCENT
```
- Increases trading volume
- Earns more points
- Randomized token selection
- Configurable cycle count

---

## 📊 Operations Guide

### Token Transfer

**Random recipient generation:**
- Generates new addresses on-demand
- Supports all token types
- Configurable amount ranges
- Automatic balance checks

### Token Swaps

**Supported pairs:**
- TCENT ↔ SMPL
- TCENT ↔ BULL
- TCENT ↔ FLIP

**Features:**
- Random token selection
- Automatic approval handling
- Slippage protection
- Gas optimization

### Contact Management

**Random contact addition:**
- Generates random addresses
- Automatic contact verification
- Configurable contact count
- Natural behavior simulation

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| **Captcha fails** | Check API key and balance |
| **Proxy errors** | Enable `rotate_proxy` option |
| **Nonce errors** | Adjust `NONCE_CHECK_*` settings |
| **Rate limiting** | Increase pause delays |
| **Deployment issues** | Complete manual transaction first |

### Common Issues

**"Smart account not deployed"**
```bash
Solution: Make 1 manual transaction at testnet.incentiv.io
```

**"Insufficient balance"**
```bash
Solution: Claim testnet tokens first via bot menu
```

**"Captcha timeout"**
```bash
Solution: Check captcha API key and service status
```

---

## 🎯 Best Practices

1. **Start Small** - Test with 1-2 accounts first
2. **Use Proxies** - Avoid IP bans and rate limits
3. **Random Delays** - Configure natural pause ranges
4. **Monitor Logs** - Check for errors and issues
5. **Backup Data** - Export statistics regularly
6. **Update Settings** - Adjust based on performance
7. **Manual Deploy** - Always deploy smart accounts manually first

---

## 📈 Statistics & Analytics

**View Statistics:**
- Total actions performed
- Success/failure rates
- Recent operation history
- Per-account performance

**Export to JSON:**
```bash
Menu → Export Statistics
# Generates: statistics_export.json
```

**Database Management:**
- SQLite storage
- Automatic backups
- Query capabilities
- Data integrity checks

---

## 🔐 Security & Privacy

- **Private Keys** - Never shared or logged
- **Proxy Support** - Hide your real IP
- **SSL Verification** - Secure connections
- **Error Handling** - No sensitive data in logs
- **Database Encryption** - SQLite with secure storage

---

## 🆘 Support & Community

**Need Help?**
- 📢 **Telegram Channel:** [@hashycash](https://t.me/hashycash)
- 💬 **Telegram Chat:** [@hasycashtalks](https://t.me/hasycashtalks)
- 🐛 **GitHub Issues:** [Report Bugs](https://github.com/rahibweb/incentiv-testnet-bot/issues)

**Stay Updated:**
- Latest features and improvements
- Tips and best practices
- Community support
- Exclusive guides

---

## 📜 License

This software is provided as-is for educational purposes only.

**Disclaimer:** Use at your own risk. Always comply with platform terms of service.

---

## 🙏 Credits

**Developer:** RAHIBWEB

**Special Thanks:**
- Incentiv Protocol Team
- Community Contributors
- Beta Testers

---

<div align="center">

### 🌟 Star this repo if you find it useful!

[![GitHub Stars](https://img.shields.io/github/stars/rahibweb/incentiv-testnet-bot?style=social)](https://github.com/rahibweb/incentiv-testnet-bot)

**Made with ❤️ for the Crypto Community**

[Telegram](https://t.me/hashycash) • [Chat](https://t.me/hasycashtalks) • [GitHub](https://github.com/rahibweb)

</div>

---

# 🇷🇺 Русская Версия

## ✨ Основные возможности

### 🎯 Управление аккаунтами
- **Умная система регистрации** - Создание новых или регистрация существующих кошельков
- **Автоопределение деплоя** - Определяет задеплоенные смарт-контракты
- **Отслеживание в БД** - SQLite хранилище для аккаунтов и статистики
- **Реферальная система** - Автоматическое применение реф-кодов

### 🤖 Интеллектуальная автоматизация
- **Многопоточность** - Одновременная обработка нескольких аккаунтов
- **Ротация прокси** - HTTP/SOCKS5 с автоматическим переключением
- **Решение капчи** - Интеграция Solvium и 2Captcha
- **Умные повторы** - Экспоненциальная задержка при ошибках
- **Случайные паузы** - Имитация человеческого поведения

### 💰 Операции с токенами
- **Мультитокен** - TCENT, SMPL, BULL, FLIP
- **Случайные переводы** - Автоматическая дистрибуция токенов
- **Умные свапы** - Обмен Native ↔ ERC20
- **Пакетные действия** - Несколько свапов в одной транзакции
- **UnifiedToken Gas** - Оплата комиссий токенами ERC20

### 📊 Продвинутые функции
- **Настраиваемые диапазоны** - Мин/макс суммы для всех операций
- **Фильтрация аккаунтов** - Выбор диапазона или точных номеров
- **Экспорт статистики** - Сохранение в JSON
- **Логирование** - Отслеживание операций в реальном времени
- **Управление контактами** - Добавление случайных контактов

---

## 📥 Установка

**1. Клонируйте репозиторий:**
```bash
git clone https://github.com/rahibweb/incentiv-testnet-bot.git
cd incentiv-testnet-bot
```

**2. Установите зависимости:**
```bash
pip install -r requirements.txt
```

**3. Запустите настройку:**
```bash
python setup.py
```

---

## ⚙️ Конфигурация

### Основные настройки (`settings.yaml`)

```yaml
SETTINGS:
  THREADS: 10                    # Количество потоков
  ATTEMPTS: 5                    # Попытки при ошибках
  SHUFFLE_WALLETS: false         # Перемешать аккаунты

  # Задержки (секунды)
  RANDOM_PAUSE_BETWEEN_ACCOUNTS: [5, 20]
  RANDOM_PAUSE_BETWEEN_ACTIONS: [1, 5]
  PAUSE_BETWEEN_SWAPS: [3, 8]

CAPTCHA:
  PROVIDER: "solvium"            # или "2captcha"
  SOLVIUM_KEY: "ваш_api_ключ"
  CAPTCHA_2CAPTCHA_KEY: "ваш_api_ключ"

# Рандомизированные диапазоны
ACTIONS_COUNT:
  ADD_CONTACTS: [2, 3]           # Случайное кол-во контактов
  TRANSFERS: [7, 20]             # Случайное кол-во переводов
  SWAPS: [6, 20]                 # Случайное кол-во свапов
  BUNDLE_ACTIONS: [10, 20]       # Пакетные действия
  UNIFIED_TOKEN_GAS: [3, 6]      # Транзакции с ERC20 газом

# Диапазоны сумм
TRANSFER:
  TCENT_TRANSFER_AMOUNT: [0.15, 0.25]
  SMPL_TRANSFER_AMOUNT: [0.005, 0.015]

SWAP:
  TCENT_SWAP_AMOUNT: [0.008, 0.012]
  SMPL_SWAP_AMOUNT: [0.008, 0.012]
```

### Настройка файлов данных

**Аккаунты (`data/farm.txt`):**
```
0xВашПриватныйКлюч1
0xВашПриватныйКлюч2
```

**Прокси (`data/proxies.txt`):**
```
http://user:pass@ip:port
socks5://user:pass@ip:port
```

**💎 Рекомендуемый провайдер: NodeMaven**

<div align="center">

<h3>Премиум резидентные прокси для профессиональной автоматизации</h3>

<p>
<a href="https://go.nodemaven.com/RAHIBWEB">
<img src="https://img.shields.io/badge/Получить-NodeMaven_Прокси-0066cc?style=for-the-badge&logo=proxy&logoColor=white" alt="Получить NodeMaven"/>
</a>
</p>

</div>

<table align="center">
<tr>
<td align="center" width="50%">

### 🎁 Эксклюзивные промокоды

<table>
<tr>
<td><b>Код</b></td>
<td><b>Бонус</b></td>
</tr>
<tr>
<td><code>RAHIB</code></td>
<td>+12 ГБ бонусного трафика</td>
</tr>
<tr>
<td><code>RAHIB50</code></td>
<td>Скидка 50% на любой тариф</td>
</tr>
<tr>
<td><code>RAHIB100</code></td>
<td>Удвоение трафика (100ГБ→200ГБ)</td>
</tr>
</table>

</td>
<td align="center" width="50%">

### ⚡ Преимущества

<table>
<tr>
<td>🚀</td>
<td><b>Высокая скорость</b></td>
</tr>
<tr>
<td>🔓</td>
<td><b>Без верификации</b></td>
</tr>
<tr>
<td>💯</td>
<td><b>Реальные бонусы</b></td>
</tr>
<tr>
<td>🎯</td>
<td><b>Для мультиаккаунтинга</b></td>
</tr>
<tr>
<td>🛡️</td>
<td><b>Минимум банов</b></td>
</tr>
</table>

</td>
</tr>
</table>

---

## 🚀 Быстрый старт

```bash
python main.py
```

### Главное меню

```
1. Run Bot (Farm Tasks)          # Запуск фарминга
2. Register New Accounts          # Создать новые кошельки
3. Register Existing Wallets      # Импорт существующих
4. View Statistics                # Просмотр статистики
5. Export Statistics              # Экспорт в JSON
6. Remove All Proxies             # Очистить прокси
7. Database Info                  # Инфо о базе данных
8. Settings                       # Показать настройки
```

### Операции бота

```
1. Claim Testnet Tokens          # Запросить токены
2. Random Add Contact            # Добавить контакты
3. Random Transfer               # Переводы токенов
4. Random Swap                   # Обмен токенов
5. Bundle Action                 # Пакетные свапы
6. Run All Features              # Полная автоматизация
7. UnifiedToken Gas (ERC20)      # Оплата газа ERC20
```

---

## 🎮 Примеры использования

### ⚠️ КРИТИЧЕСКИ ВАЖНО: Действия после регистрации

**После регистрации выполните эти шаги:**

**1. Запросите токены (через бот)**
- Меню: `Run Bot → Claim Testnet Tokens`
- Бот автоматически запросит токены для всех аккаунтов
- Дождитесь поступления токенов

**2. Задеплойте смарт-аккаунт (ВРУЧНУЮ - ОБЯЗАТЕЛЬНО)**
- Перейдите на https://testnet.incentiv.io
- Сделайте **ОДНУ ручную транзакцию** с каждого аккаунта
- Можно простой перевод или обмен
- Это задеплоит смарт-контракт в блокчейне
- **⚠️ Бот НЕ работает без деплоя!**

**3. Запускайте автоматизацию**
- После ручного деплоя запускайте бот
- Бот автоматически определит задеплоенные аккаунты
- Полная автоматизация теперь доступна

---

## 🆘 Поддержка

**Нужна помощь?**
- 📢 **Telegram Канал:** [@hashycash](https://t.me/hashycash)
- 💬 **Telegram Чат:** [@hasycashtalks](https://t.me/hasycashtalks)
- 🐛 **GitHub Issues:** [Сообщить о баге](https://github.com/rahibweb/incentiv-testnet-bot/issues)

---

<div align="center">

**Сделано с ❤️ для крипто-сообщества**

[Telegram](https://t.me/hashycash) • [Чат](https://t.me/hasycashtalks) • [GitHub](https://github.com/rahibweb)

</div>