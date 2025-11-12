#!/usr/bin/env python3
"""
Extract all data values for a variable from NetCDF file.

Extracts all data points for a specified variable (e.g., tas)
with their corresponding dimension coordinates.
"""

import json
import xarray as xr
import numpy as np
from pathlib import Path


def extract_variable_data(netcdf_path: str, variable: str, output_path: str,
                         max_records: int = None):
    """
    Extract all data values for a variable with dimension coordinates.

    Args:
        netcdf_path: Path to NetCDF file
        variable: Name of variable to extract (e.g., 'tas')
        output_path: Path to output JSON file
        max_records: Optional limit on number of records to extract
    """
    # Load NetCDF file
    ds = xr.open_dataset(netcdf_path)

    # Check if variable exists
    if variable not in ds.variables:
        available = list(ds.data_vars.keys())
        raise ValueError(f"Variable '{variable}' not found. Available variables: {available}")

    # Get variable
    var = ds[variable]

    # Extract metadata
    metadata = {
        'variable': variable,
        'source_file': Path(netcdf_path).name,
        'attributes': dict(var.attrs),
        'dimensions': list(var.dims),
        'shape': list(var.shape),
        'dtype': str(var.dtype),
        'total_values': int(np.prod(var.shape))
    }

    # Add units if available
    if 'units' in var.attrs:
        metadata['units'] = var.attrs['units']
    if 'long_name' in var.attrs:
        metadata['long_name'] = var.attrs['long_name']

    print(f"Extracting variable '{variable}'")
    print(f"  Dimensions: {metadata['dimensions']}")
    print(f"  Shape: {metadata['shape']}")
    print(f"  Total values: {metadata['total_values']:,}")

    if max_records:
        print(f"  Limiting to first {max_records:,} records")

    # Convert to DataFrame for easier handling
    df = var.to_dataframe().reset_index()

    # Limit records if specified
    if max_records:
        df = df.head(max_records)

    # Extract data points
    data_points = []

    for idx, row in df.iterrows():
        point = {}

        # Add dimension coordinates
        for dim in metadata['dimensions']:
            if dim in row.index:
                val = row[dim]
                # Handle datetime
                if isinstance(val, np.datetime64) or hasattr(val, 'isoformat'):
                    point[dim] = str(val)
                # Handle numeric
                elif isinstance(val, (np.floating, float)):
                    point[dim] = float(val)
                elif isinstance(val, (np.integer, int)):
                    point[dim] = int(val)
                else:
                    point[dim] = str(val)

        # Add variable value
        value = row[variable]
        if np.isnan(value):
            point['value'] = None
        else:
            point['value'] = float(value)

        data_points.append(point)

        # Progress indicator for large datasets
        if (idx + 1) % 10000 == 0:
            print(f"  Processed {idx + 1:,} records...")

    # Build output structure
    output = {
        'metadata': metadata,
        'data': data_points,
        'record_count': len(data_points)
    }

    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nExtracted {len(data_points):,} data points")
    print(f"Output saved to {output_path}")

    # Show file size
    file_size = Path(output_path).stat().st_size
    if file_size > 1024 * 1024:
        print(f"File size: {file_size / (1024 * 1024):.2f} MB")
    else:
        print(f"File size: {file_size / 1024:.2f} KB")

    # Close dataset
    ds.close()

    return output


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python extract_variable_data.py <netcdf_file> <variable> [output_file] [max_records]")
        print("\nExample:")
        print("  python extract_variable_data.py data.nc tas tas_all_data.json")
        print("  python extract_variable_data.py data.nc tas tas_sample.json 1000")
        sys.exit(1)

    netcdf_path = sys.argv[1]
    variable = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else f"{variable}_all_data.json"
    max_records = int(sys.argv[4]) if len(sys.argv) > 4 else None

    # Extract variable data
    try:
        extract_variable_data(netcdf_path, variable, output_path, max_records)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
