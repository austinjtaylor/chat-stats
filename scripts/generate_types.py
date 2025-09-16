#!/usr/bin/env python3
"""
Generate TypeScript types from Pydantic models.

This script converts backend Pydantic models to TypeScript interfaces,
ensuring frontend-backend type consistency.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import tempfile
import re

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.db import (
    Team,
    Player,
    Game,
    PlayerGameStats,
    PlayerSeasonStats,
    TeamSeasonStats,
    StatsQuery,
)
from backend.models.api import (
    QueryRequest,
    QueryResponse,
    StatsResponse,
    PlayerSearchResponse,
    TeamSearchResponse,
    DataPoint,
)

# Map of Pydantic models to TypeScript file names
MODEL_GROUPS = {
    "db": {
        "models": [
            Team,
            Player,
            Game,
            PlayerGameStats,
            PlayerSeasonStats,
            TeamSeasonStats,
            StatsQuery,
        ],
        "output": "generated/db.ts",
    },
    "api": {
        "models": [
            QueryRequest,
            QueryResponse,
            StatsResponse,
            PlayerSearchResponse,
            TeamSearchResponse,
            DataPoint,
        ],
        "output": "generated/api.ts",
    },
}


def python_type_to_typescript(python_type: str) -> str:
    """Convert Python type hint to TypeScript type."""
    type_mapping = {
        "str": "string",
        "int": "number",
        "float": "number",
        "bool": "boolean",
        "None": "null",
        "NoneType": "null",
        "datetime": "string",  # ISO string
        "date": "string",
        "UUID": "string",
        "Any": "any",
    }

    # Handle optional types
    if "Optional[" in python_type:
        inner_type = python_type.replace("Optional[", "").rstrip("]")
        return f"{python_type_to_typescript(inner_type)} | null"

    # Handle list types
    if "List[" in python_type or "list[" in python_type:
        inner_type = re.search(r'\[(.*?)\]', python_type).group(1)
        return f"{python_type_to_typescript(inner_type)}[]"

    # Handle dict types
    if "Dict[" in python_type or "dict[" in python_type:
        return "Record<string, any>"

    return type_mapping.get(python_type, "any")


def generate_typescript_from_pydantic(model) -> str:
    """Generate TypeScript interface from a Pydantic model."""
    schema = model.model_json_schema()
    model_name = model.__name__

    # Get model description
    description = schema.get("description", f"TypeScript interface for {model_name}")

    # Start building the interface
    lines = []
    lines.append(f"/**")
    lines.append(f" * {description}")
    lines.append(f" */")
    lines.append(f"export interface {model_name} {{")

    # Process properties
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for prop_name, prop_schema in properties.items():
        # Get type
        prop_type = "any"

        if "type" in prop_schema:
            json_type = prop_schema["type"]
            if json_type == "string":
                prop_type = "string"
            elif json_type == "number" or json_type == "integer":
                prop_type = "number"
            elif json_type == "boolean":
                prop_type = "boolean"
            elif json_type == "array":
                items_type = prop_schema.get("items", {}).get("type", "any")
                if items_type == "string":
                    prop_type = "string[]"
                elif items_type == "number" or items_type == "integer":
                    prop_type = "number[]"
                else:
                    prop_type = "any[]"
            elif json_type == "object":
                prop_type = "Record<string, any>"

        # Handle nullable/optional
        if "anyOf" in prop_schema:
            # This is typically for Optional fields
            types = []
            for type_schema in prop_schema["anyOf"]:
                if type_schema.get("type") == "string":
                    types.append("string")
                elif type_schema.get("type") in ["number", "integer"]:
                    types.append("number")
                elif type_schema.get("type") == "boolean":
                    types.append("boolean")
                elif type_schema.get("type") == "array":
                    items = type_schema.get("items", {})
                    if items.get("type") == "string":
                        types.append("string[]")
                    elif items.get("type") in ["number", "integer"]:
                        types.append("number[]")
                    else:
                        types.append("any[]")
                elif type_schema.get("type") == "object":
                    types.append("Record<string, any>")
                elif type_schema.get("type") == "null":
                    types.append("null")

            prop_type = " | ".join([t for t in types if t])
            if not prop_type:
                prop_type = "any"

        # Determine if property is optional
        is_optional = prop_name not in required
        optional_marker = "?" if is_optional else ""

        # Add property to interface
        lines.append(f"  {prop_name}{optional_marker}: {prop_type};")

    lines.append("}")

    return "\n".join(lines)


def generate_types_for_group(group_name: str, group_config: Dict[str, Any]):
    """Generate TypeScript types for a group of models."""
    models = group_config["models"]
    output_path = Path("frontend/types") / group_config["output"]

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate TypeScript content
    typescript_content = f"""/**
 * AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
 *
 * This file is automatically generated from backend Pydantic models.
 * To update these types, run: npm run generate-types
 *
 * Source models are located in:
 * - backend/models/{group_name}.py
 */

"""

    # Generate interface for each model
    for model in models:
        typescript_content += generate_typescript_from_pydantic(model)
        typescript_content += "\n\n"

    # Write output
    output_path.write_text(typescript_content)
    print(f"✓ Generated {output_path}")
    return True


def create_index_file():
    """Create an index file that re-exports all generated types."""
    index_path = Path("frontend/types/generated/index.ts")
    index_path.parent.mkdir(parents=True, exist_ok=True)

    content = """/**
 * AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
 *
 * This file re-exports all generated types.
 * To update these types, run: npm run generate-types
 */

export * from './db';
export * from './api';
"""

    index_path.write_text(content)
    print(f"✓ Generated {index_path}")


def add_npm_script():
    """Add type generation script to package.json."""
    package_json_path = Path("frontend/package.json")

    if package_json_path.exists():
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)

        # Check if script already exists
        if "generate-types" not in package_data.get("scripts", {}):
            package_data["scripts"]["generate-types"] = "cd .. && uv run python scripts/generate_types.py"

            with open(package_json_path, 'w') as f:
                json.dump(package_data, f, indent=2)
                f.write('\n')  # Add newline at end of file

            print("✓ Added 'generate-types' script to package.json")


def main():
    """Main entry point."""
    print("Generating TypeScript types from Pydantic models...\n")

    success = True
    for group_name, group_config in MODEL_GROUPS.items():
        if not generate_types_for_group(group_name, group_config):
            success = False

    # Create index file
    create_index_file()

    # Add npm script
    add_npm_script()

    print("\n" + "=" * 50)
    if success:
        print("✅ Type generation completed successfully!")
        print("\nGenerated files:")
        print("  - frontend/types/generated/db.ts")
        print("  - frontend/types/generated/api.ts")
        print("  - frontend/types/generated/index.ts")
        print("\nUsage:")
        print("  Run 'npm run generate-types' from the frontend directory")
        print("  or 'uv run python scripts/generate_types.py' from the project root")
        print("\nNext steps:")
        print("  1. Review the generated types")
        print("  2. Update imports in frontend code to use generated types")
        print("  3. Run 'npm run typecheck' to verify compatibility")
    else:
        print("❌ Type generation encountered errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()