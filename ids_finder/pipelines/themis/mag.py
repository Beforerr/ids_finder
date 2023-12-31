# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../notebooks/missions/themis/mag.ipynb.

# %% auto 0
__all__ = ['download_data', 'spz2df', 'load_data', 'preprocess_data', 'process_data', 'create_pipeline']

# %% ../../../notebooks/missions/themis/mag.ipynb 1
from datetime import timedelta
import polars as pl

from ...utils.basic import resample, partition_data_by_year
from ..default.data_mag import create_pipeline_template

# %% ../../../notebooks/missions/themis/mag.ipynb 4
import speasy as spz
from speasy import SpeasyVariable

# %% ../../../notebooks/missions/themis/mag.ipynb 5
def download_data(trange, mission, instrument, sat, datatype, coord) -> SpeasyVariable:
    product = f"cda/{sat}_L2_{instrument}/{sat.lower()}_{datatype}_{coord}"
    data = spz.get_data(product, trange, disable_proxy=True)

    return data


def spz2df(raw_data: SpeasyVariable):
    return pl.from_dataframe(raw_data.to_dataframe().reset_index()).rename(
        {"index": "time"}
    )


def load_data(
    start,
    end,
    sat="THB",
    instrument="FGM",
    datatype="fgs",
    coord="gse",
):
    trange = [start, end]

    data = download_data(
        trange, sat=sat, instrument=instrument, datatype=datatype, coord=coord
    )
    return spz2df(data).lazy()

# %% ../../../notebooks/missions/themis/mag.ipynb 7
def preprocess_data(
    raw_data: pl.LazyFrame,
    datatype: str = None,
) -> pl.LazyFrame:
    """
    Preprocess the raw dataset (only minor transformations)

    - Applying naming conventions for columns
    - Dropping duplicate time
    - Changing storing format to `parquet`

    """

    datatype = datatype.upper()
    name_mapping = {
        f"Bx {datatype}-D": "B_x",
        f"By {datatype}-D": "B_y",
        f"Bz {datatype}-D": "B_z",
    }

    return raw_data.sort("time").unique("time").rename(name_mapping)

# %% ../../../notebooks/missions/themis/mag.ipynb 9
def process_data(
    raw_data: pl.LazyFrame,
    ts,  # time resolution, in seconds
):
    every = timedelta(seconds=ts)
    period = every

    return raw_data.pipe(resample, every=every, period=period).pipe(
        partition_data_by_year
    )

# %% ../../../notebooks/missions/themis/mag.ipynb 11
def create_pipeline(sat_id="THB", source="MAG"):
    return create_pipeline_template(
        sat_id=sat_id,
        source=source,
        load_data_fn=load_data,
        preprocess_data_fn=preprocess_data,
        process_data_fn=process_data,
    )
