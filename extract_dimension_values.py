#!/usr/bin/env python3
"""
Extract dimension values from NetCDF file.

Extracts all values for a specified dimension (e.g., time, lat, lon)
and saves to JSON format.
"""

import json
import xarray as xr
import numpy as np
from pathlib import Path


def extract_dimension_values(netcdf_path: str, dimension: str, output_path: str):
    """
    Extract all values for a specified dimension.

    Args:
        netcdf_path: Path to NetCDF file
        dimension: Name of dimension to extract (e.g., 'time', 'lat', 'lon')
        output_path: Path to output JSON file
    """
    # Load NetCDF file
    ds = xr.open_dataset(netcdf_path)

    # Check if dimension exists
    if dimension not in ds.dims:
        available = list(ds.dims.keys())
        raise ValueError(f"Dimension '{dimension}' not found. Available dimensions: {available}")

    # Get dimension variable
    dim_var = ds[dimension]

    # Extract metadata
    metadata = {
        'dimension': dimension,
        'source_file': Path(netcdf_path).name,
        'length': len(dim_var),
        'attributes': dict(dim_var.attrs)
    }

    # Add data type info
    if hasattr(dim_var, 'dtype'):
        metadata['dtype'] = str(dim_var.dtype)

    # Extract dimension values
    values = []
    for idx, val in enumerate(dim_var.values):
        # Handle different data types
        if np.issubdtype(type(val), np.datetime64):
            # Convert datetime64 to ISO string
            value_str = np.datetime_as_string(val, unit='s')
            value_obj = {
                'index': int(idx),
                'value': value_str,
                'value_type': 'datetime'
            }
        elif isinstance(val, (np.floating, float)):
            # Handle floating point numbers
            value_obj = {
                'index': int(idx),
                'value': float(val),
                'value_type': 'float'
            }
        elif isinstance(val, (np.integer, int)):
            # Handle integers
            value_obj = {
                'index': int(idx),
                'value': int(val),
                'value_type': 'integer'
            }
        else:
            # Handle other types as strings
            value_obj = {
                'index': int(idx),
                'value': str(val),
                'value_type': 'string'
            }

        values.append(value_obj)

    # Build output structure
    output = {
        'metadata': metadata,
        'values': values,
        'count': len(values)
    }

    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Extracted {len(values)} values for dimension '{dimension}'")
    print(f"Output saved to {output_path}")
    print(f"\nDimension info:")
    print(f"  - Name: {dimension}")
    print(f"  - Length: {len(values)}")
    print(f"  - Type: {metadata.get('dtype', 'unknown')}")
    if metadata['attributes']:
        print(f"  - Attributes: {list(metadata['attributes'].keys())}")

    # Close dataset
    ds.close()

    return output


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python extract_dimension_values.py <netcdf_file> <dimension> [output_file]")
        print("\nExample:")
        print("  python extract_dimension_values.py data.nc time time_values.json")
        print("  python extract_dimension_values.py data.nc lat lat_values.json")
        print("  python extract_dimension_values.py data.nc lon lon_values.json")
        sys.exit(1)

    netcdf_path = sys.argv[1]
    dimension = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else f"{dimension}_values.json"

    # Extract dimension values
    try:
        extract_dimension_values(netcdf_path, dimension, output_path)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
