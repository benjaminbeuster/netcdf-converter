# NetCDF to DDI-CDI Converter

A Python tool for converting NetCDF files to DDI-CDI (Data Documentation Initiative - Cross Domain Integration) JSON-LD format.

## Overview

This converter reads NetCDF files and extracts their **metadata structure** (not data values) into DDI-CDI JSON-LD format. It's designed to help document and catalog NetCDF datasets in a standardized, interoperable way.

## Features

- **Metadata-only conversion**: Extracts structural metadata without including actual data values
- **Flattened representation**: Represents multidimensional arrays as long-format tabular structures
- **CF Conventions support**: Handles CF (Climate and Forecast) conventions metadata
- **Comprehensive mapping**: Converts NetCDF components to DDI-CDI equivalents:
  - Variables → InstanceVariable
  - Dimensions → Identifier/Measure Components
  - Attributes → ValueAndConceptDescription
  - Data types → XML Schema types
  - Global attributes → PhysicalDataSet properties

## Installation

### 1. Clone or download this repository

```bash
cd /path/to/netcdf
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python netcdf_to_cdi.py <netcdf_file> [output_file]
```

### Examples

Convert a NetCDF file to DDI-CDI JSON-LD:

```bash
python netcdf_to_cdi.py data.nc output.jsonld
```

Convert the example climate data file:

```bash
python netcdf_to_cdi.py files/tas_Amon_AWI-CM-1-1-MR_ssp585_r1i1p1f1_gn_201501-201512.nc climate_cdi.jsonld
```

If no output file is specified, defaults to `output.jsonld`:

```bash
python netcdf_to_cdi.py data.nc
```

## Output Structure

The converter generates DDI-CDI JSON-LD with the following components:

### Core Components
- **PhysicalDataSet**: File-level metadata
- **DataStore**: Record count and storage information
- **LogicalRecord**: Variable organization
- **WideDataSet**: Dataset definition
- **WideDataStructure**: Structure definition

### Per-Variable Components
- **InstanceVariable**: Variable metadata (name, type, labels)
- **SubstantiveValueDomain**: Data type and constraints
- **ValueAndConceptDescription**: Units and descriptions
- **ComponentPosition**: Variable ordering
- **IdentifierComponent**: For coordinate variables (time, lat, lon)
- **MeasureComponent**: For data variables (temperature, etc.)
- **PrimaryKeyComponent**: Composite key components

## Example Output

For a NetCDF file with variables `time`, `lat`, `lon`, and `tas` (temperature), the converter generates:

```json
{
  "@context": [
    "https://docs.ddialliance.org/DDI-CDI/1.0/model/encoding/json-ld/ddi-cdi.jsonld",
    {
      "skos": "http://www.w3.org/2004/02/skos/core#"
    }
  ],
  "DDICDIModels": [
    {
      "@id": "#physicalDataSet",
      "@type": "PhysicalDataSet",
      "physicalFileName": "data.nc",
      "recordCount": 884736
    },
    {
      "@id": "#instanceVariable-tas",
      "@type": "InstanceVariable",
      "name": { "name": "tas" },
      "displayLabel": {
        "locationVariant": {
          "entryValue": "Near-Surface Air Temperature"
        }
      },
      "physicalDataType": { "entryValue": "float32" }
    }
    ...
  ]
}
```

## Data Type Mapping

NetCDF types are mapped to XML Schema types:

| NetCDF Type | XML Schema Type |
|-------------|-----------------|
| float32 | xsd:float |
| float64 | xsd:double |
| int32 | xsd:int |
| int64 | xsd:long |
| string | xsd:string |

## Coordinate vs Data Variables

The converter distinguishes between:

- **Coordinate variables** (e.g., time, lat, lon): Treated as `IdentifierComponent` and included in the `PrimaryKey`
- **Data variables** (e.g., temperature, pressure): Treated as `MeasureComponent`

## Record Count Calculation

For flattened long-format representation, the record count is calculated as the product of all dimension sizes:

```
recordCount = dim1_size × dim2_size × dim3_size × ...
```

Example: A file with dimensions `time=12, lat=192, lon=384` has `12 × 192 × 384 = 884,736` records.

## Limitations

### Current Version (v1.0)
- **Metadata only**: Does not include actual data values (no `InstanceValue` objects)
- **Simple flattening**: Represents multidimensional arrays as flat tables
- **No SKOS concepts**: Does not generate SKOS concept schemes for CF standard_names (yet)
- **Basic attributes**: Extracts common attributes but may miss specialized metadata

### Known Issues
- Nested groups in NetCDF-4 files are not fully supported
- Complex CF cell_methods are not parsed
- User-defined types are not handled

## Dependencies

- **xarray** (>= 2023.0.0): High-level NetCDF interface
- **netCDF4** (>= 1.6.0): Low-level NetCDF reading
- **h5netcdf** (>= 1.2.0): Alternative HDF5-based backend
- **numpy** (>= 1.24.0): Array operations

## File Structure

```
netcdf/
├── files/
│   ├── cdi-examples/
│   │   └── ESS11-subset_DDICDI.jsonld  # Reference DDI-CDI example
│   └── tas_Amon_AWI-CM-1-1-MR_ssp585_r1i1p1f1_gn_201501-201512.nc
├── venv/                                # Virtual environment (created)
├── netcdf_to_cdi.py                     # Main converter script
├── requirements.txt                      # Python dependencies
├── output.jsonld                         # Generated output (example)
└── README.md                             # This file
```

## Development

### Adding New Features

The converter is organized as a single class with modular methods:

```python
class NetCDFToCDIConverter:
    def extract_metadata(self)          # NetCDF metadata extraction
    def convert(self)                    # Main conversion logic
    def create_<component>(self)         # Individual DDI-CDI component builders
```

To add new DDI-CDI components:
1. Add a `create_<component>()` method
2. Call it from the `convert()` method
3. Add the result to the `models` list

### Testing

Test with different NetCDF files:

```bash
# Climate model data
python netcdf_to_cdi.py files/climate_data.nc

# Satellite data
python netcdf_to_cdi.py files/satellite_obs.nc

# Oceanographic data
python netcdf_to_cdi.py files/ocean_data.nc
```

## Future Enhancements

Potential improvements for future versions:

1. **Data value export**: Option to include actual data (sample or full)
2. **SKOS concept schemes**: Generate concepts from CF standard_names
3. **Rich CF metadata**: Parse cell_methods, coordinate systems, grids
4. **Group support**: Handle NetCDF-4 group hierarchies
5. **Validation**: DDI-CDI schema validation
6. **CLI options**: Configurable behavior (verbosity, filters, mappings)
7. **Multiple output formats**: Support other DDI versions or formats

## References

- [DDI-CDI 1.0 Specification](https://docs.ddialliance.org/DDI-CDI/1.0/)
- [CF Conventions](https://cfconventions.org/)
- [NetCDF Documentation](https://www.unidata.ucar.edu/software/netcdf/)
- [xarray Documentation](https://docs.xarray.dev/)

## License

This tool is provided as-is for educational and research purposes.

## Contributing

Contributions are welcome! Areas for improvement:
- Support for additional NetCDF conventions (COARDS, etc.)
- Enhanced metadata extraction
- DDI-CDI validation
- Unit tests
- Performance optimizations for large files
