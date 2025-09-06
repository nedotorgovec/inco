import asyncio
import random
from web3 import Web3
from colorama import Fore, Style, init

init(autoreset=True)

# -------------------- Настройки --------------------
DELAY_RANGE = (15, 25)
WRAP_CONTRACT = '0xA449bc031fA0b815cA14fAFD0c5EdB75ccD9c80f'
USDC_CONTRACT = '0xAF33ADd7918F685B2A82C1077bd8c07d220FFA04'
CHAIN_ID = 84532
RPC_URL = "https://sepolia.base.org"
ROUNDS_PER_WALLET = 2  # количество функций за один "раунд" кошелька

COLOR_LIST = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.CYAN, Fore.MAGENTA]
wallet_colors = {}
wallet_delays = {}
wallet_nonces = {}

# -------------------- Цвета --------------------
def assign_colors(wallets):
    for i, wallet in enumerate(wallets):
        public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
        wallet_colors[public] = COLOR_LIST[i % len(COLOR_LIST)]
        wallet_delays[public] = random.uniform(DELAY_RANGE[0], DELAY_RANGE[1])

def colorize_for_wallet(text, public):
    color = wallet_colors.get(public, Fore.CYAN)
    return f"{color}{text}{Style.RESET_ALL}"

# -------------------- RPC с прокси --------------------
def connect_to_rpc_with_proxy(proxy=None):
    if proxy:
        import os
        os.environ["HTTP_PROXY"] = proxy
        os.environ["HTTPS_PROXY"] = proxy
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise Exception(f"❌ Could not connect to RPC: {RPC_URL}")
    print(f"{Fore.MAGENTA}✅ Connected to RPC: {RPC_URL}{Style.RESET_ALL}")
    return w3

# -------------------- Nonce --------------------
def get_nonce(w3, wallet):
    if wallet not in wallet_nonces:
        public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
        wallet_nonces[wallet] = w3.eth.get_transaction_count(public)
    nonce = wallet_nonces[wallet]
    wallet_nonces[wallet] += 1
    return nonce

# -------------------- Рандомная задержка --------------------
async def delay(wallet=None):
    if wallet:
        public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
        t = wallet_delays.get(public, random.uniform(DELAY_RANGE[0], DELAY_RANGE[1]))
        print(colorize_for_wallet(f"⏱ Waiting {t:.1f}s before next tx", public))
    else:
        t = random.uniform(DELAY_RANGE[0], DELAY_RANGE[1])
    await asyncio.sleep(t)

# -------------------- Отправка транзакции --------------------
async def send_transaction(w3, wallet, tx, description="tx"):
    public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    for attempt in range(3):
        try:
            gas_estimate = w3.eth.estimate_gas(tx)
            tx['gas'] = int(gas_estimate * 1.2)
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(colorize_for_wallet(f'⚠️ Gas estimation failed, retry {attempt + 1}: {e}', public))

    signed_tx = w3.eth.account.sign_transaction(tx, wallet)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt["status"] != 1:
        raise Exception(f"[{tx['from']}] {description} transaction failed")
    print(colorize_for_wallet(f"[{tx['from']}] {description} DONE | {tx_hash.hex()}", public))
    return tx_hash.hex()

# -------------------- Случайные суммы для каждой функции --------------------
def random_amount_for_function(func_type):
    if func_type in ["mint_usdc", "mint_cusdc"]:
        return random.randint(2000, 5000)  # больше токенов
    elif func_type == "unshield_cusdc":
        return random.randint(100, 2500)   # меньше токенов
    elif func_type == "shield_usdc":
        return random.randint(500, 3000)   # среднее количество
    else:
        return random.randint(1000, 3000)

# -------------------- Основные операции --------------------
async def mint_usdc(w3, wallet):
    public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    amount = int(w3.to_wei(random_amount_for_function("mint_usdc"), "ether"))
    tx = {
        "chainId": CHAIN_ID,
        "data": f"0x40c10f19"
                f"000000000000000000000000{public.lower()[2:]}"
                f"{amount:064x}",
        "from": public,
        "gas": random.randint(170000, 200000),
        "gasPrice": w3.eth.gas_price,
        "nonce": get_nonce(w3, wallet),
        "to": USDC_CONTRACT
    }
    return await send_transaction(w3, wallet, tx, "mint_usdc")

async def mint_cusdc(w3, wallet):
    public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    amount = int(w3.to_wei(random_amount_for_function("mint_cusdc"), "ether"))
    tx = {
        "chainId": CHAIN_ID,
        "data": f"0x40c10f19"
                f"000000000000000000000000{public.lower()[2:]}"
                f"{amount:064x}",
        "from": public,
        "gas": random.randint(170000, 200000),
        "gasPrice": w3.eth.gas_price,
        "nonce": get_nonce(w3, wallet),
        "to": WRAP_CONTRACT
    }
    return await send_transaction(w3, wallet, tx, "mint_cusdc")

async def shield_usdc(w3, wallet):
    public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    amount = int(w3.to_wei(random_amount_for_function("shield_usdc"), "ether"))
    tx_approve = {
        "chainId": CHAIN_ID,
        "data": f"0x095ea7b3"
                f"000000000000000000000000{WRAP_CONTRACT.lower()[2:]}"
                f"{amount:064x}",
        "from": public,
        "gas": random.randint(170000, 200000),
        "gasPrice": w3.eth.gas_price,
        "nonce": get_nonce(w3, wallet),
        "to": USDC_CONTRACT
    }
    await send_transaction(w3, wallet, tx_approve, "approve")
    await delay(wallet)

    tx_wrap = {
        "chainId": CHAIN_ID,
        "data": f"0xea598cb0{amount:064x}",
        "from": public,
        "gas": random.randint(190000, 220000),
        "gasPrice": w3.eth.gas_price,
        "nonce": get_nonce(w3, wallet),
        "to": WRAP_CONTRACT
    }
    return await send_transaction(w3, wallet, tx_wrap, "wrap")

async def unshield_cusdc(w3, wallet):
    public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    amount = int(w3.to_wei(random_amount_for_function("unshield_cusdc"), "ether"))
    tx = {
        "chainId": CHAIN_ID,
        "data": f"0xde0e9a3e{amount:064x}",
        "from": public,
        "gas": random.randint(190000, 220000),
        "gasPrice": w3.eth.gas_price,
        "nonce": get_nonce(w3, wallet),
        "to": WRAP_CONTRACT
    }
    return await send_transaction(w3, wallet, tx, "unshield_cusdc")

# -------------------- Обработка одного кошелька --------------------
async def process_wallet(w3, wallet):
    public = Web3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    functions = [mint_usdc, mint_cusdc, shield_usdc, unshield_cusdc]

    try:
        for round_num in range(1, ROUNDS_PER_WALLET + 1):
            func = random.choice(functions)  # рандомный выбор функции
            print(colorize_for_wallet(f"⏳ [{public}] Round {round_num}: starting {func.__name__}", public))
            try:
                await func(w3, wallet)
            except Exception as e:
                print(colorize_for_wallet(f"❌ [{public}] Round {round_num}: {func.__name__} failed | {e}", public))
            
            await delay(wallet)

    except Exception as e:
        print(colorize_for_wallet(f"[{public}] Wallet processing failed: {e}", public))

# -------------------- Обработка всех кошельков --------------------
async def process_all_wallets(w3, wallets):
    assign_colors(wallets)
    tasks = [process_wallet(w3, wallet) for wallet in wallets]
    await asyncio.gather(*tasks, return_exceptions=True)

# -------------------- Запуск --------------------
if __name__ == "__main__":
    with open("wallets.txt", "r") as f:
        wallets = [line.strip() for line in f if line.strip()]

    try:
        with open("proxies.txt", "r") as f:
            PROXY = f.readline().strip()
    except:
        PROXY = None

    w3 = connect_to_rpc_with_proxy(PROXY)
    asyncio.run(process_all_wallets(w3, wallets))
