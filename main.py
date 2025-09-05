import asyncio
import random
from web3 import Web3
from config import TX_DELAY, shuffle_wallets
from hangman import play_hangman_single as play_hangman
from comfy import mint_usdc, mint_cusdc, shield_usdc, unshield_cusdc
from hangman import connect_to_rpc_with_proxy

# ------------------------ ЦВЕТА ------------------------
COLORS = {
    "reset": "\033[0m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
}

def colorize(text, color="cyan"):
    return f"{COLORS.get(color,'')}{text}{COLORS['reset']}"

def print_colored(message, color="cyan"):
    print(colorize(message, color))

# ------------------------ НАСТРОЙКИ ------------------------
ROUNDS_PER_WALLET = 2
MODE = "mixed"  # hangman, comfy, mixed

# ------------------------ ПРОКСИ ------------------------
try:
    with open("proxies.txt", "r") as f:
        PROXY = f.readline().strip()
except:
    PROXY = None

# ------------------------ RPC ------------------------
w3 = connect_to_rpc_with_proxy(PROXY)

# ------------------------ Индивидуальная задержка ------------------------
wallet_delays = {}

def get_wallet_delay(wallet):
    if wallet not in wallet_delays:
        wallet_delays[wallet] = random.uniform(TX_DELAY[0], TX_DELAY[1])
    return wallet_delays[wallet]

async def wallet_delay(wallet):
    delay = get_wallet_delay(wallet)
    public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    print_colored(f"⏱ [{public}] Waiting {delay:.1f}s before next function", "yellow")
    await asyncio.sleep(delay)

# ------------------------ ОБРАБОТКА КОШЕЛЬКА ------------------------
async def process_wallet(wallet: str):
    public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    print_colored(f"\n🔑 Wallet: {public}", "cyan")
    if PROXY:
        print_colored(f"🌐 Using proxy: {PROXY}", "yellow")

    # Выбор функций в зависимости от режима
    if MODE == "hangman":
        functions = [play_hangman]
    elif MODE == "comfy":
        functions = [mint_usdc, mint_cusdc, shield_usdc, unshield_cusdc]
    else:  # mixed
        functions = [mint_usdc, mint_cusdc, shield_usdc, unshield_cusdc, play_hangman]

    try:
        for round_num in range(1, ROUNDS_PER_WALLET + 1):
            # Для mixed режима выбираем случайную функцию, но не более ROUNDS_PER_WALLET
            func = random.choice(functions)
            print_colored(f"⏳ [{public}] Round {round_num}: starting {func.__name__}", "magenta")
            try:
                await func(w3, wallet)  # все функции получают w3 и wallet
                print_colored(f"✅ [{public}] Round {round_num}: {func.__name__} finished successfully", "green")
            except Exception as e:
                print_colored(f"❌ [{public}] Round {round_num}: {func.__name__} failed | {e}", "red")

            # Задержка между функциями
            await wallet_delay(wallet)

    except Exception as e:
        print_colored(f"❌ [{public}] Wallet processing failed: {e}", "red")

# ------------------------ ОСНОВНОЙ ЦИКЛ ------------------------
async def main():
    with open("wallets.txt", "r") as f:
        wallets = [line.strip() for line in f if line.strip()]

    if shuffle_wallets:
        random.shuffle(wallets)

    print_colored(f"🚀 Starting in mode: {MODE}", "cyan")

    tasks = [process_wallet(wallet) for wallet in wallets]
    await asyncio.gather(*tasks)

    print_colored("🎉 All wallet operations completed", "green")

# ------------------------ ЗАПУСК ------------------------
if __name__ == "__main__":
    asyncio.run(main())
