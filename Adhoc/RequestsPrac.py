import requests


def get_secret_message():
    response = requests.get("https://localhost:5683", verify="ca-public-key.pem")
    print(f"The secret message is {response.text}")


if __name__ == "__main__":
    get_secret_message()