import json
import os
from web3 import Web3, HTTPProvider

# No need to install_solc or use py-solc-x compilation here
# since pre-compiled artifacts from Remix Desktop will be used.

def deploy_contract(w3, account, private_key, contract_artifact_filename, constructor_args=None):
    """
    Deploys a Solidity contract using pre-compiled artifacts from a specified JSON file
    and returns its address and ABI.
    """
    contract_name = os.path.splitext(contract_artifact_filename)[0] # Extract name without .json extension
    print(f"\n--- Deploying {contract_name} to chain ID {w3.eth.chain_id} ---")

    # Construct the path to the artifact JSON file
    # Assumes artifacts folder is in the same directory as this script
    artifact_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts", contract_artifact_filename)

    if not os.path.exists(artifact_path):
        raise FileNotFoundError(f"Artifact file not found: {artifact_path}. Please compile your contract in Remix Desktop and save the bytecode/ABI to this file.")

    # Load ABI and bytecode from the JSON artifact file
    with open(artifact_path, "r") as f:
        contract_artifact = json.load(f)

    bytecode = contract_artifact['bytecode']
    abi = contract_artifact['abi']

    # Ensure bytecode is a hex string (Remix usually provides it this way)
    if not bytecode.startswith('0x'):
        bytecode = '0x' + bytecode

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    nonce = w3.eth.get_transaction_count(account.address)

    # Build the constructor arguments if any
    if constructor_args:
        transaction = Contract.constructor(*constructor_args).build_transaction({
            'chainId': w3.eth.chain_id,
            'from': account.address,
            'nonce': nonce,
            'gasPrice': w3.eth.gas_price
        })
    else:
        transaction = Contract.constructor().build_transaction({
            'chainId': w3.eth.chain_id,
            'from': account.address,
            'nonce': nonce,
            'gasPrice': w3.eth.gas_price
        })

    # Estimate gas and update the transaction (optional but recommended)
    gas_limit = w3.eth.estimate_gas(transaction)
    transaction['gas'] = gas_limit

    # Sign the transaction with your private key
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)

    # Send the raw transaction to the network
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Deployment transaction hash: {tx_hash.hex()}")

    # Wait for the transaction to be mined and get the receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    print(f"{contract_name} deployed at address: {contract_address}")

    return contract_address, abi

def main():
    # --- Environment setup (using public RPCs and assuming PyCharm config) ---
    # Retrieve environment variables set in PyCharm's Run/Debug Configurations
    avax_testnet_rpc_url = os.environ.get("AVAX_TESTNET_RPC_URL", "https://api.avax-test.network/ext/bc/C/rpc")
    bsc_testnet_rpc_url = os.environ.get("BSC_TESTNET_RPC_URL", "https://data-seed-prebsc-1-s1.bnbchain.org:8545")
    private_key = os.environ.get("PRIVATE_KEY")

    if not avax_testnet_rpc_url or not bsc_testnet_rpc_url or not private_key:
        raise ValueError("Missing environment variables. Please set AVAX_TESTNET_RPC_URL, BSC_TESTNET_RPC_URL, and PRIVATE_KEY in PyCharm's Run/Debug Configurations.")

    # --- Deploy to Avalanche Testnet (Source Chain) ---
    print("\n--- Deploying to Avalanche Fuji Testnet ---")
    w3_avax = Web3(HTTPProvider(avax_testnet_rpc_url))
    print(f"Connected to Avalanche Fuji Testnet: {w3_avax.is_connected()}")
    if not w3_avax.is_connected():
        raise ConnectionError("Failed to connect to Avalanche Fuji Testnet.")

    deployer_account_avax = w3_avax.eth.account.from_key(private_key)
    w3_avax.eth.default_account = deployer_account_avax.address
    print(f"Deployer (Bridge Warden) Address on Avalanche: {deployer_account_avax.address}")

    # Deploy Source Contract using its artifact file (Source.json)
    source_contract_address, source_contract_abi = deploy_contract(
        w3_avax, deployer_account_avax, private_key,
        "Source.json",  # Specify the filename here
        [deployer_account_avax.address]  # Pass the deployer's address as the admin
    )

    # --- Deploy to BNB Testnet (Destination Chain) ---
    print("\n--- Deploying to BNB Testnet ---")
    w3_bsc = Web3(HTTPProvider(bsc_testnet_rpc_url))
    print(f"Connected to BNB Testnet: {w3_bsc.is_connected()}")
    if not w3_bsc.is_connected():
        raise ConnectionError("Failed to connect to BNB Testnet.")

    deployer_account_bsc = w3_bsc.eth.account.from_key(private_key)
    w3_bsc.eth.default_account = deployer_account_bsc.address
    print(f"Deployer (Bridge Warden) Address on BNB Testnet: {deployer_account_bsc.address}")

    # Deploy Destination Contract using its artifact file (Destination.json)
    destination_contract_address, destination_contract_abi = deploy_contract(
        w3_bsc, deployer_account_bsc, private_key,
        "Destination.json",  # Specify the filename here
        [deployer_account_bsc.address]  # Pass the deployer's address as the admin for Destination.sol
    )

    # --- Store deployment information in contract_info.json ---
    contract_info = {
        "source": {
            "address": source_contract_address,
            "abi": source_contract_abi
        },
        "destination": {
            "address": destination_contract_address,
            "abi": destination_contract_abi
        }
    }

    with open("contract_info.json", "w") as outfile:
        json.dump(contract_info, outfile, indent=4)
    print("\nDeployment information saved to contract_info.json")

if __name__ == "__main__":
    main()
