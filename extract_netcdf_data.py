#!/usr/bin/env python3
"""
Extract sample data from NetCDF file.

Extracts the first 5 spatial points (lon 0-4 at lat 0) for each time step
from the 'tas' variable and saves to JSON format.
"""

import json
import xarray as xr
import numpy as np
from pathlib import Path
from datetime import datetime


def extract_tas_sample(netcdf_path: str, output_path: str, num_points: int = 5):
    """
    Extract first N points per time step from tas variable.

    Args:
        netcdf_path: Path to NetCDF file
        output_path: Path to output JSON file
        num_points: Number of spatial points to extract per time step (default: 5)
    """
    # Load NetCDF file
    ds = xr.open_dataset(netcdf_path)

    # Get tas variable
    tas = ds['tas']

    # Extract metadata
    metadata = {
        'variable': 'tas',
        'long_name': tas.attrs.get('long_name', 'Near-Surface Air Temperature'),
        'standard_name': tas.attrs.get('standard_name', 'air_temperature'),
        'units': tas.attrs.get('units', 'K'),
        'source_file': Path(netcdf_path).name,
        'dimensions': {
            'time': len(ds['time']),
            'lat': len(ds['lat']),
            'lon': len(ds['lon'])
        },
        'sample_description': f'First {num_points} longitude points at first latitude for each time step'
    }

    # Extract data points
    data_points = []

    # Iterate through each time step
    for t_idx, time_val in enumerate(ds['time'].values):
        # Take first latitude
        lat_idx = 0
        lat_val = float(ds['lat'].values[lat_idx])

        # Take first N longitudes
        for lon_idx in range(min(num_points, len(ds['lon']))):
            lon_val = float(ds['lon'].values[lon_idx])

            # Extract tas value
            tas_value = float(tas.values[t_idx, lat_idx, lon_idx])

            # Convert numpy datetime64 to ISO format string
            time_str = np.datetime_as_string(time_val, unit='s')

            data_point = {
                'time': time_str,
                'time_index': int(t_idx),
                'lat': lat_val,
                'lat_index': int(lat_idx),
                'lon': lon_val,
                'lon_index': int(lon_idx),
                'value': tas_value
            }

            data_points.append(data_point)

    # Build output structure
    output = {
        'metadata': metadata,
        'data': data_points,
        'record_count': len(data_points)
    }

    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Extracted {len(data_points)} data points from {Path(netcdf_path).name}")
    print(f"Output saved to {output_path}")
    print(f"\nSample breakdown:")
    print(f"  - Time steps: {len(ds['time'])}")
    print(f"  - Points per time step: {num_points}")
    print(f"  - Total points: {len(data_points)}")

    # Close dataset
    ds.close()

    return output


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_netcdf_data.py <netcdf_file> [output_file] [num_points]")
        print("\nExample:")
        print("  python extract_netcdf_data.py data.nc tas_sample_data.json 5")
        sys.exit(1)

    netcdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "tas_sample_data.json"
    num_points = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    # Extract data
    extract_tas_sample(netcdf_path, output_path, num_points)


if __name__ == "__main__":
    main()
