import requests
import json

def pin_to_ipfs(data):
	assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
	#YOUR CODE HERE

	#API Key: e8ed7bf8681511125adf
	#API Secret: 3e6f69c04bcfa8bab61e2b8da30d101539e8b882ee8f14ecb5fe71ad72decf20
	#JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySW5mb3JtYXRpb24iOnsiaWQiOiJhMjhiYzM1Yy0yNzE2LTRlMmUtYjc0NS02NGJlZWU2NjQ5ODAiLCJlbWFpbCI6ImphYmFybmV0QHNlYXMudXBlbm4uZWR1IiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBpbl9wb2xpY3kiOnsicmVnaW9ucyI6W3siZGVzaXJlZFJlcGxpY2F0aW9uQ291bnQiOjEsImlkIjoiRlJBMSJ9LHsiZGVzaXJlZFJlcGxpY2F0aW9uQ291bnQiOjEsImlkIjoiTllDMSJ9XSwidmVyc2lvbiI6MX0sIm1mYV9lbmFibGVkIjpmYWxzZSwic3RhdHVzIjoiQUNUSVZFIn0sImF1dGhlbnRpY2F0aW9uVHlwZSI6InNjb3BlZEtleSIsInNjb3BlZEtleUtleSI6ImU4ZWQ3YmY4NjgxNTExMTI1YWRmIiwic2NvcGVkS2V5U2VjcmV0IjoiM2U2ZjY5YzA0YmNmYThiYWI2MWUyYjhkYTMwZDEwMTUzOWU4Yjg4MmVlOGYxNGVjYjVmZTcxYWQ3MmRlY2YyMCIsImV4cCI6MTc4MjcxNDI5OH0.HRced_-NIvNfr8ol3iMhtgR9EaPr6LlDXQvyrN6T6gQ

	json_data = json.dumps(data)
	cid = 0

	PINATA_BASE_URL = "https://api.pinata.cloud/"
	endpoint = "pinning/pinFileToIPFS"

	PINATA_API_KEY = "e8ed7bf8681511125adf"
	PINATA_API_SECRET = "3e6f69c04bcfa8bab61e2b8da30d101539e8b882ee8f14ecb5fe71ad72decf20"

	headers = { "pinata_api_key": PINATA_API_KEY,"pinata_secret_api_key": PINATA_API_SECRET,}

	with open("temp.json", "w") as f:
		f.write(json_data)

	files = {"file": ("temp.json", open("temp.json", "rb")),}

	try:
		response = requests.post(PINATA_BASE_URL + endpoint, headers=headers, files = files)
		response.raise_for_status()
		cid = response.json()["IpfsHash"]

	except requests.exceptions.RequestException as e:
		print(f"Error uploading file to Pinata: {e}")

	#finally:
	#	import os
	#	os.remove("temp.json")

	return cid

def get_from_ipfs(cid,content_type="json"):
	assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"

	#YOUR CODE HERE
	gateway_url = f"https://gateway.pinata.cloud/ipfs/{cid}"

	try:
		response = requests.get(gateway_url)
		response.raise_for_status()  # Raise an exception for bad status codes
		data = response.json()
	except requests.exceptions.RequestException as e:
		print(f"Error retrieving JSON from CID {cid}: {e}")
		return None
	except json.JSONDecodeError as e:
		print(f"Error decoding JSON from CID {cid}: {e}")
		return None

	assert isinstance(data,dict), f"get_from_ipfs should return a dict"
	return data


'''
if __name__ == "__main__":
	
	json_data = {
    	"name": "Your Data",
    	"value": "Important information"
	}

	cid = pin_to_ipfs(json_data)
	print(f"File uploaded successfully! cid: {cid}")


	data = get_from_ipfs(cid)

	if data:
		print("Successfully retrieved and parsed JSON:")
		print(data)
	else:
		print("Failed to retrieve or parse JSON from CID.")
		
'''
