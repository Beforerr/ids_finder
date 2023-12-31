# AUTOGENERATED! DO NOT EDIT! File to edit: ../../notebooks/utils/30_cdf.ipynb.

# %% auto 0
__all__ = ['cdf2pl']

# %% ../../notebooks/utils/30_cdf.ipynb 1
import pycdfpp
import numpy as np
import polars as pl

# %% ../../notebooks/utils/30_cdf.ipynb 2
def cdf2pl(file_path: str, var_names: str | list[str]) -> pl.LazyFrame:
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
        
        var = cdf[var_name]
        var_values = var.values
        var_attrs = var.attributes
        
        # Handle FILLVAL
        if "FILLVAL" in var_attrs:
            fillval = var_attrs["FILLVAL"][0]
            var_values[var_values == fillval] = np.nan

        if var_values.shape[1] == 1:  # One-dimensional data
            columns[var_name] = var_values[:, 0]
        else:  # Multi-dimensional data
            # Dynamically create column names based on the shape of the field values
            for i in range(var_values.shape[1]):
                columns[f"{var_name}_{i}"] = var_values[:, i]

    df = pl.DataFrame(columns).fill_nan(None).lazy()
    return df
