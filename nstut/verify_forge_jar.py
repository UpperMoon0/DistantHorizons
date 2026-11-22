#!/usr/bin/env python3
"""Verify the Forge 1.20.1 release JAR is safe for SecureJar discovery.

The old 3.3.3-nstut.1 artifact advertised a multi-release archive but had
no META-INF/versions directory. Forge 47.4.13 crashes during SecureJar
construction in that situation, before any mod can initialize.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import zipfile

MODS_TOML = "META-INF/mods.toml"
MANIFEST = "META-INF/MANIFEST.MF"


def inspect(path: pathlib.Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        assert MODS_TOML in names, f"{path}: missing Forge mods.toml"
        assert any(name.endswith("/ChunkyAccessor.class") for name in names), (
            f"{path}: missing reviewed Chunky compatibility class")
        text = archive.read(MANIFEST).decode("latin-1")
        merged = text.replace("\r\n ", "").replace("\n ", "")
        multi = any(line.lower().replace(" ", "") == "multi-release:true"
                    for line in merged.splitlines())
        versions = [name for name in names if name.startswith("META-INF/versions/")]
        assert not (multi and not versions), (
            f"{path}: Multi-Release: true without META-INF/versions; "
            "Forge SecureJar will fail before mod initialization")
        assert archive.testzip() is None, f"{path}: ZIP entry CRC failure"
        return {"name": path.name, "multi_release": multi,
                "versioned_entries": len(versions), "entries": len(names)}


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        artifact = pathlib.Path(directory) / "forge-1.20.1.jar"
        def write(multi: bool, versioned: bool) -> None:
            with zipfile.ZipFile(artifact, "w") as jar:
                jar.writestr(MANIFEST, "Manifest-Version: 1.0\r\n"
                             + ("Multi-Release: true\r\n" if multi else "")
                             + "\r\n")
                jar.writestr(MODS_TOML, "modLoader=\"javafml\"\n")
                jar.writestr("com/seibel/distanthorizons/forge/ChunkyAccessor.class", b"fixture")
                if versioned:
                    jar.writestr("META-INF/versions/17/example.class", b"fixture")
        write(True, False)
        try:
            inspect(artifact)
        except AssertionError as exc:
            assert "SecureJar" in str(exc)
        else:
            raise AssertionError("Malformed multi-release artifact was accepted")
        write(False, False)
        assert inspect(artifact)["multi_release"] is False
        write(True, True)
        assert inspect(artifact)["versioned_entries"] == 1
        print("SecureJar multi-release regression fixtures PASSED")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        assert len(sys.argv) == 2, "usage: verify_forge_jar.py path/to/forge-1.20.1.jar"
        print(inspect(pathlib.Path(sys.argv[1]).resolve()))
