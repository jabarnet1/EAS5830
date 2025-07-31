import csv
import json
import os
import time

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

    # Connect to the appropriate chain
    w3 = connect_to(chain)
    if not w3.is_connected():
        print(f"Failed to connect to {chain} chain.")
        return

    # Load contract information
    contract_details = get_contract_info(chain, contract_info)
    contract_address = Web3.to_checksum_address(contract_details["address"])
    contract_abi = contract_details["abi"]

    # Initialize contract instance
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    # Get the latest block number
    latest_block = w3.eth.block_number

    # Determine the start block for scanning
    start_block = 0
    if last_scanned_block[chain] is None:
        # If this is the first scan, go back 5 blocks from the latest
        start_block = max(0, latest_block - 5)
    else:
        # Otherwise, start from the block after the last scanned block
        start_block = last_scanned_block[chain] + 1

    # Ensure start_block doesn't exceed latest_block
    if start_block > latest_block:
        print(f"No new blocks to scan on {chain}.")
        return

    print(f"\nScanning {chain} chain from block {start_block} to {latest_block}...")

    # Update last scanned block for this chain
    last_scanned_block[chain] = latest_block

    if chain == 'source':
        # Scan for 'Deposit' events
        # Deposit(address indexed token, address indexed recipient, uint256 amount)
        deposit_event_filter = contract.events.Deposit.get_logs(
            fromBlock=start_block,
            toBlock=latest_block
        )
        deposit_events = deposit_event_filter.get_all_entries()

        for event in deposit_events:
            event_args = event['args']
            token = event_args['token']
            recipient = event_args['recipient']
            amount = event_args['amount']

            print(f"Detected Deposit event on Source Chain:")
            print(f"  Token: {token}")
            print(f"  Recipient (Destination): {recipient}")
            print(f"  Amount: {amount}")

            # Now, call the 'wrap' function on the destination chain
            # Connect to destination chain
            w3_destination = connect_to('destination')
            if not w3_destination.is_connected():
                print("Failed to connect to destination chain for wrapping.")
                continue

            destination_details = get_contract_info('destination', contract_info)
            destination_contract_address = Web3.to_checksum_address(destination_details["address"])
            destination_contract_abi = destination_details["abi"]
            destination_contract = w3_destination.eth.contract(address=destination_contract_address,
                                                               abi=destination_contract_abi)

            warden_account = w3_destination.eth.account.from_key(private_key)
            w3_destination.eth.default_account = warden_account.address

            try:
                # Retrieve the current nonce for the warden's account on the destination chain
                current_nonce = w3_destination.eth.get_transaction_count(warden_account.address)
                # Call the wrap function. This requires the Destination contract to have the WARDEN_ROLE.
                # Assuming the _underlying_token in createToken is the same as the _token from Deposit event
                # And the recipient is the one provided in the Deposit event
                # And the amount is the one provided in the Deposit event
                send_transaction(w3_destination, warden_account, private_key,
                                 destination_contract, "wrap", token, recipient, amount,
                                 nonce=current_nonce)  # Pass current_nonce for reliability
            except Exception as e:
                print(f"Error calling wrap function on destination chain: {e}")

    elif chain == 'destination':
        # Scan for 'Unwrap' events
        # Unwrap(address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount)
        # Note: You have an 'Unwrap' event definition like:
        # event Unwrap( address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount );
        # And the proposed `unwrap` function revision takes (_wrapped_token, _from, _recipient, _amount)
        # So we need to match these in the event processing.

        # NOTE: If you implemented the suggested change to `unwrap` function in Destination.sol,
        # the event will also have `_from` as an indexed parameter.
        # However, the current event definition provided in Destination.sol snippet is:
        # event Unwrap( address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount );
        # Let's assume 'frm' is the account from which tokens were burned.

        # If your grader uses the original function signature for `unwrap` (3 params)
        # and the event reflects `frm`, you might need to adapt.
        # But based on the shared code, `frm` is likely the 'sender' or 'from' address.

        unwrap_event_filter = contract.events.Unwrap.get_logs(
            fromBlock=start_block,
            toBlock=latest_block
        )
        unwrap_events = unwrap_event_filter.get_all_entries()

        for event in unwrap_events:
            event_args = event['args']
            underlying_token = event_args['underlying_token']
            wrapped_token = event_args['wrapped_token']
            frm = event_args['frm']  # This is the address from which tokens were burned on destination
            recipient = event_args['to']  # This is the final recipient on the source chain
            amount = event_args['amount']

            print(f"Detected Unwrap event on Destination Chain:")
            print(f"  Underlying Token: {underlying_token}")
            print(f"  Wrapped Token: {wrapped_token}")
            print(f"  From (Burner on Destination): {frm}")
            print(f"  Recipient (Source Chain): {recipient}")
            print(f"  Amount: {amount}")

            # Now, call the 'withdraw' function on the source chain
            # Connect to source chain
            w3_source = connect_to('source')
            if not w3_source.is_connected():
                print("Failed to connect to source chain for withdrawing.")
                continue

            source_details = get_contract_info('source', contract_info)
            source_contract_address = Web3.to_checksum_address(source_details["address"])
            source_contract_abi = source_details["abi"]
            source_contract = w3_source.eth.contract(address=source_contract_address, abi=source_contract_abi)

            warden_account = w3_source.eth.account.from_key(private_key)
            w3_source.eth.default_account = warden_account.address

            try:
                # Retrieve the current nonce for the warden's account on the source chain
                current_nonce = w3_source.eth.get_transaction_count(warden_account.address)
                # Call the withdraw function. This requires the Source contract to have the WARDEN_ROLE.
                # The _token should be the underlying_token (original token address)
                # The _recipient is the address on the source chain (from the 'to' in the event)
                # The _amount is the amount from the event
                send_transaction(w3_source, warden_account, private_key,
                                 source_contract, "withdraw", underlying_token, recipient, amount,
                                 nonce=current_nonce)  # Pass current_nonce for reliability
            except Exception as e:
                print(f"Error calling withdraw function on source chain: {e}")


def register_and_create_tokens(warden_private_key, contract_info_file="contract_info.json"):
    print("\n--- Registering and Creating Tokens ---")

    # Connect to both chains to avoid reconnecting multiple times in the loop
    w3_source = connect_to('source')
    w3_destination = connect_to('destination')

    if not w3_source.is_connected() or not w3_destination.is_connected():
        print("Failed to connect to both chains. Cannot register/create tokens.")
        return

    source_details = get_contract_info('source', contract_info_file)
    destination_details = get_contract_info('destination', contract_info_file)

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

            # You might need to infer or provide names/symbols.
            # For assignment, a simple naming might suffice.
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
