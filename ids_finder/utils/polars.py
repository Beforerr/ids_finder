# AUTOGENERATED! DO NOT EDIT! File to edit: ../../notebooks/utils/10_polars.ipynb.

# %% auto 0
__all__ = ['create_partitions', 'convert_to_pd_dataframe', 'sort', 'pl_norm', 'decompose_vector']

# %% ../../notebooks/utils/10_polars.ipynb 2
import polars as pl
import modin.pandas as mpd

from typing import Any, Collection

from functools import partial


# %% ../../notebooks/utils/10_polars.ipynb 3
def create_partitions(files, func):
    keys = [file.split("/")[-1] for file in files]
    return {key: partial(func, file) for key, file in zip(keys, files)}

# %% ../../notebooks/utils/10_polars.ipynb 5
def convert_to_pd_dataframe(
    df: pl.DataFrame | pl.LazyFrame, # original DataFrame or LazyFrame
    modin: bool = False # whether to use modin or not
):
    """
    Convert a Polars DataFrame or LazyFrame into a pandas-like DataFrame.
    If modin=True, returns a Modin DataFrame.
    """
    if isinstance(df, pl.LazyFrame):
        df = df.collect()
    elif not isinstance(df, pl.DataFrame):
        raise TypeError("Input must be a Polars DataFrame or LazyFrame")

    data = df.to_pandas(use_pyarrow_extension_array=True)

    if modin:
        return mpd.DataFrame(data)
    else:
        return data


# %% ../../notebooks/utils/10_polars.ipynb 7
def sort(df: pl.DataFrame, col="time"):
    if df.get_column(col).is_sorted():
        return df.set_sorted(col)
    else:
        return df.sort(col)


# %% ../../notebooks/utils/10_polars.ipynb 8
def _expand_selectors(items: Any, *more_items: Any) -> list[Any]:
    """
    See `_expand_selectors` in `polars`.
    """
    expanded: list[Any] = []
    for item in (
        *(
            items
            if isinstance(items, Collection) and not isinstance(items, str)
            else [items]
        ),
        *more_items,
    ):
        expanded.append(item)
    return expanded

# %% ../../notebooks/utils/10_polars.ipynb 9
def pl_norm(columns, *more_columns) -> pl.Expr:
    """
    Computes the square root of the sum of squares for the given columns.

    Args:
    *columns (str): Names of the columns.

    Returns:
    pl.Expr: Expression representing the square root of the sum of squares.
    """
    all_columns = _expand_selectors(columns, *more_columns)
    squares = [pl.col(column).pow(2) for column in all_columns]

    return sum(squares).sqrt()

# %% ../../notebooks/utils/10_polars.ipynb 10
def decompose_vector(df: pl.LazyFrame, vector_col, name=None):
    if name is None:
        name = vector_col

    return df.with_columns(
        pl.col(vector_col).list.get(0).alias(f"{name}_x"),
        pl.col(vector_col).list.get(1).alias(f"{name}_y"),
        pl.col(vector_col).list.get(2).alias(f"{name}_z"),
    )

