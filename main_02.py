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

import cexs
from create_wallets_01 import get_first_funding_tx
from spl_trans import send_sol, send_transfer
from config import PRE_JSON, MEXC_COLD_CSV, GATE_COLD_CSV, FUNDS_JSON, MEXC_WARM_CSV, GATE_WARM_CSV, CEXS_LIST, async_client, bot, dp, CHAT_ID, BALANCE_THRESHOLD, ACTIVITY_THRESHOLD
from encoding import decrypt_secret

# ---------------- Monitor for wallet inactivity ----------------
last_added_time = time.time()  

async def monitor_inactivity():
    global last_added_time
    while True:
        await asyncio.sleep(300) 
        if time.time() - last_added_time > ACTIVITY_THRESHOLD:
            await send_alert("⚠️ BOT IS INACTIVE FOR 3 HOURS!")

# ---------------- CSV helpers ----------------
def load_cold_wallets(cex):
    wallets = []
    
    if cex == "MEXC":
        with open(MEXC_COLD_CSV, "r", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                wallets.append({"sk": row["sk"], "pk": row["pk"]})

        return wallets
    
    elif cex == "Gate":
        with open(GATE_COLD_CSV, "r", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                wallets.append({"sk": row["sk"], "pk": row["pk"]})

        return wallets
    
def load_warm_wallets(cex):
    wallets = []

    if cex == "MEXC":
        try:
            with open(MEXC_WARM_CSV, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    wallets.append(row)

        except FileNotFoundError:
            pass
    
    elif cex == "Gate":
        try:
            with open(GATE_WARM_CSV, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    wallets.append(row)

        except FileNotFoundError:
            pass
    return wallets

async def add_warm_wallet(cex, wallet):
    if cex == "MEXC":
        path = MEXC_WARM_CSV
    elif cex == "Gate":
        path = GATE_WARM_CSV
    else:
        raise ValueError("Unsupported CEX")

    file_exists = os.path.isfile(path)

    with open(path, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["sk", "pk", "fund_datetime", "funder_pk"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        fund_datetime, funder_pk = await get_first_funding_tx(str(wallet["pk"]).strip())

        writer.writerow({
            "sk": str(wallet["sk"]).strip(),
            "pk": str(wallet["pk"]).strip(),
            "fund_datetime": fund_datetime,
            "funder_pk": str(funder_pk)
        })

# ---------------- Bot commands ----------------
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("👋 Bot is online! Use /stats to get statistics.")

@dp.message(Command("stats"))
async def stats_command(message: Message):
    total, mexc_balance, gate_balance, funds_balances, total_warm = await get_stats()
    stats_message = f"Stats:\nTotal balance: {total} SOL\nMEXC balance: {mexc_balance}\nGate balance: {gate_balance}\nfunds balances sum: {funds_balances}\nwarm wallets amount: {total_warm}"
    await message.answer(stats_message)

async def send_alert(text: str):
    """Send message to Telegram chat."""
    await bot.send_message(CHAT_ID, text)

async def finish_cold(password, cex, to_fund_pk, to_fund , to_fund_kp):
    with open(FUNDS_JSON, "r") as f:
        funds = json.load(f)

    target_fund = random.choice(funds)
    target_fund_sk = decrypt_secret(target_fund["sk"], password)
    fund_pk = Keypair.from_base58_string(target_fund_sk).pubkey()

    print("Fund pk: ", fund_pk)

    # get full balance of cold wallet
    cold_balance = (await async_client.get_balance(to_fund_pk)).value
    cold_balance_sol = round(cold_balance / 1e9, 6)

    if cold_balance_sol > 0:
        print("sending ", cold_balance_sol, " to funding")
        sol_to_send = await send_sol(to_fund_kp, fund_pk)
        cold_change = await wait_for_decrease_cold(to_fund_pk, cold_balance_sol)
        if cold_change:
            await send_alert(f"🔄 Sent {sol_to_send} SOL from cold → fund")
        else:
            print("No cold change")

    # ---------------- Add to warm.csv ----------------
    await add_warm_wallet(cex, to_fund)
   
    # update total balance
    total_balance = await update_total_balance(password, call="no")
    await send_alert(f"Total balance updated: {total_balance} SOL")

async def get_stats():
    total = 0

    # CEX balance
    mexc_balance, _ = cexs.get_mexc_balance()
    print("MEXC balance: ", mexc_balance)
    total += mexc_balance

    gate_balance, _ = cexs.get_gate_balance()
    print("Gate balance:", gate_balance)
    total += gate_balance

    # Cold wallets (CSV)
    mexc_cold = load_cold_wallets("MEXC")
    for w in mexc_cold:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk))).value / 1e9
        total += sol_balance

    mexc_cold_balances = total - mexc_balance - gate_balance
    print("Mexc cold balances sum: ", mexc_cold_balances)

    gate_cold = load_cold_wallets("Gate")
    for w in gate_cold:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk))).value / 1e9
        total += sol_balance

    gate_cold_balances = total - mexc_balance - gate_balance - mexc_cold_balances
    print("Gate cold balances sum: ", gate_cold_balances)

    # Fund wallets
    with open(FUNDS_JSON, "r") as f:
        funds = json.load(f)
    for w in funds:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk))).value / 1e9
        total += sol_balance

    funds_balances = round(total - mexc_balance - gate_balance - mexc_cold_balances - gate_cold_balances, 6)

    print("Funds balances sum: ", funds_balances)

    total = round(total, 6)

    print("Total: ", total)

    gate_warm = load_warm_wallets("Gate")
    mexc_warm = load_warm_wallets("MEXC")
    total_warm = len(gate_warm) + len(mexc_warm)

    print("Warm amount: ", total_warm)

    return total, mexc_balance, gate_balance, funds_balances, total_warm

async def update_total_balance(password, call: str = "save") -> float:
    total = 0

    # CEX balance
    mexc_balance, _ = cexs.get_mexc_balance()
    print("MEXC balance: ", mexc_balance)
    total += mexc_balance

    gate_balance, _ = cexs.get_gate_balance()
    print("Gate balance:", gate_balance)
    total += gate_balance

    # Cold wallets (CSV)
    mexc_cold = load_cold_wallets("MEXC")
    for w in mexc_cold:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk))).value / 1e9
        if sol_balance > 0:
            await finish_cold(password, "MEXC", Pubkey.from_string(pk), w, Keypair.from_base58_string(decrypt_secret(w["sk"], password)))
            continue
        total += sol_balance

    mexc_cold_balances = total - mexc_balance - gate_balance
    print("Mexc cold balances sum: ", mexc_cold_balances)

    gate_cold = load_cold_wallets("Gate")
    for w in gate_cold:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk))).value / 1e9
        if sol_balance > 0:
            await finish_cold(password, "Gate", Pubkey.from_string(pk), w, Keypair.from_base58_string(decrypt_secret(w["sk"], password)))
            continue
        total += sol_balance

    gate_cold_balances = total - mexc_balance - gate_balance - mexc_cold_balances
    print("Gate cold balances sum: ", gate_cold_balances)

    # Fund wallets
    with open(FUNDS_JSON, "r") as f:
        funds = json.load(f)
    for w in funds:
        pk = str(w["pk"]).strip()
        sol_balance = (await async_client.get_balance(Pubkey.from_string(pk))).value / 1e9
        total += sol_balance

    funds_balances = round(total - mexc_balance - gate_balance - mexc_cold_balances - gate_cold_balances, 6)

    print("Funds balances sum: ", funds_balances)

    total = round(total, 6)

    print("Total: ", total)

    gate_warm = load_warm_wallets("Gate")
    mexc_warm = load_warm_wallets("MEXC")
    total_warm = len(gate_warm) + len(mexc_warm)

    print("Warm amount: ", total_warm)

    if call == "save":
        with open(PRE_JSON, "r") as f:
            pre = json.load(f)
        
        if total < pre["balance"]-BALANCE_THRESHOLD:
            pre["balance"] = total
        else:
            await send_alert(f"Total balance decreased too much, change amount: {pre["balance"]-total} SOL, total balance: {total} SOL")

        with open(PRE_JSON, "w", encoding="utf-8") as f:
            json.dump(pre, f, ensure_ascii=False, indent=2)

    await send_alert(f"💰 Balance snapshot saved\n Total: {total} SOL \nCold:{mexc_cold_balances + gate_cold_balances} \nFunds:{funds_balances}")

    return total


async def parse_fund_balances(amount, password):
    """Parse balances of funding wallets, return (balance, key)."""
    with open(FUNDS_JSON, "r") as f:
        funds = json.load(f)

    for w in funds:
        w_sk = decrypt_secret(w["sk"], password)
        sol_balance = (await async_client.get_balance(Keypair.from_base58_string(w_sk).pubkey())).value / 1e9
        if sol_balance > amount:
            return sol_balance, w_sk

    return 0, None


async def wait_for_increase_cex(cex: str, before_balance: float, timeout: int = 300) -> bool:
    """Wait until CEX balance changes or timeout reached."""
    deadline = time.time() + timeout
    post_balance = before_balance

    while post_balance <= before_balance and time.time() < deadline:
        post_balance, _ = await cexs.get_cex_balance(cex)
        await asyncio.sleep(20)

    return post_balance

async def wait_for_decrease_cex(cex: str, before_balance: float, timeout: int = 300) -> bool:
    """Wait until CEX balance changes or timeout reached."""
    deadline = time.time() + timeout
    post_balance = before_balance

    while post_balance <= before_balance and time.time() < deadline:
        post_balance, _ = await cexs.get_cex_balance(cex)
        await asyncio.sleep(20)

    return post_balance > before_balance

async def wait_for_increase_cold(pk, before_balance: float, timeout: int = 300):
    deadline = time.time() + timeout
    post_balance = before_balance

    while post_balance <= before_balance and time.time() < deadline:
        post_balance = (await async_client.get_balance(pk)).value/10**9
        await asyncio.sleep(20)

    return post_balance > before_balance

async def wait_for_decrease_cold(pk, before_balance: float, timeout: int = 300):
    deadline = time.time() + timeout
    post_balance = before_balance

    while post_balance >= before_balance and time.time() < deadline:
        post_balance = (await async_client.get_balance(pk)).value/10**9
        if post_balance == 0 or post_balance < before_balance:
            return True
        await asyncio.sleep(20)

    return post_balance > before_balance

async def fund_cex(cex, cex_pk, amount, password):
    fund_balance, fund_sk = await parse_fund_balances(amount, password)
    
    if fund_sk:
        before_cex_balance, _ = await cexs.get_cex_balance(cex)
        await send_transfer(Keypair.from_base58_string(fund_sk), Pubkey.from_string(cex_pk))
        await asyncio.sleep(20)

        after_fund_balance = (await async_client.get_balance(Keypair.from_base58_string(fund_sk).pubkey())).value / 1e9

        if after_fund_balance == fund_balance:
            await send_alert(f"⚠️ {cex} balance did not update after funding")
            return False
        return True

async def withdraw_cex(cex, cex_pk, cex_balance, amount, to_fund_pk, pre_balance, password):
    retry = 0
    while retry < 2: 
        if cex == "MEXC":
            print("MEXC ", amount)

            msg = cexs.mexc_withdraw(amount, str(to_fund_pk))

            if msg == "Insufficient balance":
                print("Insufficient fund balance")
                mexc_before_balance, _ = cexs.get_mexc_balance()
                await fund_cex(cex, cex_pk, amount, password)
                increase = cexs.wait_for_increase_mexc(cex_pk, mexc_before_balance)
                if increase == False:
                    await send_alert("MEXC balance has not increased")
                    return
                cexs.mexc_withdraw(amount, str(to_fund_pk))
                await wait_for_increase_cold(to_fund_pk, pre_balance)
                return
            
            else:
                await wait_for_increase_cold(to_fund_pk, pre_balance)
                return
            
        elif cex == "Gate":
            print("Gate ", amount)

            try:
                msg = cexs.gate_withdraw(amount, str(to_fund_pk))
                await wait_for_increase_cold(to_fund_pk, pre_balance)
                return
            
            except Exception as e:
                print("Error: ",e)
                gate_before_balance, _ = cexs.get_gate_balance()
                await fund_cex(cex, cex_pk, amount, password)
                increase = cexs.wait_for_increase_gate(cex_pk, gate_before_balance)
                if increase == False:
                    await send_alert("Gate balance has not increased")
                    return
                cexs.gate_withdraw(amount, str(to_fund_pk))
                await wait_for_increase_cold(to_fund_pk, pre_balance)
                return
    return

# ---------------- Main wallet logic ----------------
async def wallet_loop(password):
    """Main loop for wallet operations."""
    await update_total_balance(password)

    cold = load_cold_wallets("MEXC")

    while cold:
        print("Starting iteration")

        cex = random.choice(CEXS_LIST)

        warm = load_warm_wallets(cex)
        cold = load_cold_wallets(cex)

        # pick target wallet
        warm_pks = {w["pk"] for w in warm}
        candidates = [w for w in cold if w["pk"] not in warm_pks]

        if not candidates:
            await asyncio.sleep(60)
            await send_alert("NO CANDIDATES")
            continue

        to_fund = random.choice(candidates)
        to_fund_sk = decrypt_secret(to_fund["sk"], password)
        to_fund_kp = Keypair.from_base58_string(to_fund_sk)
        to_fund_pk = to_fund_kp.pubkey()
        
        print("To fund pk: ", to_fund_pk)

        amount = round(random.uniform(0.1, 0.5), 6)

        # ensure CEX has enough balance
        cex_balance, cex_pk = await cexs.get_cex_balance(cex)

        pre_balance = (await async_client.get_balance(to_fund_pk)).value/10**9

        print("To fund amount: ", amount)
        # transfer type
        print("Starting withdraw from CEX")
        await withdraw_cex(cex, cex_pk, cex_balance, amount, to_fund_pk, pre_balance, password)
        # wait before checking
        sleep_time = random.randint(600, 3000)
        print("sleeping for ", sleep_time/60, " mins")
        await asyncio.sleep(sleep_time)

        post_balance = (await async_client.get_balance(to_fund_pk)).value/10**9
        if post_balance <= pre_balance:
            print("Balance did not increase after transfer first time!")
            await asyncio.sleep(60)
            post_balance = (await async_client.get_balance(to_fund_pk)).value/10**9
            if post_balance <= pre_balance:
                await send_alert("Balance did not increase after transfer!")
                continue

        with open(FUNDS_JSON, "r") as f:
            funds = json.load(f)

        target_fund = random.choice(funds)
        target_fund_sk = decrypt_secret(target_fund["sk"], password)
        fund_pk = Keypair.from_base58_string(target_fund_sk).pubkey()

        print("Fund pk: ", fund_pk)

        # get full balance of cold wallet
        cold_balance = (await async_client.get_balance(to_fund_pk)).value
        cold_balance_sol = round(cold_balance / 1e9, 6)

        if cold_balance_sol > 0:
            print("sending ", cold_balance_sol, " to funding")
            sol_to_send = await send_sol(to_fund_kp, fund_pk)
            cold_change = await wait_for_decrease_cold(to_fund_pk, cold_balance_sol)
            if cold_change:
                await send_alert(f"🔄 Sent {sol_to_send} SOL from cold → fund")
            else:
                print("No cold change")

        # ---------------- Add to warm.csv ----------------
        await add_warm_wallet(cex, to_fund)

        last_added_time = time.time()
        
        # update total balance
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


