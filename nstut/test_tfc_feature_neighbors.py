#!/usr/bin/env python3
"""Guard TFC's 3x3 feature-biome neighborhood in DH Forge world generation.

Run from any working directory: python nstut/test_tfc_feature_neighbors.py
The geometry test mirrors DhChunkGenerator's four overlapping odd-sized
generation regions around a requested even-sized (4x4) batch.
"""
from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "common/src/main/java/com/seibel/distanthorizons/common/wrappers/worldGeneration/DhChunkGenerator.java"


def generated_and_decorated_chunks(target_size: int, biome_margin: int):
    assert target_size > 0 and target_size % 2 == 0
    region_size = target_size - 1 + 2 * biome_margin
    decorated = set()
    regions = []
    for offset_x in (0, 1):
        for offset_z in (0, 1):
            origin_x = offset_x - biome_margin
            origin_z = offset_z - biome_margin
            all_biomes = {
                (origin_x + x, origin_z + z)
                for x in range(region_size)
                for z in range(region_size)
            }
            decoration_targets = {
                (origin_x + x, origin_z + z)
                for x in range(biome_margin, region_size - biome_margin)
                for z in range(biome_margin, region_size - biome_margin)
            }
            regions.append((all_biomes, decoration_targets))
            decorated.update(decoration_targets)
    return decorated, regions


def test_border_geometry() -> None:
    requested = {(x, z) for x in range(4) for z in range(4)}
    decorated, regions = generated_and_decorated_chunks(4, 1)
    assert decorated == requested, (decorated ^ requested)
    for generated_biomes, interior in regions:
        for x, z in interior:
            neighborhood = {
                (x + dx, z + dz)
                for dx in (-1, 0, 1)
                for dz in (-1, 0, 1)
            }
            assert neighborhood <= generated_biomes, (x, z, neighborhood - generated_biomes)

    # The previous zero-margin implementation had uninitialized neighbor biomes.
    _, broken_regions = generated_and_decorated_chunks(4, 0)
    assert any(
        (x + dx, z + dz) not in generated_biomes
        for generated_biomes, interior in broken_regions
        for x, z in interior
        for dx in (-1, 0, 1)
        for dz in (-1, 0, 1)
    )


def test_source_wiring() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "requiresTfcFeatureNeighbors(this.globalParams.generator) ? 1 : 0" in source
    assert "Math.max(MAX_WORLD_GEN_CHUNK_BORDER_NEEDED, this.featureNeighborBorder)" in source
    assert "GetCutoutFrom(chunkWrappersToGenerate, Math.max(this.featureNeighborBorder," in source
    assert '"net.dries007.tfc.world.TFCChunkGenerator"' in source
    assert '"com.notenoughmail.kubejs_tfc.util.implementation.custom.world.WrappedChunkGenerator"' in source


if __name__ == "__main__":
    test_border_geometry()
    test_source_wiring()
    print("TFC feature-neighbor biome margin regression PASSED")
