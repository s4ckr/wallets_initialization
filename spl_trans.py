import base64
import os 
from datetime import datetime
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.message import Message  # type: ignore
from solders.transaction import Transaction  # type: ignore
from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solders.instruction import Instruction
from solders.system_program import transfer, TransferParams
from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit

from solders.system_program import (
    CreateAccountWithSeedParams,
    create_account_with_seed,
)

from spl.token.instructions import (
    CloseAccountParams,
    InitializeAccountParams,
    close_account,
    initialize_account,
)


from config import async_client

WSOL_TOKEN_ACCOUNT = Pubkey.from_string('So11111111111111111111111111111111111111112')
PUMP_AMM_PROGRAM_ID = Pubkey.from_string('pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA')
ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
TOKEN_PROGRAM_ID = Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
FEE_RECIPIENT = Pubkey.from_string('62qc2CNXwrYqQScmEdiZFFAnJR262PxWEuNQtxfafNgV')
FEE_RECIPIENT_ATA = Pubkey.from_string('94qWNrtmfn42h3ZjUZwWvK1MEo9uVmmrBPd2hpNjYDjb')
EVENT_AUTHORITY = Pubkey.from_string('GS4CU59F31iL7aR2Q8zVS8DRrcRnXX1yjQ66TqNVQnaR')
GLOBAL = Pubkey.from_string('ADyA8hdefvWN2dbGGWFotbzWxrAvLW83WG6QCVXvJKqw')
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
PROTOCOL_FEE_RECIP  = Pubkey.from_string("7VtfL8fvgNfhz17qKRMjzQEXgbdpnHHHQRh54R9jP2RJ")
TOKEN_PROGRAM_PUB   = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

def get_ts():
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]  
    return ts

async def send_transaction(client: AsyncClient, payer: Keypair, signers: list[Keypair], instructions: list[Instruction], commitment="processed") -> str | None:
    try:
        message = Message(instructions, payer.pubkey())
        
        latest_blockhash = (await client.get_latest_blockhash("processed")).value.blockhash
        # Create the transaction
        transaction = Transaction(from_keypairs=signers, message=message, recent_blockhash=latest_blockhash)
        # Sign the transaction
        transaction.sign([payer], latest_blockhash)
        # Send the transaction
        tx_signature = await client.send_raw_transaction(
            bytes(transaction),
            opts=TxOpts(
                skip_preflight=True
            ),
        )

        return tx_signature

    except Exception as e:
        print(f"[{get_ts()}] | Transaction failed: {e}")
        return None


async def close_wsol_account_and_transfer(sender_sk: str, receiver: Pubkey, wsol_token_account: str):
    sender = Keypair.from_base58_string(sender_sk)
    wsol_token_account_pubkey = wsol_token_account 

    try:
        # Only close instruction, send WSOL to receiver
        close_ix = close_account(
            CloseAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account_pubkey,
                dest=receiver,
                owner=sender.pubkey(),
            )
        )
        ix = []

        ix.append(close_ix)

        return ix
    except Exception as e:
        return {
            "status": False,
            "message": f"Transaction Failed: {str(e)}",
            "data": None
        }


async def generate_wsol_account_ix(payer: Keypair, amount_lamports):
    seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
    wsol_token_account = Pubkey.create_with_seed(payer.pubkey(), seed, TOKEN_PROGRAM_ID)

    create_wsol_account_instruction = create_account_with_seed(
        CreateAccountWithSeedParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=wsol_token_account,
            base=payer.pubkey(),
            seed=seed,
            lamports=amount_lamports,
            space=165,
            owner=TOKEN_PROGRAM_ID,
        )
    )

    init_wsol_account_instruction = initialize_account(
        InitializeAccountParams(
            program_id=TOKEN_PROGRAM_ID,
            account=wsol_token_account,
            mint=WSOL_TOKEN_ACCOUNT,
            owner=payer.pubkey(),
        )
    )

    close_wsol_account_instruction = close_account(
        CloseAccountParams(
            program_id=TOKEN_PROGRAM_ID,
            account=wsol_token_account,
            dest=payer.pubkey(),
            owner=payer.pubkey(),
        )
    )

    return wsol_token_account, [
        create_wsol_account_instruction, 
        init_wsol_account_instruction, 
        close_wsol_account_instruction
    ]

async def create_and_fund_wsol_account(sender_sk: str, sol_amount: float):
    sender = Keypair.from_base58_string(sender_sk)
    amount_lamports = int(sol_amount * 10**9)

    try:
        wsol_token_account, wsol_ix_list = await generate_wsol_account_ix(sender, amount_lamports)

        ix = []
        ix.extend(wsol_ix_list[:-1])  # Exclude close instruction

        return ix, wsol_token_account

    except Exception as e:
        return {
            "status": False,
            "message": f"Transaction Failed: {str(e)}",
            "data": None
        }
    

async def send_sol(kp: Keypair, dest: Pubkey):
    retry = 0

    while retry < 4:
        try:
            print(f"[{get_ts()}] | try to send sol from {kp.pubkey()} to {dest}")
            
            sol_balance = float(((await async_client.get_balance(kp.pubkey(), "processed")).value)/10**9)
           
            min_left = 0.000005
            sol_to_send = sol_balance - min_left
            if sol_to_send <= 0:
                print(f"[{get_ts()}] | Not enough funds for sending.")
                return False

            
            create_ix, wsol_token_account = await create_and_fund_wsol_account(str(kp), sol_to_send)

            # 2. Close WSOL account and transfer to receiver
            close_ix = await close_wsol_account_and_transfer(str(kp), dest, wsol_token_account)
            instructions = create_ix + close_ix 

            message = Message(instructions, kp.pubkey())
                
            latest_blockhash = (await async_client.get_latest_blockhash("processed")).value.blockhash
            # Create the transaction
            transaction = Transaction(from_keypairs=[kp], message=message, recent_blockhash=latest_blockhash)

            # Send the transaction
            tx_signature = await async_client.send_raw_transaction(
                bytes(transaction),
                opts=TxOpts(
                    skip_preflight=True
                ),
            )

            resp = await send_transaction(async_client, payer=kp, signers=[kp], instructions=instructions)
            
            try:
                await async_client.confirm_transaction(resp.value, "processed")
            except:
                print(f"[{get_ts()}] | unable to confirm")

            try:
                error = (await async_client.get_signature_statuses([resp.value], True)).value[0].err
            except:
                error = None

            if error:
                min_left += 0.000000001
                retry += 1
                print(f"[{get_ts()}] | has not sent sol")
                continue
            print(f"[{get_ts()}] | account {kp.pubkey()} sent {sol_to_send:.9f} SOL")
            return sol_to_send
        except Exception as e:
            print(f"[{get_ts()}] | Error occurred during transaction:", e)
            return False   


async def send_transfer(from_kp, dest_pk):
    try:
        amount = (await async_client.get_balance(from_kp.pubkey())).value

        amount = int(amount-5000-1)
        print(f"[{get_ts()}] | Sending {amount/10**9} from {from_kp.pubkey()} to {dest_pk}")

        instructions = [
            set_compute_unit_price(150),
            set_compute_unit_limit(500)
        ] 

        transfer_ix = transfer(
                TransferParams(
                    from_pubkey=from_kp.pubkey(),
                    to_pubkey=dest_pk,
                    lamports=amount
                )
            )
        
        instructions.append(transfer_ix)

        message = Message(instructions=instructions, payer=from_kp.pubkey())

        blockhash_resp = (await async_client.get_latest_blockhash()).value.blockhash
        transaction = Transaction(
            from_keypairs=[from_kp],
            message=message,
            recent_blockhash=blockhash_resp
        )
        sig = await async_client.send_raw_transaction(bytes(transaction))
        print(f"[{get_ts()}] | {sig.value}")
        return True
    except Exception as e:
        print(f"[{get_ts()}] | transfer exception", e)
        return False
    
