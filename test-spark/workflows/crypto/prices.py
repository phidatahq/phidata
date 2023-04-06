from typing import Dict

from phidata.table.local.csv import CsvTableLocal
from phidata.checks.not_empty import NotEmpty
from phidata.task import TaskArgs, task
from phidata.utils.log import logger
from phidata.utils.print_table import print_table
from phidata.workflow import Workflow

##############################################################################
# A workflow to download crypto price data locally
##############################################################################

# Step 1: Define CsvTableLocal for storing data
# Path: `storage/tables/crypto_prices`
crypto_prices_local = CsvTableLocal(
    name="crypto_prices",
    database="crypto",
    partitions=["ds"],
    write_checks=[NotEmpty()],
)


# Step 2: Create task to download crypto price data and write to CsvTableLocal
@task
def load_crypto_prices(**kwargs) -> bool:
    """
    Download prices and load a CsvTableLocal.
    """
    import httpx
    import pyarrow as pa

    coins = ["bitcoin", "ethereum"]
    run_date = TaskArgs.from_kwargs(kwargs).run_date
    run_day = run_date.strftime("%Y-%m-%d")

    logger.info(f"Downloading prices for ds={run_day}")
    response: Dict[str, Dict] = httpx.get(
        url="https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": ",".join(coins),
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        },
    ).json()

    # Create pyarrow.Table
    # https://arrow.apache.org/docs/python/generated/pyarrow.Table.html#pyarrow.Table.from_pylist
    table = pa.Table.from_pylist(
        [
            {
                "ds": run_day,
                "ticker": coin_name,
                "usd": coin_data["usd"],
                "usd_market_cap": coin_data["usd_market_cap"],
                "usd_24h_vol": coin_data["usd_24h_vol"],
                "usd_24h_change": coin_data["usd_24h_change"],
                "last_updated_at": coin_data["last_updated_at"],
            }
            for coin_name, coin_data in response.items()
        ]
    )

    # Write table to disk
    return crypto_prices_local.write_table(table)


# 2.2: Create a task to analyze data in CsvTableLocal
@task
def analyze_crypto_prices(**kwargs) -> bool:
    """
    Read CsvTableLocal
    """
    import pyarrow as pa
    import pyarrow.dataset as ds

    run_date = TaskArgs.from_kwargs(kwargs).run_date
    run_day = run_date.strftime("%Y-%m-%d")

    logger.info(f"Reading prices for ds={run_day}\n")
    table: pa.Table = crypto_prices_local.read_table(filter=(ds.field("ds") == run_day))
    print_table(
        title="Crypto Prices", header=table.column_names, rows=table.to_pylist()
    )

    # Use polars to analyze data
    # import polars as pl
    # df: pl.DataFrame = pl.DataFrame(table)
    # logger.info(df)

    # Use pandas to analyze data
    # import pandas as pd
    # df: pd.DataFrame = table.to_pandas()
    # logger.info(df)

    return True


# Step 3: Instantiate the tasks
load_prices = load_crypto_prices()
analyze_prices = analyze_crypto_prices()

# Step 4: Create a Workflow to run these tasks
crypto_prices = Workflow(
    name="crypto_prices",
    tasks=[load_prices, analyze_prices],
    outputs=[crypto_prices_local],
    # Airflow tasks created by this workflow are ordered using the graph param
    # graph = { downstream: [upstream_list] }
    # The downstream task will run after tasks in the upstream_list
    # Run analyze_prices after load_prices
    graph={
        analyze_prices: [load_prices],
    },
)

# Step 5: Create a DAG to run the workflow on a schedule
dag = crypto_prices.create_airflow_dag()
