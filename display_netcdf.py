#!/usr/bin/env python3
"""
NetCDF Display Tool using ncdump-rich

Displays NetCDF file metadata in a formatted way and saves to a text file.
"""

import sys
import subprocess
from pathlib import Path


def display_netcdf(netcdf_path: str, output_path: str = None, long_format: bool = True):
    """
    Display NetCDF file metadata using ncdump-rich and save to text file.

    Args:
        netcdf_path: Path to the NetCDF file
        output_path: Path to save the output text file (optional)
        long_format: If True, use --long to print all info (default: True)
    """
    netcdf_file = Path(netcdf_path)

    if not netcdf_file.exists():
        print(f"Error: File not found: {netcdf_path}")
        sys.exit(1)

    # Set default output path if not provided
    if output_path is None:
        output_path = netcdf_file.stem + "_display.txt"

    print(f"Reading NetCDF file: {netcdf_file.name}")
    print(f"Generating formatted output...")

    try:
        # Build the ncdump-rich command
        # Use --no-format to get plain text output (better for saving to file)
        cmd = ["ncdump-rich", str(netcdf_file), "--no-format"]

        if long_format:
            cmd.append("--long")

        # Run ncdump-rich and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"NetCDF File: {netcdf_file.name}\n")
            f.write("=" * 80 + "\n\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\nWarnings/Errors:\n")
                f.write(result.stderr)

        print(f"Output saved to: {output_path}")

        # Also display to console with formatting
        print("\n" + "=" * 80)
        print("NetCDF File Contents:")
        print("=" * 80 + "\n")

        # Display with rich formatting to console
        cmd_display = ["ncdump-rich", str(netcdf_file)]
        if long_format:
            cmd_display.append("--long")

        subprocess.run(cmd_display, check=True)

        # Print file info
        file_size = netcdf_file.stat().st_size
        if file_size < 1024:
            size_str = f"{file_size} bytes"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"

        print(f"\n{'=' * 80}")
        print(f"File size: {size_str}")
        print(f"Output saved to: {output_path}")

    except subprocess.CalledProcessError as e:
        print(f"Error running ncdump-rich: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: ncdump-rich command not found.")
        print("Please install it with: pip install ncdump-rich")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing NetCDF file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python display_netcdf.py <netcdf_file> [output_file]")
        print("\nExample:")
        print("  python display_netcdf.py data.nc")
        print("  python display_netcdf.py data.nc output.txt")
        print("\nThis tool uses ncdump-rich to display NetCDF metadata in a formatted way.")
        sys.exit(1)

    netcdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    display_netcdf(netcdf_path, output_path)


if __name__ == "__main__":
    main()
