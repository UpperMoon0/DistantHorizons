/*
 *    This file is part of the Distant Horizons mod
 *    licensed under the GNU LGPL v3 License.
 *
 *    Copyright (C) 2020 James Seibel
 *
 *    This program is free software: you can redistribute it and/or modify
 *    it under the terms of the GNU Lesser General Public License as published by
 *    the Free Software Foundation, version 3.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU Lesser General Public License for more details.
 *
 *    You should have received a copy of the GNU Lesser General Public License
 *    along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

package com.seibel.distanthorizons.common.wrappers.worldGeneration.step;

#if MC_VER > MC_1_12_2
import com.seibel.distanthorizons.common.wrappers.chunk.ChunkWrapper;
import com.seibel.distanthorizons.common.wrappers.worldGeneration.DhChunkGenerator;
import com.seibel.distanthorizons.common.wrappers.worldGeneration.params.ThreadWorldGenParams;
import com.seibel.distanthorizons.common.wrappers.worldGeneration.mimicObject.DhLitWorldGenRegion;
import com.seibel.distanthorizons.core.logging.DhLoggerBuilder;
import com.seibel.distanthorizons.core.util.gridList.ArrayGridList;

import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.levelgen.Heightmap;
#if MC_VER >= MC_1_19_4 && MC_VER <= MC_1_20_4
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.chunk.LevelChunkSection;
import net.minecraft.world.level.chunk.ProtoChunk;
import net.minecraft.world.level.levelgen.blending.Blender;
#endif
import com.seibel.distanthorizons.core.logging.DhLogger;

#if MC_VER <= MC_1_20_4
import net.minecraft.world.level.chunk.ChunkStatus;
#else
import net.minecraft.world.level.chunk.status.ChunkStatus;
#endif

import java.util.ArrayList;
import java.util.Collections;
import java.util.ConcurrentModificationException;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;


public final class StepFeatures extends AbstractWorldGenStep
{
	private static final DhLogger LOGGER = new DhLoggerBuilder().build();
	
	public static final ChunkStatus STATUS = ChunkStatus.FEATURES;
	
	private final DhChunkGenerator dhChunkGen;
	
	public static final Set<String> LOGGED_ERRORS = Collections.newSetFromMap(new ConcurrentHashMap<String, Boolean>());
	
	
	
	//=============//
	// constructor //
	//=============//
	
	public StepFeatures(DhChunkGenerator dhChunkGen) { this.dhChunkGen = dhChunkGen; }
	
	
	
	//==================//
	// abstract methods //
	//==================//
	
	@Override
	public ChunkStatus getChunkStatus() { return STATUS; }
	
	@Override
	public void generateGroup(
		ThreadWorldGenParams tParams, DhLitWorldGenRegion worldGenRegion,
		ArrayGridList<ChunkWrapper> chunkWrappers)
	{
		ArrayList<ChunkWrapper> chunksToGen = this.getChunkWrappersToGenerate(chunkWrappers);
		for (ChunkWrapper chunkWrapper : chunksToGen)
		{
			ChunkAccess chunk = chunkWrapper.getChunk();
			
			
			try
			{
				#if MC_VER < MC_1_18_2
				worldGenRegion.setOverrideCenter(chunk.getPos());
				this.dhChunkGen.globalParams.generator.applyBiomeDecoration(worldGenRegion, tParams.structFeatManager);
				#else
				if (worldGenRegion.hasChunk(chunkWrapper.getChunkPos().getX(), chunkWrapper.getChunkPos().getZ()))
				{
					#if MC_VER >= MC_1_19_4 && MC_VER <= MC_1_20_4
					// TFC reads all biome sections in the surrounding 3x3 chunks.
					// DH can retain EMPTY/default-biome ProtoChunks across overlapping regions.
					// Populate those neighbors before TFC's feature decorator sees them.
					if (this.dhChunkGen.isTfcFeatureNeighborGeneration())
					{
						this.restoreTfcNeighborBiomes(tParams, worldGenRegion, chunk);
					}
					#endif
					this.dhChunkGen.globalParams.generator.applyBiomeDecoration(worldGenRegion, chunk, tParams.structFeatManager.forWorldGenRegion(worldGenRegion));
				}
				else
				{
					LOGGER.warn("Unable to generate features for chunk at pos ["+chunkWrapper.getChunkPos()+"], world gen region doesn't contain the chunk.");
				}
				#endif
				
				Heightmap.primeHeightmaps(chunk, STATUS.heightmapsAfter());
			}
			catch (ConcurrentModificationException e)
			{
				String message = "Concurrency issue when generating features for chunk at pos ["+chunkWrapper.getChunkPos()+"], error: ["+e.getMessage()+"], this message will only be logged once. This issue cannot be resolved from DH's end.";
				if (LOGGED_ERRORS.add(message))
				{
					LOGGER.warn(message, e);
				}
			}
			catch (Exception e)
			{
				String message = "Unexpected issue when generating features for chunk at pos ["+chunkWrapper.getChunkPos()+"], error: ["+e.getMessage()+"].";
				if (LOGGED_ERRORS.add(message))
				{
					LOGGER.warn(message, e);
				}
			}
		}
	}

	#if MC_VER >= MC_1_19_4 && MC_VER <= MC_1_20_4
	/**
	 * Repair only DH's temporary ProtoChunks. Never rewrite a persisted LevelChunk.
	 * TFC's feature decorator reads every vertical biome section of the surrounding
	 * 3x3 neighborhood, including chunks whose biome step was skipped by DH.
	 */
	private void restoreTfcNeighborBiomes(
			ThreadWorldGenParams tParams, DhLitWorldGenRegion worldGenRegion, ChunkAccess target)
	{
		ChunkPos center = target.getPos();
		for (int x = center.x - 1; x <= center.x + 1; x++)
		{
			for (int z = center.z - 1; z <= center.z + 1; z++)
			{
				if (!worldGenRegion.dhHasChunk(x, z))
				{
					throw new IllegalStateException("TFC feature biome neighbor outside DH region: [" + x + "," + z + "]");
				}
				ChunkAccess neighbor = worldGenRegion.getChunk(x, z);
				if (!(neighbor instanceof ProtoChunk) || !containsDefaultPlainsBiome(neighbor))
				{
					continue;
				}
				this.dhChunkGen.confirmFutureWasRunSynchronously(
						this.dhChunkGen.globalParams.generator.createBiomes(
							Runnable::run,
							this.dhChunkGen.globalParams.randomState,
							Blender.of(worldGenRegion),
							tParams.structFeatManager.forWorldGenRegion(worldGenRegion),
							neighbor));
				if (containsDefaultPlainsBiome(neighbor))
				{
					throw new IllegalStateException("TFC neighbor biome repair left minecraft:plains in [" + neighbor.getPos() + "]");
				}
			}
		}
	}

	private static boolean containsDefaultPlainsBiome(ChunkAccess chunk)
	{
		for (LevelChunkSection section : chunk.getSections())
		{
			if (section.getBiomes().maybeHas(biome -> biome.is(Biomes.PLAINS)))
			{
				return true;
			}
		}
		return false;
	}
	#endif

}
#endif