from web3 import Web3
from web3.providers.rpc import HTTPProvider
import requests
import json

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
contract_address = Web3.to_checksum_address(bayc_address)

# You will need the ABI to connect to the contract
# The file 'abi.json' has the ABI for the bored ape contract
# In general, you can get contract ABIs from etherscan
# https://api.etherscan.io/api?module=contract&action=getabi&address=0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D
with open('ape_abi.json', 'r') as f:
    abi = json.load(f)

############################
# Connect to an Ethereum node
project_id = "295acf6b9a904c5ab2254913c941f98a"
api_url = f"https://mainnet.infura.io/v3/{project_id}"
provider = HTTPProvider(api_url)
web3 = Web3(provider)

# Check connection
#if web3.is_connected():
#    print("Connected to Ethereum node!")
#else:
#    print("Failed to connect to Ethereum node.")

try:
    contract = web3.eth.contract(address=contract_address, abi=abi)

except Exception as e:
    print(f"An contract error occurred: {e}")


def get_ape_info(ape_id):

    assert isinstance(ape_id, int), f"{ape_id} is not an int"
    assert 0 <= ape_id, f"{ape_id} must be at least 0"
    assert 9999 >= ape_id, f"{ape_id} must be less than 10,000"

    data = {'owner': "", 'image': "", 'eyes': ""}

    # YOUR CODE HERE
    owner, eyes, image = None, None, None
    cid = None

    try:

        owner = contract.functions.ownerOf(ape_id).call()
        token_uri = contract.functions.tokenURI(ape_id).call()

        prefix_to_remove = "ipfs://"
        cid = token_uri.removeprefix(prefix_to_remove)
        gateway_url = f"https://gateway.pinata.cloud/ipfs/{cid}"

        response = requests.get(gateway_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        metadata = response.json()

        # for debug
        #print(f"metadata: {metadata}")

        image = metadata['image']

        for attribute in metadata['attributes']:
            if attribute['trait_type'] == 'Eyes':
                eyes = attribute['value']
                break  # Stop after finding the desired attribute

        data['owner'] = owner
        data['image'] = image
        data['eyes'] = eyes

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving JSON from CID {cid}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from CID {cid}: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    assert isinstance(data, dict), f'get_ape_info{ape_id} should return a dict'
    assert all([a in data.keys() for a in
                ['owner', 'image', 'eyes']]), f"return value should include the keys 'owner','image' and 'eyes'"

    return data


if __name__ == "__main__":

    data = get_ape_info(1)
    print(f"owner: {data['owner']}")
    print(f"owner: {data['image']}")
    print(f"owner: {data['eyes']}")
