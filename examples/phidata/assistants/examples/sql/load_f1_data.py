import pandas as pd
from sqlalchemy import create_engine
from phi.utils.log import logger

from assistant import db_url

s3_uri = "https://phi-public.s3.amazonaws.com/f1"

# List of files and their corresponding table names
files_to_tables = {
    f"{s3_uri}/constructors_championship_1958_2020.csv": "constructors_championship",
    f"{s3_uri}/drivers_championship_1950_2020.csv": "drivers_championship",
    f"{s3_uri}/fastest_laps_1950_to_2020.csv": "fastest_laps",
    f"{s3_uri}/race_results_1950_to_2020.csv": "race_results",
    f"{s3_uri}/race_wins_1950_to_2020.csv": "race_wins",
}


def load_database():
    logger.info("Loading database.")
    engine = create_engine(db_url)

    # Load each CSV file into the corresponding PostgreSQL table
    for file_path, table_name in files_to_tables.items():
        logger.info(f"Loading {file_path} into {table_name} table.")
        df = pd.read_csv(file_path)
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        logger.info(f"{file_path} loaded into {table_name} table.")

    logger.info("Database loaded.")


if __name__ == "__main__":
    load_database()
