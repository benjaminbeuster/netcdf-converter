#!/usr/bin/env python3
"""
Test script for NetCDF import functionality
"""

from pathlib import Path
import pandas as pd
import numpy as np
import xarray as xr

# Inline version of the read_netcdf function for testing
def read_netcdf(filename: Path, sample_size=1000, **kwargs):
    """
    Read NetCDF file and create a metadata structure compatible with what pyreadstat returns
    """
    filename = Path(filename)

    if not filename.suffix.lower() in ['.nc', '.nc4', '.netcdf']:
        raise ValueError(f"Unsupported file type! Expected .nc, .nc4, or .netcdf, got: {filename.suffix}")

    try:
        ds = xr.open_dataset(filename)
    except Exception as e:
        raise ValueError(f"Could not read NetCDF file: {e}")

    # Extract dimensions
    dimensions = list(ds.dims.keys())
    dim_sizes = {dim: ds.dims[dim] for dim in dimensions}

    # Identify coordinate variables and data variables
    coord_vars = list(ds.coords.keys())
    data_vars = list(ds.data_vars.keys())

    # Filter out boundary variables
    boundary_patterns = ['_bounds', '_bnds', '_bnd', '_bound']
    data_vars = [var for var in data_vars if not any(var.endswith(pattern) for pattern in boundary_patterns)]

    # Filter out scalar coordinates
    coord_vars = [var for var in coord_vars if var in dimensions and dim_sizes.get(var, 0) > 1]

    # Calculate total number of data points
    total_points = 1
    for dim in dimensions:
        if dim in coord_vars:
            total_points *= dim_sizes[dim]

    # Create flattened DataFrame structure
    df_data = {}
    column_names = []
    variable_types = {}
    measure_types = {}
    column_labels = {}
    netcdf_attrs = {}

    # Process coordinate variables (dimensions)
    for coord_var in coord_vars:
        if coord_var in ds.coords:
            column_names.append(coord_var)
            coord_data = ds.coords[coord_var].values

            # Store attributes
            netcdf_attrs[coord_var] = dict(ds.coords[coord_var].attrs)

            # Determine data type
            if np.issubdtype(coord_data.dtype, np.datetime64):
                variable_types[coord_var] = 'datetime'
                measure_types[coord_var] = 'scale'
                coord_data = pd.to_datetime(coord_data).astype(str)
            elif np.issubdtype(coord_data.dtype, np.integer):
                variable_types[coord_var] = 'numeric'
                measure_types[coord_var] = 'scale'
            elif np.issubdtype(coord_data.dtype, np.floating):
                variable_types[coord_var] = 'numeric'
                measure_types[coord_var] = 'scale'
            else:
                variable_types[coord_var] = 'string'
                measure_types[coord_var] = 'nominal'

            # Create label from attributes
            long_name = netcdf_attrs[coord_var].get('long_name', coord_var)
            units = netcdf_attrs[coord_var].get('units', '')
            column_labels[coord_var] = f"{long_name} ({units})" if units else long_name

    # Select first data variable for sample extraction
    if not data_vars:
        raise ValueError("No data variables found in NetCDF file")

    # Create meshgrid of coordinates for flattened data
    coord_arrays = []
    for coord_var in coord_vars:
        if coord_var in ds.coords:
            coord_arrays.append(ds.coords[coord_var].values)

    # Flatten coordinates using meshgrid
    if coord_arrays:
        meshgrid_arrays = np.meshgrid(*coord_arrays, indexing='ij')
        for i, coord_var in enumerate(coord_vars):
            if np.issubdtype(meshgrid_arrays[i].dtype, np.datetime64):
                df_data[coord_var] = pd.to_datetime(meshgrid_arrays[i].flatten()).astype(str).tolist()
            else:
                df_data[coord_var] = meshgrid_arrays[i].flatten().tolist()

    # Add data variables
    for data_var in data_vars:
        if data_var in ds.data_vars:
            column_names.append(data_var)
            netcdf_attrs[data_var] = dict(ds.data_vars[data_var].attrs)

            data_values = ds.data_vars[data_var].values

            if np.issubdtype(data_values.dtype, np.integer):
                variable_types[data_var] = 'numeric'
                measure_types[data_var] = 'scale'
            elif np.issubdtype(data_values.dtype, np.floating):
                variable_types[data_var] = 'numeric'
                measure_types[data_var] = 'scale'
            else:
                variable_types[data_var] = 'string'
                measure_types[data_var] = 'nominal'

            long_name = netcdf_attrs[data_var].get('long_name', data_var)
            units = netcdf_attrs[data_var].get('units', '')
            standard_name = netcdf_attrs[data_var].get('standard_name', '')

            if standard_name:
                column_labels[data_var] = f"{long_name} ({standard_name}) [{units}]" if units else f"{long_name} ({standard_name})"
            else:
                column_labels[data_var] = f"{long_name} [{units}]" if units else long_name

            df_data[data_var] = data_values.flatten().tolist()

    # Create full DataFrame
    df_full = pd.DataFrame(df_data)

    # Apply sample size limit
    if len(df_full) > sample_size:
        indices = np.linspace(0, len(df_full) - 1, sample_size, dtype=int)
        df = df_full.iloc[indices].copy()
        print(f"NetCDF: Sampled {sample_size} of {len(df_full)} total data points")
    else:
        df = df_full

    # Process data types
    for col in df.columns:
        if df[col].dtype.kind in 'biufc':
            df[col].fillna(pd.NA, inplace=True)
            try:
                if all(df[col].dropna().astype(float).map(float.is_integer)):
                    df[col] = df[col].astype('Int64')
            except (ValueError, TypeError):
                pass
        else:
            df[col].fillna(np.nan, inplace=True)

    # Replace NaN with None
    df.replace({np.nan: None, pd.NA: None}, inplace=True)

    # Classify variables
    identifier_vars = coord_vars.copy()
    measure_vars = data_vars.copy()
    attribute_vars = []

    # Simple metadata class for testing
    class NetCDFMetadata:
        def __init__(self):
            self.column_names = column_names
            self.column_labels = column_labels
            self.original_variable_types = variable_types
            self.variable_measure = measure_types
            self.number_rows = len(df)
            self.datafile = filename
            self.measure_vars = measure_vars
            self.identifier_vars = identifier_vars
            self.attribute_vars = attribute_vars
            self.file_format = 'netcdf'
            self.netcdf_attrs = netcdf_attrs
            self.dimensions = dimensions
            self.dim_sizes = dim_sizes
            self.total_points = total_points

    meta = NetCDFMetadata()
    ds.close()

    return df, meta, str(filename), total_points


# Run test
if __name__ == "__main__":
    nc_file = Path('files/tas_Amon_AWI-CM-1-1-MR_ssp585_r1i1p1f1_gn_201501-201512.nc')
    print(f'Testing with: {nc_file}')
    print(f'File exists: {nc_file.exists()}')

    if nc_file.exists():
        try:
            df, meta, filename, n_rows = read_netcdf(nc_file, sample_size=10)
            print(f'\n✓ Success! Read {len(df)} rows (sample)')
            print(f'✓ Total data points in file: {n_rows:,}')
            print(f'✓ Columns: {list(df.columns)}')
            print(f'\nFirst few rows:')
            print(df.head())
            print(f'\nMetadata:')
            print(f'  File format: {meta.file_format}')
            print(f'  Dimensions: {meta.dimensions}')
            print(f'  Dimension sizes: {meta.dim_sizes}')
            print(f'  Identifier vars (coordinates): {meta.identifier_vars}')
            print(f'  Measure vars (data): {meta.measure_vars}')
            print(f'\nVariable attributes:')
            for var in meta.column_names:
                if var in meta.netcdf_attrs and meta.netcdf_attrs[var]:
                    print(f'  {var}: {meta.netcdf_attrs[var]}')
        except Exception as e:
            print(f'✗ Error: {e}')
            import traceback
            traceback.print_exc()
    else:
        print('File not found!')
