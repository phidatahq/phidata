import pandas as pd

def download_csv(url):
    return pd.read_csv(url)

def calculate_average_rating(df):
    return df['Rating'].mean()

if __name__ == "__main__":
    csv_url = "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv"
    movie_data = download_csv(csv_url)
    average_rating = calculate_average_rating(movie_data)
    print(f'The average rating of movies is {average_rating:.2f}')