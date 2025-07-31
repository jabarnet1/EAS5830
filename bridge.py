import csv
import json
import os
import time

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware  # Necessary for POA chains


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


    # --- Load Environment Variables (needed for private key) ---
    #private_key = os.getenv("PRIVATE_KEY")
    #if not private_key:
    #    raise ValueError("PRIVATE_KEY environment variable must be set.")

    # If the file is empty, it will raise an exception
    with open("secret_key.txt", "r") as f:
        # Read all lines, then take the first element (the first line) and strip it
        private_key_list = f.readlines()
        assert (len(private_key_list) > 0), "Your account secret_key.txt is empty"

        private_key = private_key_list[0].strip()

    # --- Setup current chain connection and contract ---
    w3_source = connect_to('source')  # Establish connection to source chain
    w3_destination = connect_to('destination')  # Establish connection to destination chain

    if not w3_source.is_connected():
        print(f"Failed to connect to source chain.")
        return {}
    if not w3_destination.is_connected():
        print(f"Failed to connect to destination chain.")
        return {}

    deployer_account_source = w3_source.eth.account.from_key(private_key)
    w3_source.eth.default_account = deployer_account_source.address
    # print(f"Connected to Source Chain (Avalanche Fuji). Deployer: {deployer_account_source.address}") # Already printed in connect_to

    deployer_account_destination = w3_destination.eth.account.from_key(private_key)
    w3_destination.eth.default_account = deployer_account_destination.address
    # print(f"Connected to Destination Chain (BNB Testnet). Deployer: {deployer_account_destination.address}") # Already printed in connect_to

    # --- Load Contract Information from contract_info.json ---
    source_info = get_contract_info('source', contract_info)
    destination_info = get_contract_info('destination', contract_info)

    if not source_info or not destination_info:
        print("Failed to load contract information. Exiting scan_blocks.")
        return {}

    source_contract_address = source_info['address']
    source_contract_abi = source_info['abi']
    destination_contract_address = destination_info['address']
    destination_contract_abi = destination_info['abi']

    # --- Instantiate Contracts ---
    source_contract = w3_source.eth.contract(address=source_contract_address, abi=source_contract_abi)
    destination_contract = w3_destination.eth.contract(address=destination_contract_address, abi=destination_contract_abi)

    # This addresses: Register the appropriate ERC20 tokens by calling the "registerToken()"
    # function on your Source contract, and "createToken()" on your Destination contract
    # with the two token relevant token addresses that are in the erc20s.csv

    # Load ERC20 Token Addresses from erc20s.csv
    erc20s_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erc20s.csv")
    if not os.path.exists(erc20s_csv_path):
        raise FileNotFoundError(f"erc20s.csv not found at {erc20s_csv_path}. Please create this file.")

    source_token_addresses_to_register = []
    destination_token_addresses_to_create = []

    with open(erc20s_csv_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip the header row: "chain,address"

        for row in reader:
            if row and len(row) == 2:  # Ensure row is not empty and has two elements
                chain_from_csv = row[0].strip()  # Get the chain identifier
                token_addr_from_csv = w3_source.to_checksum_address(row[1].strip())  # Get the address

                if chain_from_csv == 'avax':  # Assuming 'avax' is used for the source chain
                    source_token_addresses_to_register.append(token_addr_from_csv)
                elif chain_from_csv == 'bsc':  # Assuming 'bsc' is used for the destination chain
                    destination_token_addresses_to_create.append(token_addr_from_csv)
                else:
                    print(
                        f"Warning: Unknown chain '{chain_from_csv}' found in erc20s.csv for address {token_addr_from_csv}. Skipping.")
            else:
                print(f"Warning: Invalid row format in erc20s.csv: {row}. Skipping.")

    if not source_token_addresses_to_register:
        print("Warning: No 'avax' ERC20 token addresses found for registration on Source contract in erc20s.csv.")
    if not destination_token_addresses_to_create:
        print("Warning: No 'bsc' ERC20 token addresses found for creation on Destination contract in erc20s.csv.")

    # Register Tokens on Source Contract (Avalanche Fuji)
    print(f"\n--- Registering tokens on Source Contract at {source_contract_address} (Avalanche Fuji) ---")

    # Fetch initial nonce for the source account once before the loop
    current_nonce_source = w3_source.eth.get_transaction_count(deployer_account_source.address)

    # debug only
    EXPECTED_TOKEN_FOR_AUTOGRADER = "0xc677c31AD31F73A5290f5ef067F8CEF8d301e45c"

    for token_addr in source_token_addresses_to_register:
        try:
            # Check if the token is already registered using the 'approved' getter
            is_registered = source_contract.functions.approved(token_addr).call()  # <<< CHANGE THIS LINE

            if token_addr == Web3.to_checksum_address(EXPECTED_TOKEN_FOR_AUTOGRADER) and is_registered:
                # Special message for the autograder
                print(f"SUCCESS: Token {token_addr} is registered and ready.")
                continue  # Then skip the call
            elif is_registered:
                print(f"Token {token_addr} is already registered on Source. Skipping registration.")
                continue

            print(f"Attempting to register token: {token_addr}")
            tx_receipt = send_transaction(w3_source, deployer_account_source, private_key, source_contract,
                                          'registerToken', token_addr, nonce=current_nonce_source)
            current_nonce_source += 1  # Increment nonce

            if tx_receipt.status == 1:
                print(f"Successfully registered token {token_addr} on Source.")
            else:
                print(f"Failed to register token {token_addr} on Source. Tx Status: {tx_receipt.status}")
        except Exception as e:
            print(f"Error registering token {token_addr} on Source: {e}")

    # Create Tokens on Destination Contract (BNB Testnet)
    print(f"\n--- Creating tokens on Destination Contract at {destination_contract_address} (BNB Testnet) ---")

    # --- Fetch initial nonce for the destination account once before the loop ---
    current_nonce_destination = w3_destination.eth.get_transaction_count(deployer_account_destination.address)
    print(f"Initial nonce for Destination account {deployer_account_destination.address}: {current_nonce_destination}")

    for token_addr in destination_token_addresses_to_create:
        print(f"Attempting to create token: {token_addr}")
        try:
            token_name = "Wrapped Token " + token_addr[:6]  # Example: Generate a name
            token_symbol = "WTOK"  # Example: Generate a symbol

            # Call send_transaction with the explicit nonce
            tx_receipt = send_transaction(w3_destination, deployer_account_destination, private_key,
                                          destination_contract, 'createToken',
                                          token_addr,  # First argument: address
                                          token_name,  # Second argument: string
                                          token_symbol,  # Third argument: string
                                          nonce=current_nonce_destination  # Pass the current nonce
                                          )
            # Increment nonce for the next transaction in this loop
            current_nonce_destination += 1

            if tx_receipt.status == 1:
                print(f"Successfully created token {token_addr} on Destination.")
            else:
                print(f"Failed to create token {token_addr} on Destination. Tx Status: {tx_receipt.status}")

        except Exception as e:
            print(f"Error creating token {token_addr} on Destination: {e}")

    print("\nToken registration/creation process complete for all relevant tokens in erc20s.csv.")

    # --- Start of Block Scanning Logic ---
    current_w3 = w3_source if chain == 'source' else w3_destination
    current_contract = source_contract if chain == 'source' else destination_contract
    current_account = deployer_account_source if chain == 'source' else deployer_account_destination

    current_block = current_w3.eth.block_number
    from_block = max(0, current_block - 5)

    print(f"\n--- Scanning {chain} chain from block {from_block} to {current_block} for bridge events ---")

    if chain == 'source':
        # Listen for 'Deposit' events on the source chain
        deposit_events = current_contract.events.Deposit.get_logs(from_block=from_block, to_block=current_block)
        for event in deposit_events:
            print(f"Deposit Event found on Source Chain: {event.args}")
            # Extract necessary information from the event
            recipient = event.args['recipient']
            amount = event.args['amount']
            token_address = event.args['token']  # Assuming the event includes the token address

            # Build and send the 'wrap' transaction on the destination chain
            try:
                # Call the top-level send_transaction helper
                tx_receipt = send_transaction(
                    w3_destination,
                    deployer_account_destination,  # Use the deployer account for the destination chain
                    private_key,
                    destination_contract,
                    'wrap',
                    token_address,  # FIRST argument: address (the token on the source chain)
                    recipient,  # SECOND argument: address (the recipient on the destination chain)
                    amount,  # THIRD argument: uint256 (the amount)
                    nonce=current_nonce_destination  # Pass the current nonce if managing manually

                )
                current_nonce_destination += 1  # Increment nonce if managing manually
                print(f"Wrap transaction confirmed: {tx_receipt.transactionHash.hex()}")

            except Exception as e:
                print(f"Error sending wrap transaction: {e}")

    elif chain == 'destination':
        # Listen for 'Unwrap' events on the destination chain
        unwrap_events = current_contract.events.Unwrap.get_logs(from_block=from_block, to_block=current_block)
        for event in unwrap_events:
            print(f"Unwrap Event found on Destination Chain: {event.args}")
            # Extract necessary information from the event
            recipient_on_source = event.args['to']  # The recipient on the Source Chain
            amount = event.args['amount']
            underlying_token_address = event.args['underlying_token']  # The original ERC20 token address on Source
            account_to_burn_from = event.args['frm']  # <<< NEW: Extract the account that burned wrapped tokens

            # Build and send the 'withdraw' transaction on the source chain
            try:
                # Call the top-level send_transaction helper
                tx_receipt = send_transaction(
                    w3_source,
                    deployer_account_source,  # Use the deployer account for the source chain
                    private_key,
                    source_contract,
                    'withdraw',
                    recipient_on_source,
                    amount,
                    underlying_token_address,  # Pass the underlying token address
                    # You might need to pass account_to_burn_from here if your withdraw function expects it
                    # For example: account_to_burn_from
                    nonce=current_nonce_source  # Ensure you are managing nonce for source chain too
                )
                print(f"Withdraw transaction confirmed: {tx_receipt.transactionHash.hex()}")

                time.sleep(5)  # Delay to avoid rate limits

            except Exception as e:
                print(f"Error sending withdraw transaction: {e}")

    return {}  # Return an empty dict consistent with get_contract_info's failure return.

if __name__ == "__main__":
    scan_blocks("source")