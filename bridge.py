from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd


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
        contract_details = get_contract_info(chain, contract_info)
        contract_address = Web3.toChecksumAddress(contract_details['address'])
        contract_abi = contract_details['abi']
        contract = w3.eth.contract(address=contract_address, abi=contract_abi)

        current_block = w3.eth.block_number
        # Scan the last 5 blocks
        from_block = max(0, current_block - 5)

        print(f"Scanning {chain} chain from block {from_block} to {current_block}...")

        if chain == 'source':
            # Listen for 'Deposit' events on the source chain
            deposit_events = contract.events.Deposit.getLogs(fromBlock=from_block, toBlock=current_block)
            for event in deposit_events:
                print(f"Deposit Event found on Source Chain: {event.args}")
                # Extract necessary information from the event
                recipient = event.args['recipient']
                amount = event.args['amount']
                token_address = event.args['token']  # Assuming the event includes the token address

                # Connect to the destination chain (BNB Testnet)
                w3_destination = connect_to('destination')
                destination_contract_details = get_contract_info('destination', contract_info)
                destination_contract_address = Web3.toChecksumAddress(destination_contract_details['address'])
                destination_contract_abi = destination_contract_details['abi']
                destination_contract = w3_destination.eth.contract(address=destination_contract_address,
                                                                   abi=destination_contract_abi)

                # Build and send the 'wrap' transaction on the destination chain
                try:
                    # The wardens signing key is needed to sign the transaction
                    account = w3_destination.eth.account.from_key(WARDEN_PRIVATE_KEY)
                    w3_destination.eth.default_account = account.address

                    # Build the transaction
                    nonce = w3_destination.eth.get_transaction_count(account.address)
                    # The wrap function will need to be called with the appropriate arguments.
                    # In a real scenario, you'd verify the message signature from the source chain
                    # and use that to authorize the wrap on the destination.
                    # For this assignment, we're assuming the listener acts as the trusted warden.
                    # You'll likely need to pass the source contract's token address and the recipient/amount
                    # based on your contract's 'wrap' function signature.
                    # Example:
                    tx_hash = destination_contract.functions.wrap(
                        recipient,
                        amount,
                        token_address  # The ERC20 token address on the source chain
                    ).transact({
                        'from': account.address,
                        'nonce': nonce,
                        'gas': 2000000,  # Adjust gas limit as needed
                        'gasPrice': w3_destination.eth.gas_price
                    })
                    print(f"Wrap transaction sent on Destination Chain: {w3_destination.toHex(tx_hash)}")
                    w3_destination.eth.wait_for_transaction_receipt(tx_hash)
                    print(f"Wrap transaction confirmed: {w3_destination.toHex(tx_hash)}")
                except Exception as e:
                    print(f"Error sending wrap transaction: {e}")

        elif chain == 'destination':
            # Listen for 'Unwrap' events on the destination chain
            unwrap_events = contract.events.Unwrap.getLogs(fromBlock=from_block, toBlock=current_block)
            for event in unwrap_events:
                print(f"Unwrap Event found on Destination Chain: {event.args}")
                # Extract necessary information from the event
                recipient = event.args['recipient']
                amount = event.args['amount']
                token_address = event.args['token']  # The destination chain's token address

                # Connect to the source chain (AVAX Testnet)
                w3_source = connect_to('source')
                source_contract_details = get_contract_info('source', contract_info)
                source_contract_address = Web3.toChecksumAddress(source_contract_details['address'])
                source_contract_abi = source_contract_details['abi']
                source_contract = w3_source.eth.contract(address=source_contract_address, abi=source_contract_abi)

                # Build and send the 'withdraw' transaction on the source chain
                try:
                    account = w3_source.eth.account.from_key(WARDEN_PRIVATE_KEY)
                    w3_source.eth.default_account = account.address

                    nonce = w3_source.eth.get_transaction_count(account.address)
                    # Similar to 'wrap', you'll need to pass the appropriate arguments to 'withdraw'
                    # Example:
                    tx_hash = source_contract.functions.withdraw(
                        recipient,
                        amount,
                        token_address  # The ERC20 token address on the destination chain
                    ).transact({
                        'from': account.address,
                        'nonce': nonce,
                        'gas': 2000000,  # Adjust gas limit as needed
                        'gasPrice': w3_source.eth.gas_price
                    })
                    print(f"Withdraw transaction sent on Source Chain: {w3_source.toHex(tx_hash)}")
                    w3_source.eth.wait_for_transaction_receipt(tx_hash)
                    print(f"Withdraw transaction confirmed: {w3_source.toHex(tx_hash)}")
                except Exception as e:
                    print(f"Error sending withdraw transaction: {e}")








