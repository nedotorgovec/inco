import asyncio
import random
import logging
from web3 import Web3
from eth_abi import encode
import config
import requests
from colorama import Fore, Style, init

init(autoreset=True)  # Автоматически сбрасывать цвета после каждого print

# -------------------- Настройка логов --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler("mint_operations.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -------------------- Константы --------------------
WORDS = [
    "play", "time", "home", "mind", "work", "jump", "farm", "cake",
    "bake", "fire", "wind", "gold", "road", "love", "rock", "rain",
    "star", "fish", "desk", "news", "team", "care", "peak", "golf",
    "mesh", "ping", "dock", "lamb", "comb", "stem", "grow", "clan",
    "hint", "glad", "vile", "zone", "xray", "kids", "pony", "germ",
    "bank", "ship", "bark", "dust", "made", "sake", "corn", "pail",
    "tuck", "boil", "ramp", "vase", "blow", "chat", "drum", "flop",
    "grim", "hazy", "jolt", "keen", "lurk", "moat", "numb", "oath",
    "pace", "quit", "rude", "dope", "tail", "urge", "veto", "yarn",
    "zinc"
]

LETTER_DELAY = (20, 38)
MAX_LIVES = 8
CHAIN_ID = 84532
HANGMAN_FACTORY_ADDRESS = "0x9d0C9Cde372c3b50e953E6dD620B503f2Bddc6A2"
HANGMAN_FACTORY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "player", "type": "address"},
            {"indexed": False, "internalType": "address", "name": "gameContract", "type": "address"}
        ],
        "name": "GameCreated",
        "type": "event"
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "getGameAddressByPlayer",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

RPC_URL = "https://sepolia.base.org"

# -------------------- Цвета --------------------
COLOR_LIST = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.CYAN, Fore.MAGENTA]
wallet_colors = {}

def assign_colors(wallets):
    for i, wallet in enumerate(wallets):
        public = Web3().eth.account.from_key(wallet).address
        public = Web3.to_checksum_address(public)
        wallet_colors[public] = COLOR_LIST[i % len(COLOR_LIST)]

def colorize_for_wallet(text, public):
    color = wallet_colors.get(public, Fore.CYAN)
    return f"{color}{text}{Style.RESET_ALL}"

# -------------------- RPC с прокси --------------------
def connect_to_rpc_with_proxy(proxy=None):
    session = None
    if proxy:
        session = requests.Session()
        session.proxies = {"http": proxy, "https": proxy}
    w3 = Web3(Web3.HTTPProvider(RPC_URL, session=session))
    if not w3.is_connected():
        raise Exception(f"❌ Could not connect to RPC: {RPC_URL}")
    print(f"{Fore.MAGENTA}✅ Connected to RPC: {RPC_URL}{Style.RESET_ALL}")
    return w3

# -------------------- Управление nonce --------------------
wallet_nonces = {}
def get_nonce(w3, wallet):
    if wallet not in wallet_nonces:
        public = Web3().eth.account.from_key(wallet).address
        wallet_nonces[wallet] = w3.eth.get_transaction_count(Web3.to_checksum_address(public))
    nonce = wallet_nonces[wallet]
    wallet_nonces[wallet] += 1
    return nonce

# -------------------- Универсальная транзакция --------------------
async def send_transaction(w3, wallet, tx):
    signed_tx = w3.eth.account.sign_transaction(tx, wallet)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt["status"] != 1:
        raise Exception(f"[{tx['from']}] transaction failed")
    return tx_hash.hex()

# -------------------- Создание игры --------------------
async def create_game(w3, wallet):
    public = w3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    tx = {
        "chainId": CHAIN_ID,
        "data": f"0x9feb6c1b000000000000000000000000{public.lower()[2:]}",
        "from": public,
        "gas": random.randint(1700000, 2300000),
        "gasPrice": w3.eth.gas_price,
        "nonce": get_nonce(w3, wallet),
        "to": HANGMAN_FACTORY_ADDRESS,
    }
    await send_transaction(w3, wallet, tx)
    factory_contract = w3.eth.contract(address=HANGMAN_FACTORY_ADDRESS, abi=HANGMAN_FACTORY_ABI)
    return factory_contract.functions.getGameAddressByPlayer(public).call()

# -------------------- Угадывание буквы --------------------
async def guess_letter(w3, wallet, game_address, letter):
    public = w3.to_checksum_address(Web3().eth.account.from_key(wallet).address)
    encoded_string = encode(["string"], [letter]).hex()[2:]
    tx_data = f"0x662a655900{encoded_string}"
    tx = {
        "chainId": CHAIN_ID,
        "data": tx_data,
        "from": public,
        "gas": random.randint(1100000, 1500000),
        "gasPrice": w3.eth.gas_price,
        "nonce": get_nonce(w3, wallet),
        "to": game_address,
    }
    await send_transaction(w3, wallet, tx)

# -------------------- Симуляция состояния игры --------------------
def simulate_game_state(word, guessed_letters, lives):
    display_word = "".join(letter if letter in guessed_letters else "_" for letter in word)
    has_won = display_word == word
    has_lost = lives <= 0 and not has_won
    return {"display_word": display_word, "lives": lives, "has_won": has_won, "has_lost": has_lost}

# -------------------- Игра на одном кошельке --------------------
async def play_hangman_single(w3, wallet):
    public = Web3().eth.account.from_key(wallet).address
    public = Web3.to_checksum_address(public)
    game_address = await create_game(w3, wallet)
    secret_word = random.choice(WORDS)

    guessed_letters = set()
    lives = MAX_LIVES
    word_letters = list(secret_word)
    available_wrong_letters = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in secret_word]

    round_counter = 1
    while lives > 0 and word_letters:
        if random.random() < getattr(config, "ERROR_PROBABILITY", 0) and available_wrong_letters:
            letter = random.choice(available_wrong_letters)
            available_wrong_letters.remove(letter)
            letter_type = "❌ wrong"
        else:
            letter = random.choice(word_letters)
            word_letters.remove(letter)
            letter_type = "✅ correct"

        logger.info(colorize_for_wallet(
            f"[{public}] Round {round_counter} | Guessing letter '{letter}' ({letter_type}) | Lives: {lives}",
            public
        ))
        await guess_letter(w3, wallet, game_address, letter)
        guessed_letters.add(letter)
        if letter not in secret_word:
            lives -= 1

        state = simulate_game_state(secret_word, guessed_letters, lives)
        if state["has_won"]:
            logger.info(colorize_for_wallet(f"[{public}] Game completed: 🎉 Won!", public))
            break
        if state["has_lost"]:
            logger.info(colorize_for_wallet(f"[{public}] Game completed: ❌ Lost!", public))
            break

        # Рандомная задержка между буквами
        await asyncio.sleep(random.uniform(LETTER_DELAY[0], LETTER_DELAY[1]))
        round_counter += 1

# -------------------- Обработка всех кошельков --------------------
async def play_hangman_all(w3, wallets):
    assign_colors(wallets)
    if getattr(config, "shuffle_wallets", False):
        random.shuffle(wallets)

    for wallet in wallets:
        try:
            await play_hangman_single(w3, wallet)
            # Рандомная задержка между кошельками
            await asyncio.sleep(random.uniform(LETTER_DELAY[0], LETTER_DELAY[1]))
        except Exception as e:
            public = Web3().eth.account.from_key(wallet).address
            public = Web3.to_checksum_address(public)
            logger.error(colorize_for_wallet(f"[{public}] Error: {e}", public))

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
    asyncio.run(play_hangman_all(w3, wallets))
