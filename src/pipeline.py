from config import (
    SALES_FILE,
    PRODUCTS_FILE,
    STORES_FILE,
    DATABASE_PATH
)

from src.extract import load_data
from src.validate import check_missing_values
from src.clean import clean_sales_data
from src.transform import transform_data
from src.load import load_to_database
from src.query import (
    get_top_products,
    get_revenue_per_store_per_day
)
from src.report import generate_summary_report


def run_pipeline():

    try:

        sales_df, products_df, stores_df = load_data(
            SALES_FILE,
            PRODUCTS_FILE,
            STORES_FILE
        )

        check_missing_values(sales_df, "SALES")
        check_missing_values(products_df, "PRODUCTS")
        check_missing_values(stores_df, "STORES")

        sales_df = clean_sales_data(sales_df)

        final_df, city_revenue = transform_data(
            sales_df,
            products_df,
            stores_df
        )

        load_to_database(
            final_df,
            DATABASE_PATH
        )

        top_products = get_top_products(
            DATABASE_PATH
        )

        get_revenue_per_store_per_day(
            DATABASE_PATH
        )

        generate_summary_report(
            final_df,
            city_revenue,
            top_products
        )

    except FileNotFoundError as e:
        print(f"File not found: {e}")

    except Exception as e:
        print(f"Unexpected pipeline error: {e}")