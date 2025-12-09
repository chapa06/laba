import requests

ACCOUNT = "Chapa"
PROJECT = "project"
ACCESS_KEY = "K9XQOQoUBYx3rZHzlrx5I4UPlM5K1m6H"  # <-- вставь ключ

CONTRACT = "0xYourContractAddress"  # <-- подставь адрес из deploy_test.py
FROM = "0x000000000000000000000000000000000000dead"  # можно любой фиктивный адрес

url = f"https://api.tenderly.co/api/v1/account/{ACCOUNT}/project/{PROJECT}/simulate"

# withdraw(1 ether) — формируем calldata manually
# function selector withdraw(uint256) = 0x2e1a7d4d
amount_hex = hex(10**18)[2:].rjust(64, "0")
input_data = "0x2e1a7d4d" + amount_hex

payload = {
    "network_id": "1",
    "from": FROM,
    "to": CONTRACT,
    "input": input_data,
    "gas": 8000000
}

headers = {
    "X-Access-Key": ACCESS_KEY,
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
print("\n--- Tenderly SIMULATION RESPONSE ---")
print(response.json())
