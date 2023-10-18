# AUTOGENERATED! DO NOT EDIT! File to edit: ../notebooks/00_candidates.ipynb.

# %% auto 0
__all__ = ['sw_vec_rtn_cols', 'b_vecL_rtn_cols', 'candidates_columns_name_mapping', 'j_factor', 'CandidateID', 'vector_project',
           'vector_project_pl', 'compute_inertial_length', 'unitize', 'combine_features', 'create_candidate_pipeline']

# %% ../notebooks/00_candidates.ipynb 2
import polars as pl
import pandas as pd
import pandas
import xarray as xr

from datetime import timedelta

# %% ../notebooks/00_candidates.ipynb 4
from kedro.pipeline import Pipeline, node
from kedro.pipeline.modular_pipeline import pipeline

# %% ../notebooks/00_candidates.ipynb 11
from pprint import pprint

# %% ../notebooks/00_candidates.ipynb 12
class CandidateID:
    def __init__(self, time, df: pl.DataFrame) -> None:
        self.time = pd.Timestamp(time)
        self.data = df.row(
            by_predicate=(pl.col("time") == self.time), 
            named=True
        )

    def __repr__(self) -> str:
        # return self.data.__repr__()
        pprint(self.data)
        return ''
    
    def plot(self, sat_fgm, tau):
        plot_candidate_xr(self.data, sat_fgm, tau)
        pass
        

# %% ../notebooks/00_candidates.ipynb 18
sw_vec_rtn_cols = ["sw_vel_r", "sw_vel_t", "sw_vel_n"]  # solar wind velocity vector in RTN coordinate system
b_vecL_rtn_cols = ["b_vecL_r", "b_vecL_t", "b_vecL_n"]  # major eigenvector

# %% ../notebooks/00_candidates.ipynb 20
candidates_columns_name_mapping = {
   "Vl_x": "b_vecL_r",
    "Vl_y": "b_vecL_t",
    "Vl_z": "b_vecL_n",
}

# %% ../notebooks/00_candidates.ipynb 21
import polars as pl

from .utils.basic import df2ts, pl_norm
import xarray as xr
from xarray_einstats import linalg

# %% ../notebooks/00_candidates.ipynb 22
def vector_project(v1,v2, dim="v_dim"):
    return xr.dot(v1 , v2, dims=dim) / linalg.norm(v2, dims=dim)

def vector_project_pl(df: pl.DataFrame, v1_cols, v2_cols, name=None):
    
    v1 = df2ts(df, v1_cols).assign_coords(v_dim=["r","t","n"])
    v2 = df2ts(df, v2_cols).assign_coords(v_dim=["r","t","n"]) 
    result = vector_project(v1, v2, dim="v_dim")
    
    return df.with_columns(
        pl.Series(result.data).alias(name or "v_proj")
    )

# %% ../notebooks/00_candidates.ipynb 23
import astropy.units as u
from astropy.constants import mu0
from plasmapy.formulary.lengths import inertial_length

# %% ../notebooks/00_candidates.ipynb 24
def compute_inertial_length(df: pl.DataFrame):
    
    result = inertial_length(df['sw_density'].to_numpy() * u.cm**(-3), 'H+').to(u.km)
    
    return df.with_columns(
        ion_inertial_length = pl.Series(result.value)
    )

j_factor = ((u.nT/u.s) * (1 / mu0 / (u.km/u.s) )).si.value


def unitize(df: pl.DataFrame):
    """unitize the columns in the dataframe with
    """

    return df.with_columns(
        j0 = pl.col('j0') * j_factor,
    )

# %% ../notebooks/00_candidates.ipynb 25
def combine_features(candidates: pl.DataFrame, sat_states: pl.DataFrame):
    updated_candidates = (
        candidates.rename(candidates_columns_name_mapping)
        .sort("time")
        .join_asof(sat_states.sort("time"), on="time")
    )

    df = (
        updated_candidates.with_columns(
            duration=pl.col("d_tstop") - pl.col("d_tstart"),
        )
        .pipe(vector_project_pl, sw_vec_rtn_cols, b_vecL_rtn_cols, name="sw_vel_l")
        .with_columns(
            sw_vel_mn=(pl.col("sw_speed") ** 2 - pl.col("sw_vel_l") ** 2).sqrt()
        )
        .with_columns(
            L_mn=pl.col("sw_vel_mn") * pl.col("duration").dt.nanoseconds() / 1e9,
            j0=pl.col("d_star") / pl.col("sw_vel_mn"),
        )
        .pipe(compute_inertial_length)
        .pipe(unitize)
        .with_columns(L_mn_norm=pl.col("L_mn") / pl.col("ion_inertial_length"))
    )

    return df

# %% ../notebooks/00_candidates.ipynb 27
from kedro.pipeline import Pipeline, node
from kedro.pipeline.modular_pipeline import pipeline

# %% ../notebooks/00_candidates.ipynb 28
def create_candidate_pipeline(
    sat_id, 
    tau: str = "60s",
    ts_state: str = "1h",
    **kwargs) -> Pipeline:

    node_combine_features = node(
        combine_features,
        inputs=[
            f"{sat_id}.feature_tau_{tau}",
            f"{sat_id}.primary_state_{ts_state}",
        ],
        outputs=f"candidates.{sat_id}_tau_{tau}",
    )

    nodes = [node_combine_features]
    return pipeline(nodes)
