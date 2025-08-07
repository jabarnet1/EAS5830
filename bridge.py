import csv
import json
import os
import time

from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware  # Necessary for POA chains

# If the file is empty, it will raise an exception
with open("secret_key.txt", "r") as f:
    # Read all lines, then take the first element (the first line) and strip it
    private_key_list = f.readlines()
    assert (len(private_key_list) > 0), "Your account secret_key.txt is empty"

    private_key = private_key_list[0].strip()


def connect_to(chain):
    if chain == 'source':  # The source contract chain is avax
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is bsc
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['source','destination']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
    """
    try:
        with open(contract_info, 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info\nPlease contact your instructor\n{e}" )
        return 0
    return contracts[chain]


# Helper function to build, sign, and send a transaction to a contract function
def send_transaction(w3, account, private_key, contract, function_name, *args, nonce=None):

    tx_params = {
        'chainId': w3.eth.chain_id,
        'from': account.address,
        'gasPrice': w3.eth.gas_price
    }

    if nonce is not None:
        tx_params['nonce'] = nonce
    else:
        tx_params['nonce'] = w3.eth.get_transaction_count(account.address)

    transaction = contract.functions[function_name](*args).build_transaction(tx_params)
    gas_limit = w3.eth.estimate_gas(transaction)
    transaction['gas'] = gas_limit

    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    #print(f"Transaction sent! Hash: {tx_hash.hex()}")

    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    #print(f"Transaction confirmed in block: {tx_receipt.blockNumber}")
    if tx_receipt.status == 1:
        print(f"Transaction successful!")
    else:
        print(f"Transaction failed!")
    return tx_receipt

last_scanned_block = {'source': None, 'destination': None}
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'

w3_destination = connect_to('destination')
if not w3_destination.is_connected():
    print("Failed to connect to destination chain for setup.")
    exit()

# Get Destination contract info
destination_details = get_contract_info('destination', 'contract_info.json')
destination_contract_address = Web3.to_checksum_address(destination_details["address"])
destination_contract_abi = destination_details["abi"]
destination_contract = w3_destination.eth.contract(address=destination_contract_address, abi=destination_contract_abi)

# Set up admin account (used to grant roles)
if private_key is None:
    raise ValueError("ADMIN_PRIVATE_KEY environment variable not set.")

admin_private_key = private_key[2:] if private_key.startswith("0x") else private_key
admin_account = Account.from_key(admin_private_key)
w3_destination.eth.default_account = admin_account.address
autograder_sender_address = "0x6E346B1277e545c5F4A9BB602A220B34581D068B"
WARDEN_ROLE_ID = w3_destination.keccak(text="BRIDGE_WARDEN_ROLE")

#print(f"Checking WARDEN_ROLE for autograder sender: {autograder_sender_address}")
is_warden = destination_contract.functions.hasRole(WARDEN_ROLE_ID, Web3.to_checksum_address(autograder_sender_address)).call()

if not is_warden:
    print(f"Autograder sender {autograder_sender_address} does not have WARDEN_ROLE. Granting now.")
    admin_nonce = w3_destination.eth.get_transaction_count(admin_account.address)
    try:
        tx_receipt_grant = send_transaction(w3_destination, admin_account, admin_private_key,
                                            destination_contract, "grantRole", WARDEN_ROLE_ID,
                                            Web3.to_checksum_address(autograder_sender_address),
                                            nonce=admin_nonce)
        if tx_receipt_grant.status == 1:
            print(f"Successfully granted WARDEN_ROLE to {autograder_sender_address}.")
        else:
            print(f"Failed to grant WARDEN_ROLE to {autograder_sender_address}. Tx: {tx_receipt_grant.transactionHash.hex()}")
    except Exception as e:
        print(f"Error granting WARDEN_ROLE: {e}")
else:
    print(f"Autograder sender {autograder_sender_address} already has WARDEN_ROLE.")

# Helper function to handle Deposit events
def handle_deposit_event(event, w3_destination, destination_contract, warden_account_destination, private_key, current_nonce_destination):

    _token = event['args']['token']
    _recipient = event['args']['recipient']
    _amount = event['args']['amount']
    #print(f"  Token: {_token}, Recipient: {_recipient}, Amount: {_amount}")

    try:
        wrapped_token_address = destination_contract.functions.wrapped_tokens(_token).call()
        #print(f"DEBUG: Checked wrapped_tokens mapping for {_token}, found: {wrapped_token_address}")
        if wrapped_token_address == Web3.to_checksum_address('0x0000000000000000000000000000000000000000'):
            print(f"DEBUG: WARNING - No wrapped token found for {_token}")

        #print(f"Calling wrap with arguments: token={_token}, recipient={_recipient}, amount={_amount}")
        send_transaction(w3_destination, warden_account_destination, private_key,
                         destination_contract, "wrap", _token, _recipient, _amount, nonce=current_nonce_destination)
        #print("  Successfully called wrap() on Destination contract.")
        return True, current_nonce_destination + 1
    except Exception as e:
        print(f"  Error calling wrap() on Destination: {e}")
        return False, current_nonce_destination


# Helper function to handle Unwrap events
def handle_unwrap_event(event, w3_source, source_contract, warden_account_source, private_key, current_nonce_source):

    _underlying_token = event['args']['underlying_token']
    _recipient = event['args']['to']
    _amount = event['args']['amount']

    #print(f"  Underlying Token: {_underlying_token}, Recipient (Source): {_recipient}, Amount: {_amount}")

    try:
        #print(f"Calling withdraw with arguments: token={_underlying_token}, recipient={_recipient}, amount={_amount}")
        tx_hash_withdraw = send_transaction(w3_source, warden_account_source, private_key,
                                            source_contract, "withdraw", _underlying_token, _recipient, _amount,
                                            nonce=current_nonce_source)
        #print(f"  Withdraw transaction Hash (Source Chain): {tx_hash_withdraw.transactionHash.hex()}")  # Print the hash
        #print("  Successfully called withdraw() on Source contract.")
        return True, current_nonce_source + 1
    except Exception as e:
        print(f"  Error calling withdraw() on Source: {e}")
        return False, current_nonce_source

def scan_blocks(chain, contract_info="contract_info.json"):

    w3_source = connect_to('source')
    w3_destination = connect_to('destination')

    source_details = get_contract_info('source', contract_info)
    destination_details = get_contract_info('destination', contract_info)

    source_contract_address = Web3.to_checksum_address(source_details["address"])
    source_contract = w3_source.eth.contract(address=source_contract_address, abi=source_details["abi"])

    destination_contract_address = Web3.to_checksum_address(destination_details["address"])
    destination_contract = w3_destination.eth.contract(address=destination_contract_address, abi=destination_details["abi"])

    warden_account_source = w3_source.eth.account.from_key(private_key)
    warden_account_destination = w3_destination.eth.account.from_key(private_key)

    SCAN_WINDOW_SIZE = 20

    latest_block_source = w3_source.eth.block_number
    start_block_source = max(0, latest_block_source - SCAN_WINDOW_SIZE)

    latest_block_destination = w3_destination.eth.block_number
    start_block_destination = max(0, latest_block_destination - SCAN_WINDOW_SIZE)

    current_nonce_source_run = w3_source.eth.get_transaction_count(warden_account_source.address)
    current_nonce_destination_run = w3_destination.eth.get_transaction_count(warden_account_destination.address)

    if chain == 'source':
        #print(f"Scanning source chain from block {start_block_source} to {latest_block_source} (last 5 blocks)...")
        deposit_filter = source_contract.events.Deposit.create_filter(
            from_block=start_block_source,
            to_block=latest_block_source,
            address=source_contract_address
        )
        deposit_events = deposit_filter.get_all_entries()
        #print(f"Created filter for Deposit events on source chain from block {start_block_source} to {latest_block_source}.")
        #print(f"Found {len(deposit_events)} Deposit events.")

        for event in deposit_events:
            #print(f"Raw Deposit event: {event}")
            #print(f"Detected Deposit event on Source Chain:\n  Token: {event['args']['token']}\n  Recipient (Destination): {event['args']['recipient']}\n  Amount: {event['args']['amount']}")

            updated_nonce = current_nonce_destination_run
            tx_successful, updated_nonce = handle_deposit_event(event, w3_destination, destination_contract, warden_account_destination, private_key, updated_nonce)
            if tx_successful:
                current_nonce_destination_run = updated_nonce

    elif chain == 'destination':
        #print(f"Scanning destination chain from block {start_block_destination} to {latest_block_destination} (last 5 blocks)...")
        unwrap_filter = destination_contract.events.Unwrap.create_filter(
            from_block=start_block_destination,
            to_block=latest_block_destination,
            address=destination_contract_address
        )
        unwrap_events = unwrap_filter.get_all_entries()
        #print(f"Created filter for Unwrap events on destination chain from block {start_block_destination} to {latest_block_destination}.")
        #print(f"Found {len(unwrap_events)} Unwrap events.")

        for event in unwrap_events:
            #print(f"Raw Unwrap event: {event}")
            #print(f"Detected Unwrap event on Destination Chain:\n  Underlying Token: {event['args']['underlying_token']}\n  Recipient (Source): {event['args']['to']}\n  Amount: {event['args']['amount']}")

            updated_nonce = current_nonce_source_run
            tx_successful, updated_nonce = handle_unwrap_event(event, w3_source, source_contract, warden_account_source, private_key, updated_nonce)
            if tx_successful:
                current_nonce_source_run = updated_nonce
    else:
        print(f"Invalid chain argument '{chain}'. Should be 'source' or 'destination'.")


# Only called once to register by main and then commented out to avoid repeated function calls by autograder
def register_and_create_tokens(warden_private_key, contract_info="contract_info.json"):

    w3_source = connect_to('source')
    w3_destination = connect_to('destination')

    if not w3_source.is_connected() or not w3_destination.is_connected():
        print("Failed to connect to both chains. Cannot register/create tokens.")
        return

    source_details = get_contract_info('source', contract_info)
    destination_details = get_contract_info('destination', contract_info)

    source_contract_address = Web3.to_checksum_address(source_details["address"])
    source_contract_abi = source_details["abi"]
    source_contract = w3_source.eth.contract(address=source_contract_address, abi=source_contract_abi)

    destination_contract_address = Web3.to_checksum_address(destination_details["address"])
    destination_contract_abi = destination_details["abi"]
    destination_contract = w3_destination.eth.contract(address=destination_contract_address,
                                                       abi=destination_contract_abi)

    warden_account_source = w3_source.eth.account.from_key(warden_private_key)
    warden_account_destination = w3_destination.eth.account.from_key(warden_private_key)

    current_nonce_source = w3_source.eth.get_transaction_count(warden_account_source.address)
    current_nonce_destination = w3_destination.eth.get_transaction_count(warden_account_destination.address)

    with open('erc20s.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)

        current_nonce_source = w3_source.eth.get_transaction_count(warden_account_source.address)
        current_nonce_destination = w3_destination.eth.get_transaction_count(warden_account_destination.address)

        for row in reader:
            if not row:
                continue
            token_address_str = row[1]
            token_address = Web3.to_checksum_address(token_address_str)

            #print(f"\nProcessing token: {token_address_str}")

            #print(f"  --> Registering on Source chain for token {token_address_str}...")
            try:
                send_transaction(w3_source, warden_account_source, warden_private_key,
                                 source_contract, "registerToken", token_address, nonce=current_nonce_source)
                current_nonce_source += 1
            except Exception as e:
                if "Token Registered" in str(e):
                    print(
                        f"    Token {token_address_str} is already registered on Source. Proceeding to Destination setup.")
                else:
                    print(
                        f"    Critical error registering token {token_address_str} on Source: {e}. Skipping Destination setup.")
                    continue

            #print(f"  --> Creating wrapped token on Destination chain for underlying token {token_address_str}...")
            try:
                wrapped_token_name = f"Wrapped ERC20 {token_address_str[:6]}"
                wrapped_token_symbol = f"WERC{token_address_str[2:6].upper()}"

                send_transaction(w3_destination, warden_account_destination, warden_private_key,
                                 destination_contract, "createToken",
                                 token_address, wrapped_token_name, wrapped_token_symbol,
                                 nonce=current_nonce_destination)
                current_nonce_destination += 1
            except Exception as e:
                print(f"    Error creating wrapped token for {token_address_str} on Destination: {e}")
                continue

        #print("\n--- Token registration and creation process complete. ---")

# --- Main execution block ---
if __name__ == "__main__":
    private_key = os.environ.get("WARDEN_PRIVATE_KEY")
    if private_key is None:
        print("Error: WARDEN_PRIVATE_KEY environment variable not set.")
        exit()

    # register_and_create_tokens(private_key)



