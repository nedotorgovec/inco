import asyncio
import random
from web3 import Web3
from config import TX_DELAY, shuffle_wallets
from hangman import play_hangman_single as play_hangman
from comfy import mint_usdc, mint_cusdc, shield_usdc, unshield_cusdc
from hangman import connect_to_rpc_with_proxy



# ------------------------ НАСТРОЙКИ ------------------------
ROUNDS_PER_WALLET = 2
MODE = "comfy"  # hangman, comfy, mixed

# ------------------------ ВЫБОР ------------------------
SELECTED_GROUP = 0   # индекс группы приватников (0 = первая, 1 = вторая, ...)
SELECTED_PROXY = 0   # индекс прокси (0 = первый, 1 = второй, ...)

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


# ------------------------ ПРОКСИ ------------------------
try:
    with open("proxies.txt", "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
    PROXY = proxies[SELECTED_PROXY] if SELECTED_PROXY < len(proxies) else None
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

# ------------------------ Чтение приватников ------------------------
def load_wallets(file_path, group_index):
    with open(file_path, "r") as f:
        content = f.read().strip()
    groups_raw = [group.strip().splitlines() for group in content.split("---")]
    wallets = []
    if group_index < len(groups_raw):
        for line in groups_raw[group_index]:
            line = line.strip()
            if line and not line.startswith("#"):
                wallets.append(line)
    return wallets

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
            func = random.choice(functions)
            print_colored(f"⏳ [{public}] Round {round_num}: starting {func.__name__}", "magenta")
            try:
                await func(w3, wallet)
                print_colored(f"✅ [{public}] Round {round_num}: {func.__name__} finished successfully", "green")
            except Exception as e:
                print_colored(f"❌ [{public}] Round {round_num}: {func.__name__} failed | {e}", "red")

            # Задержка между функциями
            await wallet_delay(wallet)

    except Exception as e:
        print_colored(f"❌ [{public}] Wallet processing failed: {e}", "red")

# ------------------------ ОСНОВНОЙ ЦИКЛ ------------------------
async def main():
    wallets = load_wallets("wallets.txt", SELECTED_GROUP)

    if shuffle_wallets:
        random.shuffle(wallets)

    print_colored(f"🚀 Starting in mode: {MODE} | Using proxy #{SELECTED_PROXY+1}", "cyan")
    print_colored(f"👛 Loaded {len(wallets)} wallets from group #{SELECTED_GROUP+1}", "yellow")

    tasks = [process_wallet(wallet) for wallet in wallets]
    await asyncio.gather(*tasks)

    print_colored("🎉 All wallet operations completed", "green")

# ------------------------ ЗАПУСК ------------------------
if __name__ == "__main__":
    asyncio.run(main())
