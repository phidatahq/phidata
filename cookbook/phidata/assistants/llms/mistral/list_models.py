import os

from mistralai import Mistral


def main():
    api_key = os.environ["MISTRAL_API_KEY"]
    client = Mistral(api_key=api_key)
    list_models_response = client.models.list()
    if list_models_response is not None:
        for model in list_models_response:
            print(model)


if __name__ == "__main__":
    main()
