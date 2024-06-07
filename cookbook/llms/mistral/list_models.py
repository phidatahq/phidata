import os

from rich.pretty import pprint
from mistralai.client import MistralClient


def main():
    api_key = os.environ["MISTRAL_API_KEY"]
    client = MistralClient(api_key=api_key)
    list_models_response = client.list_models()
    available_models = []
    for model in list_models_response.data:
        available_models.append(model.id)
    pprint(available_models)


if __name__ == "__main__":
    main()
