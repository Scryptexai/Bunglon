#!/usr/bin/env python3
"""Create deterministic software review renders of the Phase 3 GLB outputs.

This is a mesh/UV/material inspection aid for CI-friendly environments without Blender,
Godot, EGL, or OSMesa. It samples the embedded base-color textures per face and uses
simple directional shading; it is not a replacement for the Phase 6 engine-import test.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import trimesh
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[2]
RENDERS = ROOT / "character_optimized" / "renders"
LOD0 = ROOT / "character_optimized" / "lyra_vesper_optimized.glb"
LOD1 = ROOT / "character_lod" / "lyra_vesper_lod1.glb"
EPSILON = 1e-8


def normalized(vector: np.ndarray) -> np.ndarray:
    return vector / max(float(np.linalg.norm(vector)), EPSILON)


def face_texture_colors(mesh: trimesh.Trimesh) -> np.ndarray:
    """Return base-color samples for each face using its interpolated UV center."""

    texture = mesh.visual.material.baseColorTexture.convert("RGB")
    pixels = np.asarray(texture, dtype=np.float32) / 255.0
    height, width = pixels.shape[:2]
    uv = mesh.visual.uv[mesh.faces].mean(axis=1)
    # glTF V coordinates are bottom-origin; Pillow image pixels are top-origin.
    x = np.clip((uv[:, 0] * (width - 1)).astype(np.int32), 0, width - 1)
    y = np.clip(((1.0 - uv[:, 1]) * (height - 1)).astype(np.int32), 0, height - 1)
    colors = pixels[y, x]
    if mesh.visual.material.name == "M_Lyra_LumenEnergy":
        # Preserve a readable bloom-like cue in the software proof without HDR output.
        colors = np.clip(colors * np.array((0.68, 1.15, 1.20)), 0.0, 1.0)
    return colors


def draw_mesh(axis, mesh: trimesh.Trimesh) -> None:
    triangles = mesh.vertices[mesh.faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normal_lengths = np.maximum(np.linalg.norm(normals, axis=1), EPSILON)
    normals = normals / normal_lengths[:, None]
    light = normalized(np.array((-0.72, -0.84, 1.18), dtype=float))
    shade = 0.42 + 0.58 * np.clip(normals @ light, 0.0, 1.0)
    base = face_texture_colors(mesh)
    colors = np.empty((len(triangles), 4), dtype=np.float32)
    colors[:, :3] = np.clip(base * shade[:, None], 0.0, 1.0)
    colors[:, 3] = 0.78 if mesh.visual.material.name == "M_Lyra_AuroraMantle" else 1.0
    axis.add_collection3d(Poly3DCollection(triangles, facecolors=colors, edgecolors="none", linewidths=0.0))


def render(path: Path, filename: str, azimuth: float) -> None:
    scene = trimesh.load(path, force="scene")
    RENDERS.mkdir(parents=True, exist_ok=True)
    figure = plt.figure(figsize=(7.5, 8.5), dpi=170, facecolor="#e8ebf2")
    axis = figure.add_subplot(111, projection="3d")
    axis.set_facecolor("#e8ebf2")
    # Mantle is layered after opaque faces, consistent with its double-sided presentation.
    meshes = sorted(
        scene.geometry.values(),
        key=lambda mesh: mesh.visual.material.name == "M_Lyra_AuroraMantle",
    )
    for mesh in meshes:
        draw_mesh(axis, mesh)
    grid_x, grid_y = np.meshgrid(np.linspace(-2.0, 2.0, 2), np.linspace(-1.5, 1.5, 2))
    axis.plot_surface(grid_x, grid_y, np.zeros_like(grid_x) - 0.015, color="#c9ceda", alpha=0.28, shade=False)
    axis.set_proj_type("ortho")
    axis.view_init(elev=8.5, azim=azimuth)
    axis.set_xlim(-1.65, 1.85)
    axis.set_ylim(-1.05, 1.05)
    axis.set_zlim(-0.05, 3.85)
    axis.set_box_aspect((3.5, 2.1, 3.9))
    axis.set_axis_off()
    figure.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
    figure.savefig(RENDERS / filename, facecolor=figure.get_facecolor(), transparent=False)
    plt.close(figure)


def main() -> None:
    if not LOD0.is_file() or not LOD1.is_file():
        raise RuntimeError("Build Phase 3 assets before generating review renders.")
    for suffix, azimuth in (("front", -90.0), ("three_quarter", -58.0), ("back", 90.0)):
        render(LOD0, f"lyra_phase3_lod0_{suffix}.png", azimuth)
    render(LOD1, "lyra_phase3_lod1_three_quarter.png", -58.0)


if __name__ == "__main__":
    main()
