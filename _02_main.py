import asyncio
import json
import random
import time
import getpass
import csv
import datetime
import os

from aiogram.types import Message
from aiogram.filters import Command

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from typing import List, Tuple

import cexs
from _01_create_wallets import get_first_funding_tx
from spl_trans import send_sol, send_transfer
from config import (
    PRE_JSON, MEXC_CSV, GATE_CSV, CEXS_LIST, async_client, bot, dp, CHAT_ID,
    BALANCE_THRESHOLD, ACTIVITY_THRESHOLD, WARM_CSV, MIN_FUND_AMOUNT, MAX_FUND_AMOUNT,
    COLD_CSV, BONDED_CSV, MIN_SLEEP_SECONDS, MAX_SLEEP_SECONDS
)
from encoding import decrypt_secret

# ---------------- Monitor for wallet inactivity ----------------
last_added_time = time.time()  
LAMPORTS_PER_SOL = 1_000_000_000


async def monitor_inactivity():
    global last_added_time
    while True:
        await asyncio.sleep(300) 
        if time.time() - last_added_time > ACTIVITY_THRESHOLD:
            await send_alert("⚠️ BOT IS INACTIVE FOR 3 HOURS!")

# ---------------- CSV helpers ----------------
def load_wl(cex):
    wallets = []
    if cex == "MEXC":
        with open(MEXC_CSV, "r", newline="") as f:
            for row in csv.DictReader(f):
                wallets.append({"sk": row["sk"], "pk": row["pk"]})
        return wallets
    elif cex == "Gate":
        with open(GATE_CSV, "r", newline="") as f:
            for row in csv.DictReader(f):
                wallets.append({"sk": row["sk"], "pk": row["pk"]})
        return wallets
    return [] 
    
def load_cold_wallets(cex: str | None = None) -> list[dict]:
    rows = []
    if not os.path.exists(COLD_CSV):
        return rows
    with open(COLD_CSV, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if cex and "cex" in row and row["cex"] != cex:
                continue
            rows.append({"sk": row.get("sk",""), "pk": row["pk"]})
    return rows

def load_warm_wallets(cex: str | None = None) -> list[dict]:
    rows = []
    if not os.path.exists(WARM_CSV):
        return rows
    with open(WARM_CSV, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if cex and "cex" in row and row["cex"] != cex:
                continue
            rows.append({"sk": row.get("sk",""), "pk": row["pk"]})
    return rows

def load_bonded() -> list[dict]:
    rows = []
    if not os.path.exists(BONDED_CSV):
        return rows
    with open(BONDED_CSV, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({"sk": row.get("sk",""), "pk": row["pk"]})
    return rows

def _wallet_to_pk(wallet) -> str:
    if isinstance(wallet, dict):
        return str(wallet["pk"]).strip()
    return str(wallet).strip() 

async def add_warm_wallet(cex, wallet):
    path = WARM_CSV
    file_exists = os.path.isfile(path)
    pk = _wallet_to_pk(wallet)
    with open(path, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["sk", "pk", "fund_datetime", "funder_pk", "cex"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        fund_datetime, funder_pk = await get_first_funding_tx(pk)
        w.writerow({
            "sk": wallet["sk"] if isinstance(wallet, dict) else "",
            "pk": pk,
            "fund_datetime": fund_datetime,
            "funder_pk": str(funder_pk),
            "cex": cex
        })

async def add_bonded_wallet(cex, wallet):
    path = BONDED_CSV
    file_exists = os.path.isfile(path)
    pk = _wallet_to_pk(wallet)
    with open(path, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["sk", "pk", "fund_datetime", "funder_pk", "cex"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        fund_datetime, funder_pk = await get_first_funding_tx(pk)
        w.writerow({
            "sk": wallet["sk"] if isinstance(wallet, dict) else "",
            "pk": pk,
            "fund_datetime": fund_datetime,
            "funder_pk": str(funder_pk),
            "cex": cex
        })

# ---------------- Bot commands ----------------
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("👋 Bot is online! Use /stats to get statistics.")

async def send_alert(text: str):
    """Send message to Telegram chat."""
    await bot.send_message(CHAT_ID, text)

async def update_total_balance(password, call: str = "save") -> float:
    total = 0

    # CEX balance
    mexc_balance, _ = cexs.get_mexc_balance()
    print("MEXC balance: ", mexc_balance)
    total += mexc_balance

    gate_balance, _ = cexs.get_gate_balance()
    print("Gate balance:", gate_balance)
    total += gate_balance

    mexc_wl = load_wl("MEXC")

    for w in mexc_wl:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk), "processed")).value / 1e9
        total += sol_balance

    mexc_wl_balances = total - mexc_balance - gate_balance
    print("MEXC wl balances: ", mexc_wl_balances)

    gate_wl = load_wl("Gate")

    for w in gate_wl:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk), "processed")).value / 1e9
        total += sol_balance

    gate_wl_balances = total - mexc_balance - gate_balance - mexc_wl_balances
    print("Gate wl balances: ", gate_wl_balances)

    # Cold wallets (CSV)
    warm = load_warm_wallets()
    for w in warm:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk), "processed")).value / 1e9
        total += sol_balance

    warm_balances = total - mexc_balance - gate_balance - mexc_wl_balances - gate_wl_balances
    print("Warm balances: ", warm_balances)

    bonded = load_bonded()
    for w in bonded:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk), "processed")).value / 1e9
        total += sol_balance

    bonded_balances = total - mexc_balance - gate_balance - warm_balances - mexc_wl_balances - gate_wl_balances
    print("Bonded balances: ", bonded_balances)

    total = round(total, 6)

    print("Total: ", total)

    total_warm = len(warm)

    print("Warm amount: ", total_warm)

    if call == "save":
        with open(PRE_JSON, "r") as f:
            pre = json.load(f)
        
        if total < pre["balance"]-BALANCE_THRESHOLD:
            await send_alert(f"Total balance decreased too much, change amount: {pre['balance']-total} SOL, total balance: {total} SOL")
        else:
            pre["balance"] = total
            
        with open(PRE_JSON, "w", encoding="utf-8") as f:
            json.dump(pre, f, ensure_ascii=False, indent=2)

    await send_alert(f"💰 Balance snapshot saved\n Total: {total} SOL \nMEXC:{mexc_balance} \nBonded:{bonded_balances}")

    return total

async def _get_sol_balance(kp: Keypair) -> float:
    resp = await async_client.get_balance(kp.pubkey(), "processed")
    return resp.value / 1e9

async def fund_cex(
    cex: str,
    cex_pk: str,
    S: float,                     
    password: str,
    warm_csv_path: str = WARM_CSV,           
    pace_sleep_sec: float = 20.0, 
    recheck_delay_sec: int = 1800 
) -> bool:
    B, _ = await cexs.get_cex_balance(cex)
    need = max(0.0, S - float(B))
    if need <= 0:
        return True

    used_wallet_pks: List[str] = []
    sent_total = 0.0

    with open(warm_csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            enc_sk = row.get("sk")
            if not enc_sk:
                continue

            try:
                sk_b58 = decrypt_secret(enc_sk, password)
                kp = Keypair.from_base58_string(sk_b58)
                pk_str = str(kp.pubkey())
            except Exception:
                continue

            try:
                bal = await _get_sol_balance(kp)
            except Exception:
                continue

            if bal <= 0.00205:
                continue

            try:
                await send_transfer(kp, Pubkey.from_string(cex_pk))
            except Exception as e:
                continue

            used_wallet_pks.append(pk_str)
            sent_total += bal

            if pace_sleep_sec > 0:
                await asyncio.sleep(pace_sleep_sec)

            if sent_total >= need:
                break

    if sent_total < need:
        msg = (
            f"⚠️ Insufficient funds to fund {cex}.\n"
            f"Target S={S:.9f} SOL, initial balance B={B:.9f} SOL, shortfall {need:.9f} SOL.\n"
            f"Only {sent_total:.9f} SOL could be sent.\n"
        )
        await send_alert(msg)
        raise SystemExit(1)

    B1, _ = await cexs.get_cex_balance(cex)
    if float(B1) >= float(B) + float(sent_total):
        return True

    await asyncio.sleep(recheck_delay_sec)
    B2, _ = await cexs.get_cex_balance(cex)
    if float(B2) >= float(B) + float(sent_total):
        return True

    msg = (
        f"⚠️ {cex}: balance did not update after funding.\n"
        f"Expected ≥ {(B + sent_total):.9f} SOL, actual: {float(B2):.9f} SOL.\n"
        f"Source wallets: {', '.join(used_wallet_pks) if used_wallet_pks else '—'}"
    )

    await send_alert(msg)
    raise SystemExit(1)

async def withdraw_cex(cex, cex_pk, cex_balance, amount, to_fund_pk, pre_balance, password):
    retry = 0
    while retry < 2: 
        if cex == "MEXC":
            mexc_balance, _ = cexs.get_mexc_balance()

            if mexc_balance >= amount: 
                print("MEXC ", amount)
                msg = cexs.mexc_withdraw(amount, str(to_fund_pk))
                return
        
            else:
                print("Insufficient balance")
                await fund_cex(cex, cex_pk, amount, password)
                cexs.mexc_withdraw(amount, str(to_fund_pk))
                return
            
        elif cex == "Gate":
            print("Gate ", amount)

            gate_balance, _ = cexs.get_gate_balance()

            if gate_balance >= amount: 
                msg = cexs.gate_withdraw(amount, str(to_fund_pk))
                return
            
            else:
                print("Insufficient balance")
                await fund_cex(cex, cex_pk, amount, password)
                cexs.gate_withdraw(amount, str(to_fund_pk))
                return
    return

async def _get_balance_sol(async_client, pubkey_str: str) -> float:
    resp = await async_client.get_balance(Pubkey.from_string(pubkey_str), "processed")
    return resp.value / 1e9

async def confirm_deposit_or_alert(
    target_pubkey: str,          # адрес пополняемого аккаунта (депозита)
    source_pubkey: str,          # адрес кошелька-источника
    amount_sent_sol: float,      # сумма пополнения (SOL)
    before_balance_sol: float,   # баланс target ДО пополнения (SOL)
    recheck_delay_sec: int = 1800,   # ОБЩЕЕ окно ожидания (по умолчанию 30 мин)
    poll_interval_sec: int = 120     # интервал опроса (по умолчанию 2 мин)
) -> bool:
    """
    Периодически проверяет, что баланс target >= before + amount.
    Чекает сразу, затем каждые poll_interval_sec, пока не истечёт recheck_delay_sec.
    При провале шлёт алерт и завершает процесс.
    """
    EPS = 1e-6  # небольшой допуск на комиссии/округления
    expected = float(before_balance_sol) + float(amount_sent_sol)
    deadline = time.time() + float(recheck_delay_sec)
    last_seen = None

    while True:
        now = await _get_balance_sol(async_client, target_pubkey)
        last_seen = now
        if now + EPS >= expected:
            return True

        remaining = deadline - time.time()
        if remaining <= 0:
            break

        await asyncio.sleep(min(poll_interval_sec, max(remaining, 0)))

    # Дважды/многократно не выполнилось — алерт и стоп
    msg = (
        "⚠️ Пополнение не подтверждено.\n"
        f"Аккаунт: {target_pubkey}\n"
        f"Ожидалось ≥ {expected:.9f} SOL (до пополнения {before_balance_sol:.9f} + "
        f"отправлено {amount_sent_sol:.9f}).\n"
        f"Фактический баланс: {last_seen:.9f} SOL.\n"
        f"Источник вывода: {source_pubkey}"
    )
    await send_alert(msg)
    raise SystemExit(1)
# ---------------- Main wallet logic ----------------
async def wallet_loop(password):
    global last_added_time  
    await update_total_balance(password)

    while True:
        cex = random.choice(CEXS_LIST)

        warm_rows = load_warm_wallets()
        warm_pks = {w["pk"] for w in warm_rows}

        wl = load_wl(cex)  
        candidates = [w for w in wl if w["pk"] not in warm_pks]
        if not candidates:
            await asyncio.sleep(60)
            await send_alert("NO CANDIDATES")
            continue

        w1 = random.choice(candidates)
        w1_sk = decrypt_secret(w1["sk"], password)
        w1_kp = Keypair.from_base58_string(w1_sk)
        w1_pk = w1_kp.pubkey()

        amount = round(random.uniform(MIN_FUND_AMOUNT, MAX_FUND_AMOUNT), 6)

        w1_before = (await async_client.get_balance(w1_pk, "processed")).value / LAMPORTS_PER_SOL

        cex_balance, cex_pk = await cexs.get_cex_balance(cex)

        await withdraw_cex(cex, cex_pk, cex_balance, amount, w1_pk, w1_before, password)

        to_sleep = random.randint(MIN_SLEEP_SECONDS, MAX_SLEEP_SECONDS)
        print(f"Sleeping for {to_sleep/60} min")
        await asyncio.sleep(to_sleep)

        await confirm_deposit_or_alert(str(w1_pk), str(cex_pk), amount, 0)

        await add_warm_wallet(cex, w1)

        cold_rows = load_cold_wallets()
        bonded_rows = load_bonded()
        bonded_pks = {w["pk"] for w in bonded_rows}
        cold_candidates = [w for w in cold_rows if w["pk"] not in warm_pks and w["pk"] not in bonded_pks]
        if not cold_candidates:
            await send_alert("No COLD candidates for w2")
            continue

        w2 = random.choice(cold_candidates)
        w2_sk = decrypt_secret(w2["sk"], password)
        w2_kp = Keypair.from_base58_string(w2_sk)
        w2_pk = w2_kp.pubkey()

        sol_to_w2 = await send_sol(w1_kp, w2_pk)
        await confirm_deposit_or_alert(str(w2_pk), str(w1_pk), sol_to_w2, 0)

        if random.random() <= 0.33:
            cold_candidates_w3 = [w for w in cold_rows if w["pk"] not in warm_pks and w["pk"] not in bonded_pks and w["pk"] != str(w2_pk)]
            if not cold_candidates_w3:
                await send_alert("No COLD candidates for w3")
            else:
                w3 = random.choice(cold_candidates_w3)
                w3_sk = decrypt_secret(w3["sk"], password)
                w3_kp = Keypair.from_base58_string(w3_sk)
                w3_pk = w3_kp.pubkey()

                sol_to_w3 = await send_sol(w2_kp, w3_pk)
                await confirm_deposit_or_alert(str(w3_pk), str(w2_pk), sol_to_w3, 0)
                await add_warm_wallet(cex, w2)
                await add_bonded_wallet(cex, w3)
        else:
            await add_bonded_wallet(cex, w2)

        last_added_time = time.time()

        total_balance = await update_total_balance(password, call="save")
        await send_alert(f"Total balance updated: {total_balance} SOL")

async def password_buffer():
    password = getpass.getpass("Enter password: ")
    print("Password check passed!")

    await wallet_loop(password)

# ---------------- Runner ----------------
async def runner():
    await asyncio.gather(
        password_buffer(),
        dp.start_polling(bot),
        monitor_inactivity() 
    )

if __name__ == "__main__":
    asyncio.run(runner())



