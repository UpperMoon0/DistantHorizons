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



def test_structure_reference_neighborhood() -> None:
    """References inspect a radius of 8, so never process the biome-only ring."""
    width = 4
    margin = 1
    reference_radius = 8
    requested = {(x, z) for x in range(width) for z in range(width)}
    allocated = {
        (x, z)
        for x in range(-reference_radius, width + reference_radius)
        for z in range(-reference_radius, width + reference_radius)
    }
    structure_targets, regions = generated_and_decorated_chunks(width, margin)
    assert structure_targets == requested

    for full_region, interior in regions:
        # Old .3 behavior: references on full_region hit -9 or 12,
        # while DH preallocates only from -8 through 11.
        assert any(
            (x + dx, z + dz) not in allocated
            for x, z in full_region
            for dx in (-reference_radius, reference_radius)
            for dz in (-reference_radius, reference_radius)
        )
        # New behavior: references only on interior stay within that allocation.
        for x, z in interior:
            assert all(
                (x + dx, z + dz) in allocated
                for dx in range(-reference_radius, reference_radius + 1)
                for dz in range(-reference_radius, reference_radius + 1)
            ), (x, z)



def test_tfc_neighbor_biome_repair() -> None:
    """Guard the 1.20.1-only repair and its no-world-chunk-mutation invariant."""
    source = (SOURCE.parent / "step" / "StepFeatures.java").read_text(encoding="utf-8")
    assert "if (this.dhChunkGen.isTfcFeatureNeighborGeneration())" in source
    assert "this.restoreTfcNeighborBiomes(tParams, worldGenRegion, chunk)" in source
    assert "worldGenRegion.dhHasChunk(x, z)" in source
    assert "neighbor instanceof ProtoChunk" in source
    assert "containsDefaultPlainsBiome(neighbor)" in source
    assert "this.dhChunkGen.globalParams.generator.createBiomes(" in source
    assert "Blender.of(worldGenRegion)" in source
    assert "biome.is(Biomes.PLAINS)" in source
    assert "TFC neighbor biome repair left minecraft:plains" in source


def test_source_wiring() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "requiresTfcFeatureNeighbors(this.globalParams.generator) ? 1 : 0" in source
    assert "Math.max(MAX_WORLD_GEN_CHUNK_BORDER_NEEDED, this.featureNeighborBorder)" in source
    reference_section = source.split("this.stepStructureReference.generateGroup(", 1)[1].split(
        "if (step == EDhApiWorldGenerationStep.STRUCTURE_REFERENCE)", 1
    )[0]
    assert "Math.max(this.featureNeighborBorder," in reference_section
    assert "WORLD_GEN_CHUNK_BORDER_NEEDED_BY_GEN_STEP.get(EDhApiWorldGenerationStep.STRUCTURE_REFERENCE)" in reference_section
    assert "GetCutoutFrom(chunkWrappersToGenerate, Math.max(this.featureNeighborBorder," in source
    assert '"net.dries007.tfc.world.TFCChunkGenerator"' in source
    assert '"com.notenoughmail.kubejs_tfc.util.implementation.custom.world.WrappedChunkGenerator"' in source


if __name__ == "__main__":
    test_border_geometry()
    test_structure_reference_neighborhood()
    test_source_wiring()
    test_tfc_neighbor_biome_repair()
    print("TFC feature-neighbor biome margin regression PASSED")
