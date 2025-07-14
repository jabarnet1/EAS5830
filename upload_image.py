import requests
import json
from web3 import Web3

# --- 1. Upload Image to IPFS (using Pinata) ---
PINATA_API_KEY = "e8ed7bf8681511125adf"
PINATA_SECRET_API_KEY = "3e6f69c04bcfa8bab61e2b8da30d101539e8b882ee8f14ecb5fe71ad72decf20"

def upload_to_ipfs(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        headers = {'pinata_api_key': PINATA_API_KEY, 'pinata_secret_api_key': PINATA_SECRET_API_KEY}
        response = requests.post("https://api.pinata.cloud/pinning/pinFileToIPFS", files=files, headers=headers)
        response.raise_for_status()
        return response.json()['IpfsHash']

image_path = "libre.jpg"
image_ipfs_hash = upload_to_ipfs(image_path)
image_uri = f"ipfs://{image_ipfs_hash}"

# --- 2. Create NFT Metadata ---
nft_metadata = {
    "name": "LiBre NFT1",
    "description": "This is very first NFT for LiBre.",
    "image": image_uri,
    "attributes": [
        {"trait_type": "Background", "value": "Yellow"},
        {"trait_type": "Logo", "value": "Square"}
    ]
}

# --- 3. Upload Metadata to IPFS ---
metadata_filename = "nft_metadata.json"
with open(metadata_filename, "w") as f:
    json.dump(nft_metadata, f, indent=4)

metadata_ipfs_hash = upload_to_ipfs(metadata_filename)
metadata_uri = f"ipfs://{metadata_ipfs_hash}"

# --- 4. Mint NFT (Conceptual - requires smart contract interaction) ---
# w3 = Web3(Web3.HTTPProvider("YOUR_ETHEREUM_NODE_URL"))
# contract_address = "YOUR_CONTRACT_ADDRESS"
# contract_abi = json.loads("YOUR_CONTRACT_ABI")
# contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# # Example of calling a mint function (replace with your contract's function)
# # tx_hash = contract.functions.mintNFT(recipient_address, metadata_uri).transact({'from': your_wallet_address})
# # print(f"Transaction Hash: {tx_hash.hex()}")

print(f"Image IPFS URI: {image_uri}")
print(f"Metadata IPFS URI: {metadata_uri}")