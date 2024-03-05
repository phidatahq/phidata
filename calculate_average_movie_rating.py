import pandas as pd


def calculate_average_rating(file_path):
    # Load the dataset
    df = pd.read_csv(file_path)

    # Calculate the average rating
    average_rating = df["Rating"].mean()
    return average_rating


if __name__ == "__main__":
    file_path = "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv"
    average_rating = calculate_average_rating(file_path)
    print(f"Average Movie Rating: {average_rating}")
