"""
Soul Registry - Load, Validate, Cache Soul Specs

Implements Soul Spec registry per:
runtime_specs/01_identity_anchor_soul_spec.md §3.2

Author: 心屿团队
Created: 2026-05-17
"""

import yaml
from pathlib import Path
from typing import Dict, Optional
from pydantic import ValidationError
import structlog

from .schema_validator import SoulSpec, validate_soul_spec_yaml

logger = structlog.get_logger()


class SoulRegistry:
    """
    Soul Registry - Singleton registry for Soul Specs.

    Responsibilities (per §3.2):
    - Load all Soul Spec YAML files at startup
    - Validate each spec through Schema Validator
    - Cache validated specs in memory
    - Provide version-controlled read-only access

    Design principles (per §2.1):
    - P-2: Soul Spec is declarative, not generative
    - P-3: All Soul Specs must pass strict schema validation
    - P-4: Each (user, character) locks to a specific version
    - P-10: Runtime agents cannot modify Soul Spec

    Lifecycle:
    - Bootstrap: Service startup
    - Cache: In-process memory (immutable)
    - Invalidation: Service restart/deploy only
    """

    def __init__(self, soul_specs_dir: Optional[Path] = None):
        """
        Initialize Soul Registry.

        Args:
            soul_specs_dir: Path to soul_specs/ directory
                           Defaults to {repo_root}/soul_specs/
        """
        if soul_specs_dir is None:
            # Auto-detect from current file location
            # /heart/backend/heart/ss01_soul/registry.py -> /heart/soul_specs/
            current_file = Path(__file__)
            repo_root = current_file.parent.parent.parent.parent
            soul_specs_dir = repo_root / "soul_specs"

        self.soul_specs_dir = Path(soul_specs_dir)
        self._registry: Dict[str, Dict[str, SoulSpec]] = {}
        # Structure: {character_id: {version: SoulSpec}}

        logger.info(
            "soul_registry_init",
            soul_specs_dir=str(self.soul_specs_dir),
        )

    def load_all(self) -> None:
        """
        Load and validate all Soul Spec YAML files.

        File structure expected:
            soul_specs/
            ├── rin/
            │   └── v1.0.0.yaml
            └── dorothy/
                └── v1.0.0.yaml

        Raises:
            FileNotFoundError: If soul_specs_dir doesn't exist
            ValidationError: If any spec fails validation
            RuntimeError: If any YAML parsing fails
        """
        if not self.soul_specs_dir.exists():
            raise FileNotFoundError(f"Soul specs directory not found: {self.soul_specs_dir}")

        logger.info("soul_registry_load_start", dir=str(self.soul_specs_dir))

        loaded_count = 0
        failed_specs = []

        # Iterate over character directories
        for character_dir in self.soul_specs_dir.iterdir():
            if not character_dir.is_dir():
                continue

            character_id = character_dir.name

            # Skip hidden directories
            if character_id.startswith(".") or character_id.startswith("_"):
                continue

            logger.info("soul_registry_scan_character", character_id=character_id)

            # Load all YAML files in character directory
            for yaml_file in character_dir.glob("*.yaml"):
                try:
                    spec = self._load_and_validate(yaml_file)

                    # Verify character_id matches directory name
                    if spec.character_id != character_id:
                        raise ValueError(
                            f"character_id '{spec.character_id}' in YAML "
                            f"does not match directory name '{character_id}'"
                        )

                    # Store in registry
                    if character_id not in self._registry:
                        self._registry[character_id] = {}

                    self._registry[character_id][spec.spec_version] = spec
                    loaded_count += 1

                    logger.info(
                        "soul_spec_loaded",
                        character_id=character_id,
                        version=spec.spec_version,
                        file=yaml_file.name,
                    )

                except (ValidationError, ValueError, yaml.YAMLError) as e:
                    logger.error(
                        "soul_spec_load_failed",
                        character_id=character_id,
                        file=yaml_file.name,
                        error=str(e),
                    )
                    failed_specs.append(
                        {
                            "character_id": character_id,
                            "file": str(yaml_file),
                            "error": str(e),
                        }
                    )

        if failed_specs:
            error_msg = f"Failed to load {len(failed_specs)} Soul Spec(s):\n"
            for spec in failed_specs:
                error_msg += f"  - {spec['file']}: {spec['error']}\n"
            raise RuntimeError(error_msg)

        logger.info(
            "soul_registry_load_complete",
            total_specs=loaded_count,
            characters=list(self._registry.keys()),
        )

    def _load_and_validate(self, yaml_file: Path) -> SoulSpec:
        """
        Load and validate a single Soul Spec YAML file.

        Args:
            yaml_file: Path to YAML file

        Returns:
            Validated SoulSpec instance

        Raises:
            ValidationError: If validation fails
            yaml.YAMLError: If YAML parsing fails
        """
        logger.debug("soul_spec_parse", file=str(yaml_file))

        # Load YAML with safe_load (NEVER yaml.load)
        with open(yaml_file, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        # Validate through Pydantic
        spec = validate_soul_spec_yaml(yaml_data)

        return spec

    def get_soul(
        self,
        character_id: str,
        version: Optional[str] = None,
    ) -> SoulSpec:
        """
        Get Soul Spec by character_id and version.

        Args:
            character_id: Character identifier (e.g., "rin", "dorothy")
            version: Spec version (e.g., "1.0.0"). If None, returns latest.

        Returns:
            SoulSpec instance (read-only)

        Raises:
            KeyError: If character_id or version not found

        Example:
            >>> registry = SoulRegistry()
            >>> registry.load_all()
            >>> rin_spec = registry.get_soul("rin", "1.0.0")
            >>> print(rin_spec.identity_anchor.archetype)
        """
        if character_id not in self._registry:
            available = list(self._registry.keys())
            raise KeyError(f"Character '{character_id}' not found. Available: {available}")

        character_versions = self._registry[character_id]

        if version is None:
            # Return latest version (highest semver)
            version = max(character_versions.keys())
            logger.debug(
                "soul_get_latest",
                character_id=character_id,
                version=version,
            )

        if version not in character_versions:
            available_versions = list(character_versions.keys())
            raise KeyError(
                f"Version '{version}' not found for character '{character_id}'. "
                f"Available versions: {available_versions}"
            )

        return character_versions[version]

    def list_characters(self) -> list[str]:
        """
        List all available character IDs.

        Returns:
            List of character_id strings
        """
        return list(self._registry.keys())

    def list_versions(self, character_id: str) -> list[str]:
        """
        List all available versions for a character.

        Args:
            character_id: Character identifier

        Returns:
            List of version strings

        Raises:
            KeyError: If character_id not found
        """
        if character_id not in self._registry:
            raise KeyError(f"Character '{character_id}' not found")

        return list(self._registry[character_id].keys())

    def get_all_souls(self) -> Dict[str, Dict[str, SoulSpec]]:
        """
        Get all loaded Soul Specs.

        Returns:
            Dict mapping {character_id: {version: SoulSpec}}

        Warning:
            This returns the internal registry. Do NOT modify.
        """
        return self._registry


# Singleton instance (lazy-initialized)
_soul_registry: Optional[SoulRegistry] = None


def get_soul_registry(soul_specs_dir: Optional[Path] = None) -> SoulRegistry:
    """
    Get singleton Soul Registry instance.

    Args:
        soul_specs_dir: Optional path override (mainly for testing)

    Returns:
        Singleton SoulRegistry instance

    Note:
        Registry is auto-loaded on first access.
    """
    global _soul_registry

    if _soul_registry is None:
        _soul_registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        _soul_registry.load_all()

    return _soul_registry
