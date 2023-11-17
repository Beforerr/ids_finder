# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../notebooks/pipelines/100_project.ipynb.

# %% auto 0
__all__ = ['process_events_l1', 'create_l1_node', 'combine_events', 'create_pipeline']

# %% ../../../notebooks/pipelines/100_project.ipynb 3
import polars as pl
from beforerr.basics import pmap


# %% ../../../notebooks/pipelines/100_project.ipynb 5
from kedro.pipeline import Pipeline, node
from kedro.pipeline.modular_pipeline import pipeline

# %% ../../../notebooks/pipelines/100_project.ipynb 6
from datetime import timedelta
from loguru import logger
import polars.selectors as cs


def process_events_l1(events: pl.LazyFrame):
    "clean data to remove extreme values"
    events = events.collect()

    df = events.filter(
        pl.col("d_star") < 100,  # exclude extreme values
        pl.col("v_mn") > 10,
        pl.col("duration") < timedelta(seconds=60),
    ).with_columns(
        cs.float().cast(pl.Float64),
        j0_norm_log=pl.col("j0_norm").log10(),
        L_mn_norm_log=pl.col("L_mn_norm").log10(),
    )

    logger.info(
        f"candidates_l1: {len(df)}, with effective ratio: {len(df) / len(events):.2%}"
    )

    return df.lazy()

# %% ../../../notebooks/pipelines/100_project.ipynb 7
def create_l1_node(sat="JNO", ts=1, tau=60):
    ts_str = f"ts_{ts}s"
    tau_str = f"tau_{tau}s"
    return node(
        process_events_l1,
        inputs=f"events.{sat}_{ts_str}_{tau_str}",
        outputs=f"events.l1.{sat}_{ts_str}_{tau_str}",
    )

# %% ../../../notebooks/pipelines/100_project.ipynb 8
def combine_events(**datasets):
    datasets = [v.with_columns(sat=pl.lit(key)) for key, v in datasets.items()]
    combined_dataset = pl.concat(datasets, how="diagonal")
    return combined_dataset.with_columns(
        pl.col("radial_distance").fill_null(1),  # by default, fill with 1 AU
    ).with_columns(
        r_bin=pl.col("radial_distance").round(),
    )


def create_pipeline():
    combine_layer = "events.l1"
    node_combine_events = node(
        combine_events,
        inputs=dict(
            JNO=f"{combine_layer}.JNO_ts_1s_tau_60s",
            STA=f"{combine_layer}.STA_ts_1s_tau_60s",
            THB=f"{combine_layer}.THB_sw_ts_1s_tau_60s",
        ),
        outputs=f"{combine_layer}.ALL_sw_ts_1s_tau_60s",
        # namespace="events.l1",
    )

    nodes = [
        node_combine_events,
        create_l1_node("JNO"),
        create_l1_node("STA"),
        create_l1_node("THB_sw"),
    ]
    return pipeline(nodes)
