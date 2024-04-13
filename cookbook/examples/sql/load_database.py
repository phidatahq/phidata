import pandas as pd
from sqlalchemy import create_engine
from phi.utils.log import logger

from assistant import root_dir
from resources import vector_db

data_dir = root_dir.joinpath("wip", "data")

# List of files and their corresponding table names
files_to_tables = {
    data_dir.joinpath("constructors_championship_1958_2020.csv"): "constructors_championship",
    data_dir.joinpath("drivers_championship_1950_2020.csv"): "drivers_championship",
    data_dir.joinpath("fastest_laps_1950_to_2020.csv"): "fastest_laps",
    data_dir.joinpath("race_results_1950_to_2020.csv"): "race_results",
    data_dir.joinpath("race_wins_1950_to_2020.csv"): "race_wins",
}


def load_database():
    logger.info("Loading database.")
    engine = create_engine(vector_db.get_db_connection_local())

    # Load each CSV file into the corresponding PostgreSQL table
    for file_path, table_name in files_to_tables.items():
        df = pd.read_csv(file_path)
        df.to_sql(table_name, engine, schema="f1", if_exists="replace", index=False)
        logger.info(f"{file_path} loaded into {table_name} table.")

    logger.info("Database loaded.")


if __name__ == "__main__":
    load_database()
