import pandas as pd
from sqlalchemy import create_engine



import pandas as pd
from sqlalchemy import create_engine


def get_revenue_per_store_per_day(database_path):

    engine = create_engine(
        f"sqlite:///{database_path}"
    )

    query = """
    SELECT
        store_name,
        sale_date,
        SUM(total_revenue) AS revenue
    FROM retail_sales
    GROUP BY store_name, sale_date
    ORDER BY sale_date, revenue DESC;
    """

    result = pd.read_sql(query, engine)

    print("\n===== REVENUE PER STORE PER DAY =====")
    print(result)

    return result

def get_top_products(database_path):

    engine = create_engine(
        f"sqlite:///{database_path}"
    )

    query = """
    SELECT
        product_name,
        SUM(quantity) AS total_quantity
    FROM retail_sales
    GROUP BY product_name
    ORDER BY total_quantity DESC
    LIMIT 3;
    """

    result = pd.read_sql(query, engine)

    print("\n===== TOP 3 PRODUCTS =====")
    print(result)

    return result