#!/usr/bin/env python3
"""Regression guard: recognize TFC's deliberately async noise future, but still join it."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "common/src/main/java/com/seibel/distanthorizons/common/wrappers/worldGeneration/DhChunkGenerator.java").read_text()
noise = (ROOT / "common/src/main/java/com/seibel/distanthorizons/common/wrappers/worldGeneration/step/StepNoise.java").read_text()
method = source.split("public <T> T confirmFutureWasRunSynchronously(", 1)[1].split("public void updateAllFutures()", 1)[0]

assert "if (!this.unsafeThreadingRecorded && !future.isDone())" in method
assert "#if MC_VER > MC_1_12_2" in method
assert "this.usesTfcAsyncNoiseGenerator()" in method
assert "private boolean usesTfcAsyncNoiseGenerator()" in source
assert "getMethod(\"getWrapped\")" in source
assert "wrapped == generator" in source
assert "ReflectiveOperationException | SecurityException" in source
assert 'LOGGER.info("TFC/KubeJS-TFC chunk generator returned an asynchronous noise future.' in method
assert 'LOGGER.warn(' in method and 'new RuntimeException("Incorrect thread pool use")' in method
assert "this.unsafeThreadingRecorded = true;" in method
assert "return future.join();" in method, "Never advance worldgen before the async surface callback completes"
assert "Runnable::run" in noise, "Preserve direct completion executor in StepNoise"
assert "getClass().getSuperclass()" not in method, "Do not alter generator detection in the completion barrier"
print("TFC asynchronous-noise warning classification regression PASSED")
