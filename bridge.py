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


# ... other imports ...

# connect_to and get_contract_info functions here

# Helper function - send_transaction function
def send_transaction(w3, account, private_key, contract, function_name, *args, nonce=None): # ADDED 'nonce=None' here
    """
    Helper function to build, sign, and send a transaction to a contract function.
    """
    print(f"\n--- Calling {function_name} on {contract.address} ---")

    tx_params = {
        'chainId': w3.eth.chain_id,
        'from': account.address,
        'gasPrice': w3.eth.gas_price
    }

    if nonce is not None: # Use provided nonce if available
        tx_params['nonce'] = nonce
    else: # Otherwise, fetch it
        tx_params['nonce'] = w3.eth.get_transaction_count(account.address)

    # Build the transaction
    transaction = contract.functions[function_name](*args).build_transaction(tx_params)

    # Estimate gas (optional but recommended)
    gas_limit = w3.eth.estimate_gas(transaction)
    transaction['gas'] = gas_limit

    # Sign the transaction
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)

    # Send the transaction
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Transaction sent! Hash: {tx_hash.hex()}")

    # Wait for the transaction to be mined
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {tx_receipt.blockNumber}")
    if tx_receipt.status == 1:
        print(f"Transaction successful!")
    else:
        print(f"Transaction failed!")
    return tx_receipt


last_scanned_block = {'source': None, 'destination': None}
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'

# ====================================================================
# Initial Setup and Role Granting Section
# This runs once when bridge.py starts, before the main scanning loop
# ====================================================================

print("\n--- Initial Bridge Setup ---")

# Connect to the destination chain first
w3_destination = connect_to('destination')
if not w3_destination.is_connected():
    print("Failed to connect to destination chain for setup.")
    # Exit or raise an error, cannot proceed without connection
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
w3_destination.eth.default_account = admin_account.address # Set default for admin for convenience


# --- Role Granting Logic ---
autograder_sender_address = "0x6E346B1277e545c5F4A9BB602A220B34581D068B" # From previous autograder output
WARDEN_ROLE_ID = w3_destination.keccak(text="BRIDGE_WARDEN_ROLE")

print(f"Checking WARDEN_ROLE for autograder sender: {autograder_sender_address}")
is_warden = destination_contract.functions.hasRole(WARDEN_ROLE_ID, Web3.to_checksum_address(autograder_sender_address)).call()

if not is_warden:
    print(f"Autograder sender {autograder_sender_address} does not have WARDEN_ROLE. Granting now...")
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
            # Decide if you want to proceed if role granting fails
    except Exception as e:
        print(f"Error granting WARDEN_ROLE: {e}")
else:
    print(f"Autograder sender {autograder_sender_address} already has WARDEN_ROLE.")

print("--- Initial Bridge Setup Complete ---")



def scan_blocks(chain, contract_info="contract_info.json"):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    # This is different from Bridge IV where chain was "avax" or "bsc"
    if chain not in ['source','destination']:
        print( f"Invalid chain: {chain}" )
        return 0
    
        #YOUR CODE HERE

    w3 = connect_to(chain)
    if not w3.is_connected():
        print(f"Failed to connect to {chain} chain.")
        return

    contract_details = get_contract_info(chain, contract_info)
    contract_address = Web3.to_checksum_address(contract_details["address"])
    contract_abi = contract_details["abi"]
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    latest_block = w3.eth.block_number
    start_block = 0

    if last_scanned_block[chain] is None:
        start_block = max(0, latest_block - 5)
    else:
        start_block = last_scanned_block[chain] + 1


    if start_block > latest_block:
        print(f"No new blocks to scan on {chain}.")
        return
    print(f"\nScanning {chain} chain from block {start_block} to {latest_block}...")
    last_scanned_block[chain] = latest_block

    if chain == 'source':
        #deposit_events = contract.events.Deposit.get_logs(
        #    from_block=start_block,
        #    to_block=latest_block
        #)

        deposit_filter = contract.events.Deposit.create_filter(
            from_block=start_block,
            to_block=latest_block  # Or use 'latest' if you want it to automatically track up to the current block
        )

        if deposit_filter:
            print(f"Created filter for Deposit events on source chain from block {start_block} to {latest_block}.")
            deposit_events = deposit_filter.get_all_entries()
            # You can also use get_new_entries() to get only newly emitted events since the last call to this function

            if deposit_events:  # Only fetch nonce if there are events to process
                w3_destination = connect_to('destination')
                if not w3_destination.is_connected():
                    print("Failed to connect to destination chain for wrapping.")
                    return  # Exit or handle error

                destination_details = get_contract_info('destination', contract_info)
                destination_contract_address = Web3.to_checksum_address(destination_details["address"])
                destination_contract_abi = destination_details["abi"]
                destination_contract = w3_destination.eth.contract(address=destination_contract_address,
                                                                   abi=destination_contract_abi)

                warden_account = w3_destination.eth.account.from_key(private_key)
                w3_destination.eth.default_account = warden_account.address

                # --- START NONCE FIX ---
                # Get the current nonce ONCE for this batch of transactions
                current_nonce_destination = w3_destination.eth.get_transaction_count(warden_account.address)
                # --- END NONCE FIX ---

                for event in deposit_events:
                    print(f"Raw Deposit event: {event}")
                    event_args = event['args']
                    token = event_args['token']
                    recipient = event_args['recipient']
                    amount = event_args['amount']
                    print(f"Extracted amount from Deposit event: {amount}")

                    print(f"Detected Deposit event on Source Chain:")
                    print(f"  Token: {token}")
                    print(f"  Recipient (Destination): {recipient}")
                    print(f"  Amount: {amount}")

                    try:
                        # Call the public getter for the wrapped_tokens mapping
                        # The `token` variable here refers to the `_underlying_token` from the Deposit event
                        wrapped_token_address = destination_contract.functions.wrapped_tokens(token).call()
                        print(f"DEBUG: Checked wrapped_tokens mapping for {token}, found: {wrapped_token_address}")

                        if wrapped_token_address == ZERO_ADDRESS:  # Assuming ZERO_ADDRESS is defined as '0x0...'
                            print(
                                f"DEBUG: Wrapped token not found for underlying token {token}. Attempting to create new wrapped token...")

                            wrapped_token_name = f"Wrapped {token[:6]}..."  # Placeholder, adjust as needed
                            wrapped_token_symbol = f"W{token[:4]}"  # Placeholder, adjust as needed

                            tx_receipt_create = send_transaction(w3_destination, warden_account, private_key,
                                                                 destination_contract, "createToken", token,
                                                                 wrapped_token_name, wrapped_token_symbol,
                                                                 nonce=current_nonce_destination)
                            current_nonce_destination += 1  # Increment nonce for the createToken transaction

                            if tx_receipt_create.status == 1:
                                print(
                                    f"DEBUG: Successfully created wrapped token for {token} (Tx Hash: {tx_receipt_create.transactionHash.hex()})")

                                wrapped_token_address = destination_contract.functions.wrapped_tokens(token).call()
                                print(f"DEBUG: Re-fetched wrapped token address after creation: {wrapped_token_address}")
                            else:
                                print(
                                    f"ERROR: Failed to create wrapped token for {token} (Tx Hash: {tx_receipt_create.transactionHash.hex()})")
                                # Decide if you want to continue processing other events or stop
                                continue  # Skip this deposit and try the next one if token creation failed

                    except Exception as e:
                        print(f"ERROR: Exception during wrapped token check/creation for {token}: {e}")
                        # Handle the error appropriately, perhaps log it and continue
                        continue  # Skip this deposit and try the next one

                    try:
                        print(f"Calling wrap with arguments: token={token}, recipient={recipient}, amount={amount}")
                        send_transaction(w3_destination, warden_account, private_key,
                                         destination_contract, "wrap", token, recipient, amount,
                                         nonce=current_nonce_destination)
                        current_nonce_destination += 1
                    except Exception as e:
                        print(f"Error calling wrap function on destination chain: {e}")

    elif chain == 'destination':
        max_retries = 5
        base_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                # Adjust block range here - e.g., scan 50 blocks at a time
                current_start_block = start_block
                current_end_block = min(latest_block, start_block + 49)  # Adjust 49 based on desired range size

                # Create the filter for Unwrap events
                unwrap_filter = contract.events.Unwrap.create_filter(
                    from_block=current_start_block,
                    to_block=current_end_block
                )

                #unwrap_events = contract.events.Unwrap.get_logs(
                #    from_block=current_start_block,
                #    to_block=current_end_block
                #)
                print(f"\nScanning {chain} chain from block {current_start_block} to {current_end_block}...")
                last_scanned_block[chain] = current_end_block  # Update last scanned block after successful retrieval

                # Get all matching entries from the filter
                unwrap_events = unwrap_filter.get_all_entries()

                print(f"\nScanning {chain} chain from block {current_start_block} to {current_end_block}...")
                last_scanned_block[chain] = current_end_block  # Update last scanned block after successful retrieval

                # Successfully retrieved logs, break retry loop
                break

            except Exception as e:
                # Assuming the error message will be like {'code': -32005, 'message': 'limit exceeded'}
                if isinstance(e.args[0], dict) and e.args[0].get('code') == -32005:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(
                        f"RPC rate limit exceeded. Retrying in {delay} seconds (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                else:
                    print(f"ERROR: running scan_blocks('{chain}'): {e}")
                    break  # Break on other

        else:
            print(f"ERROR: Failed to scan blocks on {chain} after {max_retries} retries due to RPC limit.")
            return  # Exit if retries fail

        # Process events
        if unwrap_events:  # Only fetch nonce if there are events to process
            w3_source = connect_to('source')
            if not w3_source.is_connected():
                print("Failed to connect to source chain for withdrawing.")
                return  # Exit or handle error

            source_details = get_contract_info('source', contract_info)
            source_contract_address = Web3.to_checksum_address(source_details["address"])
            source_contract_abi = source_details["abi"]
            source_contract = w3_source.eth.contract(address=source_contract_address, abi=source_contract_abi)

            warden_account = w3_source.eth.account.from_key(private_key)
            w3_source.eth.default_account = warden_account.address

            # --- START NONCE FIX ---
            # Get the current nonce ONCE for this batch of transactions
            current_nonce_source = w3_source.eth.get_transaction_count(warden_account.address)
            # --- END NONCE FIX ---

            # --- START NEW UNWRAP CALL ---
            for event in unwrap_events:
                event_args = event['args']
                underlying_token = event_args['underlying_token']
                wrapped_token = event_args['wrapped_token']
                frm = event_args['frm']  # This is the _from parameter for the new unwrap
                recipient = event_args['to']
                amount = event_args['amount']

                print(f"Detected Unwrap event on Destination Chain:")
                print(f"  Underlying Token: {underlying_token}")
                print(f"  Wrapped Token: {wrapped_token}")
                print(f"  From (Burner on Destination): {frm}")
                print(f"  Recipient (Source Chain): {recipient}")
                print(f"  Amount: {amount}")

                try:
                    send_transaction(w3_source, warden_account, private_key,
                                     source_contract, "withdraw", underlying_token, recipient, amount,
                                     nonce=current_nonce_source)
                    current_nonce_source += 1
                except Exception as e:
                    print(f"Error calling withdraw function on source chain: {e}")
            # --- END NEW UNWRAP CALL ---

                # Successfully retrieved logs, break retry loop
                break

            else:
                print(f"ERROR: Failed to scan blocks on {chain} after {max_retries} retries due to RPC limit.")



def register_and_create_tokens(warden_private_key, contract_info="contract_info.json"):
    print("\n--- Registering and Creating Tokens ---")

    # Connect to both chains to avoid reconnecting multiple times in the loop
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

    # Assumes your erc20s.csv has a header row and token addresses in the first column
    with open('erc20s.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row

        for row in reader:
            if not row:  # Skip empty rows if any
                continue
            chain_name = row[0]  # Gets 'avax' or 'bsc'
            token_address_str = row[1]  # Gets the token address string
            token_address = Web3.to_checksum_address(token_address_str)

            wrapped_token_name = f"Wrapped ERC20 {token_address_str[:6]}..."
            wrapped_token_symbol = f"WERC{token_address_str[2:6].upper()}"

            print(f"\nProcessing token: {token_address_str}")

            # Call registerToken on Source
            try:
                # Ensure the nonce is correctly managed for sequential transactions
                nonce_source = w3_source.eth.get_transaction_count(warden_account_source.address)
                send_transaction(w3_source, warden_account_source, warden_private_key,
                                 source_contract, "registerToken", token_address, nonce=nonce_source)
            except Exception as e:
                print(f"Error registering token {token_address_str} on Source: {e}")

            # Call createToken on Destination
            try:
                nonce_destination = w3_destination.eth.get_transaction_count(warden_account_destination.address)
                send_transaction(w3_destination, warden_account_destination, warden_private_key,
                                 destination_contract, "createToken", token_address, wrapped_token_name,
                                 wrapped_token_symbol, nonce=nonce_destination)
            except Exception as e:
                print(f"Error creating wrapped token for {token_address_str} on Destination: {e}")


# ... (main_loop and if __name__ == "__main__": block) ...

if __name__ == "__main__":
    if private_key is None:
        print("Error: WARDEN_PRIVATE_KEY environment variable not set.")
        exit()

    # Call the registration function before starting the main listener loop
    #register_and_create_tokens(private_key)
