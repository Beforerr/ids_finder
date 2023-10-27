# AUTOGENERATED! DO NOT EDIT! File to edit: ../../notebooks/99_utils.ipynb.

# %% auto 0
__all__ = ['DF_TYPE', 'HTTP_PROTOCOLS', 'savefig', 'pmap', 'get_code', 'load_catalog', 'DataConfig', 'filter_tranges',
           'filter_tranges_df', 'cdf2pl', 'pl_norm', 'partition_data_by_year', 'concat_df', 'concat_partitions',
           'format_timedelta', 'resample', 'load_lbl', 'LblDataset', 'get_memory_usage', 'download_file', 'check_fgm',
           'col_renamer', 'df2ts', 'sat_get_fgm_from_df', 'juno_get_state', 'calc_vec_mag', 'calc_time_diff']

# %% ../../notebooks/99_utils.ipynb 3
import matplotlib.pyplot as plt

# %% ../../notebooks/99_utils.ipynb 4
def savefig(name, **kwargs):
    plt.savefig(f"../figures/{name}.png", bbox_inches="tight", **kwargs)
    plt.savefig(f"../figures/{name}.pdf", bbox_inches="tight", **kwargs)

# %% ../../notebooks/99_utils.ipynb 6
import os
import requests

import polars as pl
import polars.selectors as cs

import pandas as pd
import xarray as xr

import pandas
import numpy as np
from xarray_einstats import linalg

from datetime import timedelta

from loguru import logger
from multipledispatch import dispatch

from xarray import DataArray
from typing import Union, Collection, Callable, Optional, Tuple
from typing import Any, Dict

# %% ../../notebooks/99_utils.ipynb 7
from pipe import select
from fastcore.utils import partial

# %% ../../notebooks/99_utils.ipynb 8
def pmap(func, *args, **kwargs):
    """
    map with `partial`
    """
    return select(partial(func, *args, **kwargs))

# %% ../../notebooks/99_utils.ipynb 9
def get_code(data, name):
    import lineapy
    "use lineapy to get code from data"
    lineapy.save(data, name)
    code = lineapy.get(name).get_code()
    print(code)
    return code

# %% ../../notebooks/99_utils.ipynb 15
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.ipython import _resolve_project_path

def load_catalog(project_path: str = '../'):
    project_path = _resolve_project_path(project_path)
    metadata = bootstrap_project(project_path)
    # configure_project(metadata.package_name)

    session = KedroSession.create(
        metadata.package_name, project_path,
    )
    context = session.load_context()
    catalog = context.catalog
    return catalog

# %% ../../notebooks/99_utils.ipynb 20
from pydantic import BaseModel
from datetime import datetime, timedelta
from pandas import Timedelta

class DataConfig(BaseModel):
    sat_id: str = None
    start: datetime = None
    end: datetime = None
    ts: timedelta = None
    coord: str = None

# %% ../../notebooks/99_utils.ipynb 22
from fastcore.utils import patch

# %% ../../notebooks/99_utils.ipynb 23
def filter_tranges(time: pl.Series, tranges: Tuple[list, list]):
    """
    - Filter data by time ranges, return the indices of the time that are in the time ranges (left inclusive, right exclusive)
    """

    starts = tranges[0]
    ends = tranges[1]

    start_indices = time.search_sorted(starts)
    end_indices = time.search_sorted(ends)

    return np.concatenate(
        [
            np.arange(start_index, end_index)
            for start_index, end_index in zip(start_indices, end_indices)
        ]
    )

def filter_tranges_df(df: pl.DataFrame, tranges: Tuple[list, list], time_col: str = "time"):
    """
    - Filter data by time ranges
    """

    time = df[time_col]
    filtered_indices = filter_tranges(time, tranges)
    return df[filtered_indices]

# %% ../../notebooks/99_utils.ipynb 24
import pycdfpp

# %% ../../notebooks/99_utils.ipynb 25
def cdf2pl(file_path: str, var_names: Union[str, list[str]]) -> pl.LazyFrame:
    """
    Convert a CDF file to Polars Dataframe.

    Parameters:
        file_path (str): The path to the CDF file.
        var_names (Union[str, List[str]]): The name(s) of the variable(s) to retrieve from the CDF file.

    Returns:
        pl.LazyFrame: A lazy dataframe containing the requested data.
    """
    
    # Ensure var_names is always a list
    if isinstance(var_names, str):
        var_names = [var_names]

    cdf = pycdfpp.load(file_path)
    epoch_time = pycdfpp.to_datetime64(cdf["Epoch"])
    
    columns = {"time": epoch_time}
    
    for var_name in var_names:
        var_values = cdf[var_name].values
        var_attrs = cdf[var_name].attributes
        
        # Handle FILLVAL
        if "FILLVAL" in var_attrs:
            fillval = var_attrs["FILLVAL"]
            var_values[var_values == fillval] = np.nan

        if var_values.shape[1] == 1:  # One-dimensional data
            columns[var_name] = var_values[:, 0]
        else:  # Multi-dimensional data
            # Dynamically create column names based on the shape of the field values
            for i in range(var_values.shape[1]):
                columns[f"{var_name}_{i}"] = var_values[:, i]

    df = pl.DataFrame(columns).fill_nan(None).lazy()
    return df

# %% ../../notebooks/99_utils.ipynb 26
@patch
def plot(self:pl.DataFrame, *args, **kwargs):
    return self.to_pandas().plot(*args, **kwargs)

# %% ../../notebooks/99_utils.ipynb 27
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

# %% ../../notebooks/99_utils.ipynb 29
def partition_data_by_year(df: pl.LazyFrame) -> Dict[str, pl.DataFrame]:
    """Partition the dataset by year

    Args:
        df: Input DataFrame.

    Returns:
        Partitioned DataFrame.
    """
    return (
        df.with_columns(year=pl.col("time").dt.year().cast(pl.Utf8))
        .collect()
        .partition_by("year", include_key=False, as_dict=True)
    )

# %% ../../notebooks/99_utils.ipynb 30
DF_TYPE = Union[pl.DataFrame, pl.LazyFrame, pd.DataFrame]
def concat_df(dfs: list[DF_TYPE]) -> DF_TYPE:
    """Concatenate a list of DataFrames into one DataFrame.
    """
    
    match type(dfs[0]):
        case pl.DataFrame | pl.LazyFrame:
            concat_func = pl.concat
        case pandas.DataFrame:
            concat_func = pandas.concat
        case _:
            raise ValueError(f"Unsupported DataFrame type: {type(dfs[0])}")
    
    return concat_func(dfs)
                     
def concat_partitions(partitioned_input: Dict[str, Callable]):
    """Concatenate input partitions into one DataFrame.

    Args:
        partitioned_input: A dictionary with partition ids as keys and load functions as values.
    """
    partitions_data = [
        partition_load_func() for partition_load_func in partitioned_input.values()
    ]  # load the actual partition data
    
    result = concat_df(partitions_data)
    return result

# %% ../../notebooks/99_utils.ipynb 32
def format_timedelta(time):
    """Format timedelta to `timedelta`"""
    if isinstance(time, timedelta):
        return time
    elif isinstance(time, str):
        return pd.Timedelta(time)
    elif isinstance(time, int):
        return pd.Timedelta(seconds=time)
    else:
        raise TypeError(f"Unsupported type: {type(time)}")

def resample(
    df: pl.DataFrame | pl.LazyFrame, 
    every: timedelta | str | int, period: str | timedelta = None,
    time_column='time',
) -> pl.DataFrame | pl.LazyFrame:
    """Resample the DataFrame"""
    if period is None:
        period = every
    every = format_timedelta(every)
    period = format_timedelta(period)
    return (
        df.sort(time_column)
        .group_by_dynamic(time_column, every=every, period=period)
        .agg(cs.numeric().mean())
        .with_columns(
            (pl.col(time_column) + period / 2).dt.cast_time_unit("ns")
        )
    )

# %% ../../notebooks/99_utils.ipynb 34
from pathlib import PurePosixPath
import fsspec

from kedro.io import AbstractDataset
from kedro.io.core import get_filepath_str, get_protocol_and_path
from kedro.extras.datasets.pandas import CSVDataSet

import pdr

# %% ../../notebooks/99_utils.ipynb 35
HTTP_PROTOCOLS = ("http", "https")


def load_lbl(filepath: str, type: str = "table") -> pandas.DataFrame:
    """Load LBL data.

    Args:
        filepath: File path to load the data from.
        type: Type of data to load. Options are 'table' and 'index'.

    Returns:
        A pandas DataFrame containing the loaded data.
    """
    if type == "table":
        df = pdr.read(filepath).TABLE
    elif type == "index":
        df = pandas.read_csv(filepath, delimiter=",", quotechar='"')
        df.columns = df.columns.str.replace(" ", "")

    return df


class LblDataset(AbstractDataset):
    def __init__(
        self,
        filepath: str,
        load_type: str = "table",
        metadata: Dict[str, Any] = None,
    ):
        # parse the path and protocol (e.g. file, http, s3, etc.)
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._filepath = PurePosixPath(path)

        self._fs = fsspec.filesystem(self._protocol)

        self.load_type = load_type
        self.metadata = metadata

    def _load(self):
        # using get_filepath_str ensures that the protocol and path are appended correctly for different filesystems
        load_path = get_filepath_str(self._filepath, self._protocol)

        if self._protocol in HTTP_PROTOCOLS:
            import pooch

            local_fp = pooch.retrieve(load_path, known_hash=None)
        else:
            local_fp = load_path

        return load_lbl(local_fp, self.load_type)

    def _save(self):
        pass

    def _describe(self):
        """Returns a dict that describes the attributes of the dataset."""
        return dict(filepath=self._filepath, protocol=self._protocol)

# %% ../../notebooks/99_utils.ipynb 36
from humanize import naturalsize

# %% ../../notebooks/99_utils.ipynb 37
def get_memory_usage(data):
    datatype = type(data)
    match datatype:
        case pl.DataFrame:
            size = data.estimated_size()
        case pd.DataFrame:
            size = data.memory_usage().sum()
        case xr.DataArray:
            size = data.nbytes

    logger.info(f"{naturalsize(size)} ({datatype.__name__})")
    return size

# %% ../../notebooks/99_utils.ipynb 38
def download_file(url, local_dir="./", file_name=None):
    """
    Download a file from a URL and save it locally.

    Returns:
    file_path (str): Path to the downloaded file.
    """
    if file_name is None:
        file_name = url.split("/")[-1]

    file_path = os.path.join(local_dir, file_name)
    dir = os.path.dirname(file_path)
    if not os.path.isdir(dir):
        os.makedirs(dir)

    if not os.path.exists(file_path):
        logger.debug(f"Downloading from {url}")
        response = requests.get(url)
        with open(file_path, "wb") as f:
            f.write(response.content)
    return file_path

def check_fgm(vec: xr.DataArray):
    # check if time is monotonic increasing
    logger.info("Check if time is monotonic increasing")
    assert vec.time.to_series().is_monotonic_increasing
    # check available time difference
    logger.info(
        f"Available time delta: {vec.time.diff(dim='time').to_series().unique()}"
    )


def col_renamer(lbl: str):
    if lbl.startswith("BX"):
        return "BX"
    if lbl.startswith("BY"):
        return "BY"
    if lbl.startswith("BZ"):
        return "BZ"
    return lbl


def df2ts(
    df: Union[pandas.DataFrame, pl.DataFrame, pl.LazyFrame], cols, attrs=None, name=None
):
    for col in cols:
        if col not in df.columns:
            raise KeyError(f"Expected column {col} not found in the dataframe.")

    if isinstance(df, pl.LazyFrame):
        df = df.collect()

    # Prepare data
    data = df[cols]

    # Prepare coordinates
    time = df.index if isinstance(df, pandas.DataFrame) else df["time"]

    # Create the DataArray
    coords = {"time": time, "v_dim": cols}

    return xr.DataArray(data, coords=coords, attrs=attrs, name=name)


def sat_get_fgm_from_df(df: Union[pandas.DataFrame, pl.DataFrame, pl.LazyFrame]):
    attrs = {"coordinate_system": "se", "units": "nT"}

    return df2ts(df, cols=["BX", "BY", "BZ"], attrs=attrs, name="sat_fgm")


def juno_get_state(df: Union[pandas.DataFrame, pl.DataFrame, pl.LazyFrame]):
    attrs = {"coordinate_system": "se", "units": "km"}
    return df2ts(df, cols=["X", "Y", "Z"], attrs=attrs, name="sat_state")


def calc_vec_mag(vec) -> DataArray:
    return linalg.norm(vec, dims="v_dim")

# %% ../../notebooks/99_utils.ipynb 39
@dispatch(pl.DataFrame)
def calc_time_diff(data: pl.DataFrame): 
    return data.get_column('time').diff(null_behavior="drop").unique().sort()

@dispatch(pl.LazyFrame)
def calc_time_diff(
    data: pl.LazyFrame
) -> pl.Series: 
    return calc_time_diff(data.collect())
