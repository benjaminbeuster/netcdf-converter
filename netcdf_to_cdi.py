#!/usr/bin/env python3
"""
NetCDF to DDI-CDI JSON-LD Converter

Converts NetCDF files to DDI-CDI JSON-LD format (metadata only).
"""

import json
import xarray as xr
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path


class NetCDFToCDIConverter:
    """Converts NetCDF metadata to DDI-CDI JSON-LD format."""

    def __init__(self, netcdf_path: str):
        """Initialize converter with NetCDF file path."""
        self.netcdf_path = Path(netcdf_path)
        self.ds = xr.open_dataset(netcdf_path)
        self.base_id = "#"

    def extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from NetCDF file."""
        metadata = {
            'filename': self.netcdf_path.name,
            'dimensions': dict(self.ds.sizes),
            'variables': {},
            'global_attrs': dict(self.ds.attrs),
            'coordinate_vars': [],
            'data_vars': [],
            'boundary_vars': [],
            'excluded_vars': []
        }

        # First pass: identify boundary/auxiliary variables
        boundary_vars = set()

        # Check for variables referenced as bounds in coordinate attributes
        for var_name, var in self.ds.variables.items():
            if 'bounds' in var.attrs:
                bounds_var = var.attrs['bounds']
                boundary_vars.add(bounds_var)

        # Also check for common boundary naming patterns
        for var_name in self.ds.variables.keys():
            if var_name.endswith('_bnds') or var_name.endswith('_bounds'):
                boundary_vars.add(var_name)

        # Identify scalar coordinates (to be excluded)
        scalar_coords = set()
        for var_name, var in self.ds.variables.items():
            # Check if it's a coordinate with no dimensions or size 1
            if var_name in self.ds.coords and (len(var.dims) == 0 or var.size == 1):
                scalar_coords.add(var_name)

        # Second pass: classify variables
        for var_name, var in self.ds.variables.items():
            var_info = {
                'name': var_name,
                'dimensions': list(var.dims),
                'dtype': str(var.dtype),
                'attrs': dict(var.attrs),
                'shape': var.shape
            }
            metadata['variables'][var_name] = var_info

            # Apply filtering rules
            # Rule 1 & 2: Exclude boundary variables and scalar coordinates
            if var_name in boundary_vars or var_name in scalar_coords:
                metadata['excluded_vars'].append(var_name)
            # Classify remaining variables
            elif var_name in self.ds.coords:
                metadata['coordinate_vars'].append(var_name)
            else:
                metadata['data_vars'].append(var_name)

        # Calculate record count (for flattened long format)
        record_count = 1
        for dim_size in metadata['dimensions'].values():
            record_count *= dim_size
        metadata['record_count'] = record_count

        return metadata

    def map_netcdf_dtype_to_xsd(self, dtype: str) -> str:
        """Map NetCDF data type to XML Schema data type."""
        dtype_map = {
            'float32': 'http://www.w3.org/2001/XMLSchema#float',
            'float64': 'http://www.w3.org/2001/XMLSchema#double',
            'int32': 'http://www.w3.org/2001/XMLSchema#int',
            'int64': 'http://www.w3.org/2001/XMLSchema#long',
            'int16': 'http://www.w3.org/2001/XMLSchema#short',
            'int8': 'http://www.w3.org/2001/XMLSchema#byte',
            'uint32': 'http://www.w3.org/2001/XMLSchema#unsignedInt',
            'uint64': 'http://www.w3.org/2001/XMLSchema#unsignedLong',
            'uint16': 'http://www.w3.org/2001/XMLSchema#unsignedShort',
            'uint8': 'http://www.w3.org/2001/XMLSchema#unsignedByte',
            '<U': 'http://www.w3.org/2001/XMLSchema#string',
            'object': 'http://www.w3.org/2001/XMLSchema#string',
        }

        # Handle string types
        if dtype.startswith('<U') or dtype.startswith('|S') or dtype == 'object':
            return 'http://www.w3.org/2001/XMLSchema#string'

        return dtype_map.get(dtype, 'http://www.w3.org/2001/XMLSchema#string')

    def create_physical_dataset(self, metadata: Dict) -> Dict:
        """Create PhysicalDataSet component."""
        return {
            "@id": f"{self.base_id}physicalDataSet",
            "@type": "PhysicalDataSet",
            "allowsDuplicates": False,
            "physicalFileName": metadata['filename'],
            "correspondsTo_DataSet": f"{self.base_id}dimensionalDataSet",
            "formats": f"{self.base_id}dataStore",
            "has_PhysicalRecordSegment": [f"{self.base_id}physicalRecordSegment"]
        }

    def create_data_store(self, metadata: Dict) -> Dict:
        """Create DataStore component."""
        return {
            "@id": f"{self.base_id}dataStore",
            "@type": "DataStore",
            "allowsDuplicates": False,
            "recordCount": metadata['record_count'],
            "has_LogicalRecord": [f"{self.base_id}logicalRecord"]
        }

    def create_logical_record(self, metadata: Dict) -> Dict:
        """Create LogicalRecord component."""
        # Get all non-excluded variables
        all_vars = metadata['coordinate_vars'] + metadata['data_vars']

        return {
            "@id": f"{self.base_id}logicalRecord",
            "@type": "LogicalRecord",
            "has_InstanceVariable": [
                f"{self.base_id}instanceVariable-{var_name}"
                for var_name in all_vars
            ]
        }

    def create_physical_record_segment(self, metadata: Dict) -> Dict:
        """Create PhysicalRecordSegment component."""
        return {
            "@id": f"{self.base_id}physicalRecordSegment",
            "@type": "PhysicalRecordSegment",
            "mapsTo": f"{self.base_id}logicalRecord",
            "has_PhysicalSegmentLayout": f"{self.base_id}physicalSegmentLayout"
        }

    def create_instance_variable(self, var_name: str, var_info: Dict,
                                 is_coordinate: bool) -> Dict:
        """Create InstanceVariable component."""
        instance_var = {
            "@id": f"{self.base_id}instanceVariable-{var_name}",
            "@type": "InstanceVariable",
            "name": {
                "@type": "ObjectName",
                "name": var_name
            },
            "takesSubstantiveValuesFrom_SubstantiveValueDomain":
                f"{self.base_id}substantiveValueDomain-{var_name}"
        }

        # Add display label from long_name or standard_name
        if 'long_name' in var_info['attrs']:
            instance_var["displayLabel"] = {
                "@type": "LabelForDisplay",
                "locationVariant": {
                    "@type": "ControlledVocabularyEntry",
                    "entryValue": var_info['attrs']['long_name']
                }
            }
        elif 'standard_name' in var_info['attrs']:
            instance_var["displayLabel"] = {
                "@type": "LabelForDisplay",
                "locationVariant": {
                    "@type": "ControlledVocabularyEntry",
                    "entryValue": var_info['attrs']['standard_name']
                }
            }

        # Add physical data type
        instance_var["physicalDataType"] = {
            "@type": "ControlledVocabularyEntry",
            "entryValue": var_info['dtype']
        }

        return instance_var

    def create_substantive_value_domain(self, var_name: str,
                                        var_info: Dict) -> Dict:
        """Create SubstantiveValueDomain component."""
        value_domain = {
            "@id": f"{self.base_id}substantiveValueDomain-{var_name}",
            "@type": "SubstantiveValueDomain",
            "recommendedDataType": {
                "@type": "ControlledVocabularyEntry",
                "entryValue": self.map_netcdf_dtype_to_xsd(var_info['dtype'])
            },
            "isDescribedBy": f"{self.base_id}substantiveValueAndConceptDescription-{var_name}"
        }

        return value_domain

    def create_value_and_concept_description(self, var_name: str,
                                             var_info: Dict) -> Dict:
        """Create ValueAndConceptDescription component."""
        description = {
            "@id": f"{self.base_id}substantiveValueAndConceptDescription-{var_name}",
            "@type": "ValueAndConceptDescription",
            "classificationLevel": "Continuous"
        }

        return description

    def create_dimensional_dataset(self, metadata: Dict) -> Dict:
        """Create DimensionalDataSet component."""
        return {
            "@id": f"{self.base_id}dimensionalDataSet",
            "@type": "DimensionalDataSet",
            "isStructuredBy": f"{self.base_id}dimensionalDataStructure"
        }

    def create_dimensional_data_structure(self, metadata: Dict) -> Dict:
        """Create DimensionalDataStructure component."""
        # Create component references (excluding filtered variables)
        # - Coordinate variables -> DimensionComponent
        # - Data variables -> QualifiedMeasure
        # - Boundary variables -> AttributeComponent (excluded now)
        component_refs = []

        # Add coordinate variables as dimension components
        for coord_var in metadata['coordinate_vars']:
            component_refs.append(f"{self.base_id}dimensionComponent-{coord_var}")

        # Add data variables as qualified measures
        for data_var in metadata['data_vars']:
            component_refs.append(f"{self.base_id}qualifiedMeasure-{data_var}")

        # Note: boundary_vars are now excluded, so we don't add them

        return {
            "@id": f"{self.base_id}dimensionalDataStructure",
            "@type": "DimensionalDataStructure",
            "has_DataStructureComponent": component_refs,
            "has_PrimaryKey": f"{self.base_id}primaryKey"
        }

    def create_dimension_component(self, var_name: str, position: int) -> Dict:
        """Create DimensionComponent for coordinate variables."""
        return {
            "@id": f"{self.base_id}dimensionComponent-{var_name}",
            "@type": "DimensionComponent",
            "isDefinedBy_RepresentedVariable": f"{self.base_id}instanceVariable-{var_name}"
        }

    def create_qualified_measure(self, var_name: str, position: int) -> Dict:
        """Create QualifiedMeasure for data variables."""
        return {
            "@id": f"{self.base_id}qualifiedMeasure-{var_name}",
            "@type": "QualifiedMeasure",
            "isDefinedBy_RepresentedVariable": f"{self.base_id}instanceVariable-{var_name}"
        }

    def create_attribute_component(self, var_name: str, position: int) -> Dict:
        """Create AttributeComponent for boundary/auxiliary variables."""
        return {
            "@id": f"{self.base_id}attributeComponent-{var_name}",
            "@type": "AttributeComponent",
            "isDefinedBy_RepresentedVariable": f"{self.base_id}instanceVariable-{var_name}"
        }

    def create_component_position(self, var_name: str, position: int) -> Dict:
        """Create ComponentPosition."""
        return {
            "@id": f"{self.base_id}componentPosition-{var_name}",
            "@type": "ComponentPosition",
            "value": position
        }

    def create_primary_key(self, metadata: Dict) -> Dict:
        """Create PrimaryKey component with all dimension components."""
        primary_key_component_refs = []

        # Add all dimension components to the primary key
        for coord_var in metadata['coordinate_vars']:
            primary_key_component_refs.append(f"{self.base_id}primaryKeyComponent-{coord_var}")

        return {
            "@id": f"{self.base_id}primaryKey",
            "@type": "PrimaryKey",
            "isComposedOf": primary_key_component_refs
        }

    def create_primary_key_component(self, var_name: str) -> Dict:
        """Create PrimaryKeyComponent that corresponds to a DimensionComponent."""
        return {
            "@id": f"{self.base_id}primaryKeyComponent-{var_name}",
            "@type": "PrimaryKeyComponent",
            "correspondsTo_DataStructureComponent": f"{self.base_id}dimensionComponent-{var_name}"
        }

    def create_physical_segment_layout(self) -> Dict:
        """Create PhysicalSegmentLayout component."""
        return {
            "@id": f"{self.base_id}physicalSegmentLayout",
            "@type": "PhysicalSegmentLayout",
            "allowsDuplicates": False,
            "formats": f"{self.base_id}logicalRecord",
            "isDelimited": False,
            "isFixedWidth": False,
            "delimiter": ""
        }

    def convert(self) -> Dict:
        """Convert NetCDF to DDI-CDI JSON-LD."""
        metadata = self.extract_metadata()

        # Build DDICDIModels array
        models = []

        # Add core components
        models.append(self.create_physical_dataset(metadata))
        models.append(self.create_data_store(metadata))
        models.append(self.create_logical_record(metadata))
        models.append(self.create_physical_record_segment(metadata))
        models.append(self.create_dimensional_dataset(metadata))
        models.append(self.create_dimensional_data_structure(metadata))
        models.append(self.create_physical_segment_layout())

        # Add primary key components
        models.append(self.create_primary_key(metadata))
        for coord_var in metadata['coordinate_vars']:
            models.append(self.create_primary_key_component(coord_var))

        # Add instance variables and value domains (skip excluded variables)
        position = 1
        for var_name, var_info in metadata['variables'].items():
            is_coordinate = var_name in metadata['coordinate_vars']
            is_boundary = var_name in metadata['boundary_vars']
            is_data_var = var_name in metadata['data_vars']
            is_excluded = var_name in metadata['excluded_vars']

            # Skip excluded variables
            if is_excluded:
                continue

            # Create instance variable and value domain for all non-excluded variables
            models.append(self.create_instance_variable(var_name, var_info, is_coordinate))
            models.append(self.create_substantive_value_domain(var_name, var_info))
            models.append(self.create_value_and_concept_description(var_name, var_info))

            # Create appropriate structure component based on variable type:
            # - Coordinate variables -> DimensionComponent
            # - Data variables -> QualifiedMeasure
            # - Boundary variables -> AttributeComponent (won't occur since boundaries are excluded)
            if is_coordinate:
                models.append(self.create_dimension_component(var_name, position))
            elif is_data_var:
                models.append(self.create_qualified_measure(var_name, position))
            elif is_boundary:
                models.append(self.create_attribute_component(var_name, position))

            position += 1

        # Build final JSON-LD document
        cdi_document = {
            "@context": [
                "https://docs.ddialliance.org/DDI-CDI/1.0/model/encoding/json-ld/ddi-cdi.jsonld",
                {
                    "skos": "http://www.w3.org/2004/02/skos/core#"
                }
            ],
            "DDICDIModels": models,
            "@included": []  # Can add SKOS concepts here if needed
        }

        return cdi_document

    def convert_and_save(self, output_path: str):
        """Convert and save to file."""
        cdi_document = self.convert()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cdi_document, f, indent=2, ensure_ascii=False)

        print(f"Converted {self.netcdf_path.name} to {output_path}")
        print(f"Generated {len(cdi_document['DDICDIModels'])} DDI-CDI components")

    def __del__(self):
        """Close the dataset when done."""
        if hasattr(self, 'ds'):
            self.ds.close()


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python netcdf_to_cdi.py <netcdf_file> [output_file]")
        print("\nExample:")
        print("  python netcdf_to_cdi.py data.nc output.jsonld")
        sys.exit(1)

    netcdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.jsonld"

    # Convert
    converter = NetCDFToCDIConverter(netcdf_path)
    converter.convert_and_save(output_path)


if __name__ == "__main__":
    main()
