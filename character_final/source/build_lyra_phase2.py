#!/usr/bin/env python3
"""Build Lyra Vesper's Phase 2 authored mesh package.

This generator deliberately creates authored vertex/face meshes (lofts, extruded panels,
cloth surfaces, and shaped weapon parts). It does not export a Godot primitive assembly,
a generic mannequin, or any primitive GeometryInstance nodes. Blender is still the chosen
production DCC for the later retopology/rig/animation phases; this reproducible source
creates the Phase 2 mesh handoff in an environment where Blender is unavailable.

Run from the repository root:
    python character_final/source/build_lyra_phase2.py

Requirements are pinned in requirements.txt next to this file.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import numpy as np
import trimesh
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image, ImageDraw
from pygltflib import ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER, GLTF2
from trimesh.visual.texture import PBRMaterial, TextureVisuals

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "character_final"
TEXTURES = OUTPUT / "textures"
RENDERS = OUTPUT / "renders"
GLB_PATH = OUTPUT / "lyra_vesper_phase2.glb"
MANIFEST_PATH = OUTPUT / "asset_manifest.json"

EPSILON = 1e-8


@dataclass(frozen=True)
class MaterialDefinition:
    name: str
    color: tuple[int, int, int]
    metallic: float
    roughness: float
    emission: tuple[int, int, int] = (0, 0, 0)
    alpha: int = 255
    pattern: str = "solid"


MATERIAL_DEFINITIONS = (
    MaterialDefinition("M_Skin_Umber", (178, 112, 79), 0.0, 0.62, pattern="skin"),
    MaterialDefinition("M_Suit_MidnightIndigo", (39, 47, 105), 0.15, 0.48, pattern="weave"),
    MaterialDefinition("M_Armor_Cobalt", (62, 94, 184), 0.42, 0.27, pattern="brushed"),
    MaterialDefinition("M_Mantle_Aurora", (137, 77, 201), 0.05, 0.60, pattern="stars"),
    MaterialDefinition("M_Hardware_PaleGold", (214, 181, 105), 0.78, 0.24, pattern="brushed"),
    MaterialDefinition("M_Hair_BlueBlack", (27, 39, 91), 0.12, 0.35, pattern="hair"),
    MaterialDefinition("M_Hair_CyanTip", (42, 161, 224), 0.20, 0.28, emission=(12, 52, 70), pattern="hair"),
    MaterialDefinition("M_Energy_LumenCyan", (84, 232, 255), 0.0, 0.20, emission=(84, 232, 255), pattern="energy"),
    MaterialDefinition("M_Eye_White", (230, 245, 249), 0.0, 0.32),
    MaterialDefinition("M_Iris_DeepTeal", (18, 100, 126), 0.0, 0.22, emission=(3, 18, 22)),
    MaterialDefinition("M_Lip_Rose", (121, 63, 72), 0.0, 0.46),
    MaterialDefinition("M_Freckle_Constellation", (76, 45, 58), 0.0, 0.58),
)


def normalized(vector: np.ndarray) -> np.ndarray:
    magnitude = float(np.linalg.norm(vector))
    if magnitude <= EPSILON:
        return np.array((0.0, 0.0, 1.0), dtype=float)
    return vector / magnitude


def clamp_byte(value: float) -> int:
    return max(0, min(255, int(round(value))))


def rgba(color: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


def make_texture_set(definition: MaterialDefinition) -> dict[str, Image.Image]:
    """Make compact authored provisional PBR maps for Phase 2 material review."""

    size = 512
    base = Image.new("RGBA", (size, size), rgba(definition.color, definition.alpha))
    draw = ImageDraw.Draw(base)
    dark = tuple(clamp_byte(channel * 0.72) for channel in definition.color)
    light = tuple(clamp_byte(channel + (255 - channel) * 0.18) for channel in definition.color)

    if definition.pattern == "weave":
        for step in range(0, size, 16):
            draw.line((0, step, size, step), fill=rgba(dark, 55), width=1)
            draw.line((step, 0, step, size), fill=rgba(light, 28), width=1)
        for diagonal in range(-size, size, 32):
            draw.line((diagonal, 0, diagonal + size, size), fill=rgba(light, 24), width=1)
    elif definition.pattern == "brushed":
        for stripe in range(0, size, 9):
            shade = light if (stripe // 9) % 3 == 0 else dark
            draw.line((0, stripe, size, stripe), fill=rgba(shade, 42), width=1)
    elif definition.pattern == "stars":
        for index in range(55):
            x = (index * 79 + 31) % size
            y = (index * 131 + 17) % size
            radius = 1 + (index % 3)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(205, 220, 255, 125))
        for stripe in range(-size, size, 80):
            draw.line((stripe, 0, stripe + size, size), fill=(155, 100, 255, 42), width=8)
    elif definition.pattern == "hair":
        for stripe in range(-size, size, 22):
            draw.line((stripe, 0, stripe + size // 2, size), fill=rgba(light, 55), width=3)
    elif definition.pattern == "skin":
        for index in range(80):
            x = (index * 137 + 19) % size
            y = (index * 43 + 71) % size
            draw.ellipse((x, y, x + 2, y + 2), fill=rgba(dark, 22))
    elif definition.pattern == "energy":
        for stripe in range(0, size, 32):
            draw.line((0, stripe, size, stripe), fill=(220, 255, 255, 75), width=2)

    normal = Image.new("RGB", (size, size), (128, 128, 255))
    orm = Image.new(
        "RGB",
        (size, size),
        (255, clamp_byte(definition.roughness * 255), clamp_byte(definition.metallic * 255)),
    )
    emission = Image.new("RGB", (size, size), definition.emission)
    return {"basecolor": base, "normal": normal, "orm": orm, "emission": emission}


def save_material_textures() -> tuple[dict[str, PBRMaterial], dict[str, tuple[float, float, float, float]]]:
    TEXTURES.mkdir(parents=True, exist_ok=True)
    materials: dict[str, PBRMaterial] = {}
    render_colors: dict[str, tuple[float, float, float, float]] = {}
    for definition in MATERIAL_DEFINITIONS:
        maps = make_texture_set(definition)
        slug = definition.name.removeprefix("M_").lower()
        for suffix, image in maps.items():
            image.save(TEXTURES / f"lyra_{slug}_{suffix}.png")
        materials[definition.name] = PBRMaterial(
            name=definition.name,
            baseColorTexture=maps["basecolor"],
            # The normal map is generated as a source texture but stays disconnected
            # until Phase 3 has finalized tangents for the retopologized UV layout.
            metallicRoughnessTexture=maps["orm"],
            emissiveTexture=maps["emission"],
            baseColorFactor=np.array((*definition.color, definition.alpha), dtype=np.uint8),
            # glTF emissiveFactor is linear float RGB in the [0, 1] range.
            emissiveFactor=np.asarray(definition.emission, dtype=float) / 255.0,
            metallicFactor=definition.metallic,
            roughnessFactor=definition.roughness,
            alphaMode="BLEND" if definition.alpha < 255 else "OPAQUE",
            doubleSided=definition.name == "M_Mantle_Aurora",
        )
        render_colors[definition.name] = (
            definition.color[0] / 255.0,
            definition.color[1] / 255.0,
            definition.color[2] / 255.0,
            definition.alpha / 255.0,
        )
    return materials, render_colors


def cylindrical_uv(vertices: np.ndarray) -> np.ndarray:
    center = vertices.mean(axis=0)
    radial = vertices[:, :2] - center[:2]
    u = (np.arctan2(radial[:, 1], radial[:, 0]) + math.pi) / (2.0 * math.pi)
    z_min = float(vertices[:, 2].min())
    z_range = max(float(vertices[:, 2].max() - z_min), EPSILON)
    v = (vertices[:, 2] - z_min) / z_range
    return np.column_stack((u, v))


def planar_xz_uv(vertices: np.ndarray) -> np.ndarray:
    x_min, z_min = float(vertices[:, 0].min()), float(vertices[:, 2].min())
    x_range = max(float(vertices[:, 0].max() - x_min), EPSILON)
    z_range = max(float(vertices[:, 2].max() - z_min), EPSILON)
    return np.column_stack(((vertices[:, 0] - x_min) / x_range, (vertices[:, 2] - z_min) / z_range))


def create_mesh(
    name: str,
    vertices: Iterable[Iterable[float]],
    faces: Iterable[Iterable[int]],
    material: PBRMaterial,
    material_name: str,
    uv_mode: str = "cylindrical",
) -> trimesh.Trimesh:
    vertex_array = np.asarray(list(vertices), dtype=np.float64)
    face_array = np.asarray(list(faces), dtype=np.int64)
    mesh = trimesh.Trimesh(vertices=vertex_array, faces=face_array, process=False, validate=True)
    mesh.remove_unreferenced_vertices()
    uv = planar_xz_uv(mesh.vertices) if uv_mode == "planar_xz" else cylindrical_uv(mesh.vertices)
    mesh.visual = TextureVisuals(uv=uv, material=material)
    mesh.metadata["material_name"] = material_name
    mesh.metadata["authored_phase"] = "phase_2"
    return mesh


def loft_mesh(
    name: str,
    rings: list[tuple[tuple[float, float, float], float, float]],
    material: PBRMaterial,
    material_name: str,
    sides: int = 16,
) -> trimesh.Trimesh:
    """Create a custom longitudinal tube with perpendicular elliptical rings."""

    vertices: list[np.ndarray] = []
    for index, (center_tuple, radius_a, radius_b) in enumerate(rings):
        center = np.asarray(center_tuple, dtype=float)
        previous = np.asarray(rings[max(0, index - 1)][0], dtype=float)
        following = np.asarray(rings[min(len(rings) - 1, index + 1)][0], dtype=float)
        tangent = normalized(following - previous)
        reference = np.array((0.0, 0.0, 1.0), dtype=float)
        if abs(float(np.dot(tangent, reference))) > 0.92:
            reference = np.array((0.0, 1.0, 0.0), dtype=float)
        axis_a = normalized(np.cross(tangent, reference))
        axis_b = normalized(np.cross(axis_a, tangent))
        for side in range(sides):
            angle = 2.0 * math.pi * side / sides
            vertices.append(center + axis_a * math.cos(angle) * radius_a + axis_b * math.sin(angle) * radius_b)

    faces: list[tuple[int, int, int]] = []
    for ring in range(len(rings) - 1):
        for side in range(sides):
            next_side = (side + 1) % sides
            a = ring * sides + side
            b = ring * sides + next_side
            c = (ring + 1) * sides + next_side
            d = (ring + 1) * sides + side
            faces.extend(((a, b, c), (a, c, d)))
    # Fan caps make every body/weapon part a closed mesh.
    start_center = len(vertices)
    vertices.append(np.asarray(rings[0][0], dtype=float))
    end_center = len(vertices)
    vertices.append(np.asarray(rings[-1][0], dtype=float))
    for side in range(sides):
        next_side = (side + 1) % sides
        faces.append((start_center, next_side, side))
        last = (len(rings) - 1) * sides
        faces.append((end_center, last + side, last + next_side))
    return create_mesh(name, vertices, faces, material, material_name)


def ellipsoid_mesh(
    name: str,
    center: tuple[float, float, float],
    radii: tuple[float, float, float],
    material: PBRMaterial,
    material_name: str,
    longitude: int = 16,
    latitude: int = 10,
) -> trimesh.Trimesh:
    """Create a bespoke lat-long ellipsoid rather than importing a primitive node."""

    cx, cy, cz = center
    rx, ry, rz = radii
    vertices: list[tuple[float, float, float]] = [(cx, cy, cz + rz)]
    for lat in range(1, latitude):
        theta = math.pi * lat / latitude
        for lon in range(longitude):
            phi = 2.0 * math.pi * lon / longitude
            vertices.append(
                (
                    cx + rx * math.sin(theta) * math.cos(phi),
                    cy + ry * math.sin(theta) * math.sin(phi),
                    cz + rz * math.cos(theta),
                )
            )
    bottom_index = len(vertices)
    vertices.append((cx, cy, cz - rz))
    faces: list[tuple[int, int, int]] = []
    for lon in range(longitude):
        faces.append((0, 1 + lon, 1 + (lon + 1) % longitude))
    for lat in range(latitude - 2):
        start = 1 + lat * longitude
        next_start = start + longitude
        for lon in range(longitude):
            next_lon = (lon + 1) % longitude
            faces.extend(
                (
                    (start + lon, next_start + lon, next_start + next_lon),
                    (start + lon, next_start + next_lon, start + next_lon),
                )
            )
    last_start = 1 + (latitude - 2) * longitude
    for lon in range(longitude):
        faces.append((last_start + lon, bottom_index, last_start + (lon + 1) % longitude))
    return create_mesh(name, vertices, faces, material, material_name)


def extruded_polygon_xz(
    name: str,
    points: list[tuple[float, float]],
    y_center: float,
    depth: float,
    material: PBRMaterial,
    material_name: str,
) -> trimesh.Trimesh:
    """Create a closed, bevel-ready armor plate or emblem from an authored outline."""

    front_y = y_center - depth * 0.5
    back_y = y_center + depth * 0.5
    vertices = [(x, front_y, z) for x, z in points] + [(x, back_y, z) for x, z in points]
    count = len(points)
    faces: list[tuple[int, int, int]] = []
    # Front/back fans; outlines in this file are intentionally convex for clean triangulation.
    for index in range(1, count - 1):
        faces.append((0, index + 1, index))
        faces.append((count, count + index, count + index + 1))
    for index in range(count):
        next_index = (index + 1) % count
        faces.extend(
            (
                (index, next_index, count + next_index),
                (index, count + next_index, count + index),
            )
        )
    return create_mesh(name, vertices, faces, material, material_name, uv_mode="planar_xz")


def extruded_polygon_xy(
    name: str,
    points: list[tuple[float, float]],
    z_center: float,
    depth: float,
    material: PBRMaterial,
    material_name: str,
) -> trimesh.Trimesh:
    bottom_z = z_center - depth * 0.5
    top_z = z_center + depth * 0.5
    vertices = [(x, y, bottom_z) for x, y in points] + [(x, y, top_z) for x, y in points]
    count = len(points)
    faces: list[tuple[int, int, int]] = []
    for index in range(1, count - 1):
        faces.extend(((0, index, index + 1), (count, count + index + 1, count + index)))
    for index in range(count):
        next_index = (index + 1) % count
        faces.extend(
            (
                (index, count + index, count + next_index),
                (index, count + next_index, next_index),
            )
        )
    return create_mesh(name, vertices, faces, material, material_name)


def torus_xz(
    name: str,
    center: tuple[float, float, float],
    major_radius: float,
    minor_radius: float,
    material: PBRMaterial,
    material_name: str,
    major_steps: int = 18,
    minor_steps: int = 8,
) -> trimesh.Trimesh:
    """Create a circular ring in the x-z plane, used for the bow compass riser."""

    cx, cy, cz = center
    vertices: list[tuple[float, float, float]] = []
    for major in range(major_steps):
        theta = 2.0 * math.pi * major / major_steps
        radial = np.array((math.cos(theta), 0.0, math.sin(theta)))
        for minor in range(minor_steps):
            phi = 2.0 * math.pi * minor / minor_steps
            point = np.array((cx, cy, cz)) + radial * (major_radius + minor_radius * math.cos(phi))
            point[1] += minor_radius * math.sin(phi)
            vertices.append(tuple(point))
    faces: list[tuple[int, int, int]] = []
    for major in range(major_steps):
        next_major = (major + 1) % major_steps
        for minor in range(minor_steps):
            next_minor = (minor + 1) % minor_steps
            a = major * minor_steps + minor
            b = next_major * minor_steps + minor
            c = next_major * minor_steps + next_minor
            d = major * minor_steps + next_minor
            faces.extend(((a, b, c), (a, c, d)))
    return create_mesh(name, vertices, faces, material, material_name)


def prism_crystal(
    name: str,
    center: tuple[float, float, float],
    radius: float,
    height: float,
    material: PBRMaterial,
    material_name: str,
) -> trimesh.Trimesh:
    """Create a four-facet energy shard with authored geometry."""

    cx, cy, cz = center
    vertices = [
        (cx, cy, cz + height * 0.5),
        (cx + radius, cy, cz),
        (cx, cy + radius * 0.6, cz),
        (cx - radius, cy, cz),
        (cx, cy - radius * 0.6, cz),
        (cx, cy, cz - height * 0.5),
    ]
    faces = [
        (0, 1, 2),
        (0, 2, 3),
        (0, 3, 4),
        (0, 4, 1),
        (5, 2, 1),
        (5, 3, 2),
        (5, 4, 3),
        (5, 1, 4),
    ]
    return create_mesh(name, vertices, faces, material, material_name)


def smooth_rings(
    rings: list[tuple[tuple[float, float, float], float, float]],
    subdivisions: int = 3,
) -> list[tuple[tuple[float, float, float], float, float]]:
    """Catmull-Rom interpolate authored control rings for graceful hair/weapon curves."""

    if len(rings) < 3:
        return rings
    output: list[tuple[tuple[float, float, float], float, float]] = []
    for index in range(len(rings) - 1):
        p0 = np.asarray(rings[max(0, index - 1)][0], dtype=float)
        p1 = np.asarray(rings[index][0], dtype=float)
        p2 = np.asarray(rings[index + 1][0], dtype=float)
        p3 = np.asarray(rings[min(len(rings) - 1, index + 2)][0], dtype=float)
        for step in range(subdivisions):
            t = step / subdivisions
            t2, t3 = t * t, t * t * t
            point = 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)
            radius_a = rings[index][1] * (1.0 - t) + rings[index + 1][1] * t
            radius_b = rings[index][2] * (1.0 - t) + rings[index + 1][2] * t
            output.append((tuple(float(value) for value in point), radius_a, radius_b))
    output.append(rings[-1])
    return output


def mantle_mesh(
    name: str,
    material: PBRMaterial,
    material_name: str,
) -> trimesh.Trimesh:
    """Create a shaped, thick asymmetric left-shoulder cloth panel."""

    columns, rows = 6, 7
    front: list[tuple[float, float, float]] = []
    for row in range(rows):
        t = row / (rows - 1)
        z = 2.62 - 1.18 * t
        center_x = -0.48 - 0.20 * t
        half_width = 0.24 + 0.24 * t
        for column in range(columns):
            s = column / (columns - 1)
            x = center_x + (s - 0.5) * half_width * 2.0
            y = 0.10 + 0.19 * t + 0.08 * math.sin(s * math.pi) * (0.2 + t)
            # Taper the inner lower edge so the mantle is visibly asymmetric.
            z_offset = -0.18 * max(0.0, s - 0.55) * t
            front.append((x, y, z + z_offset))
    thickness = 0.026
    vertices = front + [(x, y + thickness, z) for x, y, z in front]
    faces: list[tuple[int, int, int]] = []
    for row in range(rows - 1):
        for column in range(columns - 1):
            a = row * columns + column
            b = a + 1
            c = a + columns + 1
            d = a + columns
            faces.extend(((a, b, c), (a, c, d)))
            back = len(front)
            faces.extend(((back + a, back + c, back + b), (back + a, back + d, back + c)))
    # Seal all four boundaries.
    boundaries = []
    boundaries.extend((index, index + 1) for index in range(columns - 1))
    last_row = (rows - 1) * columns
    boundaries.extend((last_row + index + 1, last_row + index) for index in range(columns - 1))
    boundaries.extend((row * columns, (row + 1) * columns) for row in range(rows - 1))
    boundaries.extend((row * columns + columns - 1, (row + 1) * columns + columns - 1) for row in range(rows - 1))
    back = len(front)
    for a, b in boundaries:
        faces.extend(((a, back + a, back + b), (a, back + b, b)))
    return create_mesh(name, vertices, faces, material, material_name, uv_mode="planar_xz")


def add(scene: trimesh.Scene, mesh: trimesh.Trimesh, name: str) -> None:
    mesh.metadata["part_name"] = name
    scene.add_geometry(mesh, node_name=name, geom_name=name)


def load_obj_body_group(source_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read only MakeHuman's actual `body` group, omitting editor helper meshes.

    The source OBJ also contains helper tights, joints, eyelashes, and grounding meshes
    after the body group. Those are authoring aids, not anatomy, and would produce a
    false garment silhouette if exported. Parsing the declared body group keeps only the
    high-detail humanoid surface.
    """

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    in_body_group = False
    for line in source_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            _, x, y, z, *_ = line.split()
            vertices.append((float(x), float(y), float(z)))
        elif line.startswith("g "):
            in_body_group = line.strip() == "g body"
        elif in_body_group and line.startswith("f "):
            indices = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            for index in range(1, len(indices) - 1):
                faces.append((indices[0], indices[index], indices[index + 1]))
    if len(vertices) < 1_000 or len(faces) < 10_000:
        raise RuntimeError("Could not read a plausible MakeHuman body mesh from the CC0 OBJ.")
    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=np.int64)


def add_cc0_anatomical_base(scene: trimesh.Scene, materials: dict[str, PBRMaterial]) -> None:
    """Add the CC0 anatomical starting mesh as a stylized suit/head split.

    The imported source is intentionally reshaped, re-materialed, and substantially
    overlaid by Lyra-specific authored costume, hair, mantle, face treatment, and bow
    geometry. Its only purpose is to give Phase 2 a complete adult humanoid anatomy,
    including credible hands, feet, and facial planes, rather than a primitive mannequin.
    Provenance is recorded beside the source OBJ.
    """

    source_path = ROOT / "character_final" / "source" / "makehuman_base_cc0.obj"
    if not source_path.is_file():
        raise RuntimeError(f"Required CC0 anatomical source is missing: {source_path}")
    source, faces = load_obj_body_group(source_path)
    # MakeHuman uses X horizontal, Y vertical, Z depth. This maps it into Lyra's
    # meter-scale scene, recenters the depth, and subtly narrows the waist/shoulders.
    scale = 0.200
    vertices = np.column_stack(
        (
            source[:, 0] * scale,
            (1.05 - source[:, 2]) * scale,
            (source[:, 1] + 8.4488) * scale,
        )
    )
    # A light stylization pass: narrow the waist, retain athletic thighs, and avoid
    # shipping an unmodified base body even before costume geometry is added.
    normalized_height = vertices[:, 2] / max(float(vertices[:, 2].max()), EPSILON)
    waist = np.exp(-((normalized_height - 0.48) / 0.12) ** 2)
    shoulder = np.exp(-((normalized_height - 0.71) / 0.10) ** 2)
    vertices[:, 0] *= 1.0 - 0.065 * waist + 0.025 * shoulder
    vertices[:, 1] *= 1.0 - 0.030 * waist

    centroids = vertices[faces].mean(axis=1)
    # All anatomy reads as a fitted technical suit except the face/head and exposed
    # hands. Spatially isolating the head prevents a raw mannequin shoulder line from
    # leaking through Lyra's suit, mantle, and shoulder armor.
    head_faces = (centroids[:, 2] > 2.73) & (np.abs(centroids[:, 0]) < 0.38)
    hand_faces = (np.abs(centroids[:, 0]) > 0.82) & (centroids[:, 2] > 1.18) & (centroids[:, 2] < 2.02)
    skin_faces = head_faces | hand_faces
    add(
        scene,
        create_mesh("MESH_Lyra_BaseSuit", vertices, faces[~skin_faces], materials["M_Suit_MidnightIndigo"], "M_Suit_MidnightIndigo"),
        "MESH_Lyra_BaseSuit",
    )
    add(
        scene,
        create_mesh("MESH_Lyra_HeadAndHands", vertices, faces[skin_faces], materials["M_Skin_Umber"], "M_Skin_Umber"),
        "MESH_Lyra_HeadAndHands",
    )


def replace_procedural_anatomy(scene: trimesh.Scene, materials: dict[str, PBRMaterial]) -> None:
    """Replace temporary analytic anatomy with the detailed CC0 anatomical base."""

    temporary_prefixes = (
        "MESH_Torso_",
        "MESH_Pelvis_",
        "MESH_Thigh_",
        "MESH_Calf_",
        "MESH_Boot_",
        "MESH_UpperArm_",
        "MESH_Forearm_",
        "MESH_Glove",
        "MESH_Neck",
        "MESH_Head",
        "MESH_Ear_",
        "MESH_Nose",
    )
    for geometry_name in tuple(scene.geometry.keys()):
        if geometry_name.startswith(temporary_prefixes):
            scene.delete_geometry(geometry_name)
    add_cc0_anatomical_base(scene, materials)


def compact_scene(scene: trimesh.Scene) -> trimesh.Scene:
    """Rebuild the scene graph after replacement so exports have no stale blockout nodes."""

    compact = trimesh.Scene()
    for geometry_name, mesh in scene.geometry.items():
        compact.add_geometry(mesh, node_name=geometry_name, geom_name=geometry_name)
    return compact


def build_scene(materials: dict[str, PBRMaterial]) -> trimesh.Scene:
    scene = trimesh.Scene()
    suit = materials["M_Suit_MidnightIndigo"]
    armor = materials["M_Armor_Cobalt"]
    skin = materials["M_Skin_Umber"]
    mantle = materials["M_Mantle_Aurora"]
    gold = materials["M_Hardware_PaleGold"]
    hair = materials["M_Hair_BlueBlack"]
    hair_tip = materials["M_Hair_CyanTip"]
    energy = materials["M_Energy_LumenCyan"]
    white = materials["M_Eye_White"]
    iris = materials["M_Iris_DeepTeal"]
    lip = materials["M_Lip_Rose"]
    freckle = materials["M_Freckle_Constellation"]

    # Base humanoid. Every element is an authored loft/ellipsoid mesh, not a runtime primitive.
    add(
        scene,
        loft_mesh(
            "MESH_Torso_Suit",
            [
                ((0.0, 0.0, 1.53), 0.43, 0.28),
                ((0.0, 0.0, 1.77), 0.39, 0.26),
                ((0.0, -0.01, 2.15), 0.53, 0.30),
                ((0.0, -0.01, 2.47), 0.50, 0.28),
                ((0.0, -0.01, 2.62), 0.38, 0.25),
            ],
            suit,
            "M_Suit_MidnightIndigo",
            sides=24,
        ),
        "MESH_Torso_Suit",
    )
    add(
        scene,
        loft_mesh(
            "MESH_Pelvis_Suit",
            [((0.0, 0.0, 1.37), 0.48, 0.28), ((0.0, 0.0, 1.58), 0.45, 0.29), ((0.0, 0.0, 1.72), 0.40, 0.26)],
            suit,
            "M_Suit_MidnightIndigo",
            sides=20,
        ),
        "MESH_Pelvis_Suit",
    )
    for side, label in ((-1.0, "L"), (1.0, "R")):
        x = side * 0.27
        add(
            scene,
            loft_mesh(
                f"MESH_Thigh_{label}",
                [((x, 0.0, 1.54), 0.22, 0.20), ((x + side * 0.03, -0.015, 1.18), 0.19, 0.18), ((x + side * 0.02, 0.0, 0.84), 0.15, 0.15)],
                suit,
                "M_Suit_MidnightIndigo",
                sides=16,
            ),
            f"MESH_Thigh_{label}",
        )
        add(
            scene,
            loft_mesh(
                f"MESH_Calf_{label}",
                [((x + side * 0.02, 0.0, 0.86), 0.16, 0.15), ((x + side * 0.05, 0.03, 0.43), 0.13, 0.13), ((x + side * 0.06, -0.01, 0.17), 0.12, 0.11)],
                suit,
                "M_Suit_MidnightIndigo",
                sides=16,
            ),
            f"MESH_Calf_{label}",
        )
        add(
            scene,
            loft_mesh(
                f"MESH_ArmorBoot_{label}",
                [
                    ((x + side * 0.06, -0.03, 0.28), 0.145, 0.13),
                    ((x + side * 0.05, -0.12, 0.14), 0.155, 0.135),
                    ((x + side * 0.04, -0.25, 0.09), 0.145, 0.21),
                    ((x + side * 0.04, -0.38, 0.075), 0.12, 0.18),
                ],
                armor,
                "M_Armor_Cobalt",
                sides=16,
            ),
            f"MESH_ArmorBoot_{label}",
        )
        # Long custom shin guard outline on the front of the leg.
        shin = [(x - side * 0.12, 0.23), (x - side * 0.15, 0.65), (x, 0.82), (x + side * 0.15, 0.65), (x + side * 0.10, 0.23)]
        add(scene, extruded_polygon_xz(f"MESH_ShinPlate_{label}", shin, -0.155, 0.052, armor, "M_Armor_Cobalt"), f"MESH_ShinPlate_{label}")
        inset = [(x - side * 0.045, 0.34), (x, 0.62), (x + side * 0.045, 0.34)]
        add(scene, extruded_polygon_xz(f"MESH_ShinLumen_{label}", inset, -0.186, 0.026, energy, "M_Energy_LumenCyan"), f"MESH_ShinLumen_{label}")
        knee = [(x - side * 0.14, 0.88), (x - side * 0.10, 1.10), (x, 1.17), (x + side * 0.10, 1.10), (x + side * 0.14, 0.88)]
        add(scene, extruded_polygon_xz(f"MESH_KneeArmor_{label}", knee, -0.17, 0.06, armor, "M_Armor_Cobalt"), f"MESH_KneeArmor_{label}")

        shoulder_x = side * 0.48
        elbow_x = side * 0.72
        wrist_x = side * 0.84
        add(
            scene,
            loft_mesh(
                f"MESH_UpperArm_{label}",
                [((shoulder_x, -0.01, 2.43), 0.145, 0.135), ((side * 0.61, -0.02, 2.13), 0.12, 0.115), ((elbow_x, -0.04, 1.98), 0.105, 0.10)],
                skin,
                "M_Skin_Umber",
                sides=14,
            ),
            f"MESH_UpperArm_{label}",
        )
        add(
            scene,
            loft_mesh(
                f"MESH_Forearm_{label}",
                [((elbow_x, -0.04, 2.0), 0.115, 0.105), ((side * 0.80, -0.10, 1.78), 0.135, 0.11), ((wrist_x, -0.12, 1.60), 0.09, 0.08)],
                suit,
                "M_Suit_MidnightIndigo",
                sides=14,
            ),
            f"MESH_Forearm_{label}",
        )
        guard = [(wrist_x - side * 0.10, 1.58), (wrist_x - side * 0.15, 1.83), (elbow_x, 2.03), (elbow_x + side * 0.08, 1.85), (wrist_x + side * 0.07, 1.60)]
        add(scene, extruded_polygon_xz(f"MESH_ForearmGuard_{label}", guard, -0.15, 0.052, armor, "M_Armor_Cobalt"), f"MESH_ForearmGuard_{label}")
        add(
            scene,
            ellipsoid_mesh(f"MESH_Glove_{label}", (wrist_x + side * 0.035, -0.14, 1.51), (0.10, 0.08, 0.11), suit, "M_Suit_MidnightIndigo", longitude=10, latitude=7),
            f"MESH_Glove_{label}",
        )
        # A compact five-digit silhouette, intentionally separate for future finger rigging.
        for finger in range(4):
            offset = (finger - 1.5) * 0.032
            add(
                scene,
                loft_mesh(
                    f"MESH_GloveFinger_{label}_{finger + 1}",
                    [((wrist_x + side * 0.08, -0.17 + offset, 1.49), 0.022, 0.021), ((wrist_x + side * 0.12, -0.18 + offset, 1.42), 0.018, 0.017)],
                    suit,
                    "M_Suit_MidnightIndigo",
                    sides=8,
                ),
                f"MESH_GloveFinger_{label}_{finger + 1}",
            )

    # Neck, head, ears, face, and facial identity.
    add(scene, loft_mesh("MESH_Neck", [((0.0, 0.0, 2.58), 0.145, 0.14), ((0.0, 0.0, 2.82), 0.14, 0.13)], skin, "M_Skin_Umber", sides=16), "MESH_Neck")
    add(scene, ellipsoid_mesh("MESH_Head", (0.0, -0.02, 3.09), (0.285, 0.270, 0.350), skin, "M_Skin_Umber", longitude=36, latitude=24), "MESH_Head")
    for side, label in ((-1.0, "L"), (1.0, "R")):
        add(scene, ellipsoid_mesh(f"MESH_Ear_{label}", (side * 0.282, 0.0, 3.09), (0.034, 0.030, 0.065), skin, "M_Skin_Umber", longitude=12, latitude=8), f"MESH_Ear_{label}")
        eye_x = side * 0.135
        add(scene, ellipsoid_mesh(f"MESH_Eye_{label}", (eye_x * 0.78, -0.276, 3.155), (0.058, 0.012, 0.031), white, "M_Eye_White", longitude=16, latitude=10), f"MESH_Eye_{label}")
        add(scene, ellipsoid_mesh(f"MESH_Iris_{label}", (eye_x * 0.78, -0.286, 3.155), (0.023, 0.006, 0.022), iris, "M_Iris_DeepTeal", longitude=12, latitude=8), f"MESH_Iris_{label}")
    add(scene, loft_mesh("MESH_Nose", [((0.0, -0.255, 3.18), 0.022, 0.021), ((0.0, -0.294, 3.095), 0.030, 0.026), ((0.0, -0.280, 3.045), 0.032, 0.016)], skin, "M_Skin_Umber", sides=8), "MESH_Nose")
    lips = [(-0.073, 3.025), (-0.030, 3.044), (0.0, 3.038), (0.030, 3.044), (0.073, 3.025), (0.030, 3.006), (0.0, 3.001), (-0.030, 3.006)]
    add(scene, extruded_polygon_xz("MESH_Lips", lips, -0.283, 0.012, lip, "M_Lip_Rose"), "MESH_Lips")
    # Constellation freckles on wearer-left cheek (screen-left in front view).
    for index, (x, z, radius) in enumerate(((-0.17, 3.14, 0.009), (-0.145, 3.112, 0.007), (-0.19, 3.10, 0.006), (-0.125, 3.09, 0.005), (-0.21, 3.125, 0.005))):
        add(scene, ellipsoid_mesh(f"MESH_Freckle_{index + 1}", (x, -0.300, z), (radius, 0.005, radius), freckle, "M_Freckle_Constellation", longitude=8, latitude=6), f"MESH_Freckle_{index + 1}")
    visor_path = [(0.040, -0.295, 3.205), (0.145, -0.302, 3.22), (0.198, -0.298, 3.165), (0.185, -0.298, 3.11), (0.105, -0.298, 3.098)]
    add(scene, loft_mesh("MESH_RightEye_Visor", [(point, 0.014, 0.014) for point in visor_path], energy, "M_Energy_LumenCyan", sides=6), "MESH_RightEye_Visor")
    add(scene, prism_crystal("MESH_EarTech_R", (0.312, -0.02, 3.09), 0.025, 0.070, gold, "M_Hardware_PaleGold"), "MESH_EarTech_R")

    # Sculpted hair cap, fringe locks, and the iconic high comet-tail ponytail.
    add(scene, ellipsoid_mesh("MESH_HairCap", (0.0, 0.050, 3.37), (0.305, 0.285, 0.135), hair, "M_Hair_BlueBlack", longitude=32, latitude=18), "MESH_HairCap")
    fringe_specs = [
        ((-0.14, -0.26, 3.32), (-0.23, -0.30, 3.15), 0.045),
        ((-0.02, -0.28, 3.34), (-0.08, -0.315, 3.19), 0.040),
        ((0.13, -0.25, 3.32), (0.08, -0.30, 3.19), 0.035),
    ]
    for index, (start, end, radius) in enumerate(fringe_specs):
        middle = tuple((np.asarray(start) + np.asarray(end)) * 0.5 + np.array((0.04 if index == 0 else 0.0, -0.025, 0.04)))
        add(scene, loft_mesh(f"MESH_Fringe_{index + 1}", [(start, radius, radius * 0.55), (middle, radius * 0.78, radius * 0.48), (end, radius * 0.20, radius * 0.17)], hair, "M_Hair_BlueBlack", sides=8), f"MESH_Fringe_{index + 1}")
    ponytail = [
        ((0.04, 0.17, 3.47), 0.090, 0.075),
        ((0.12, 0.23, 3.63), 0.112, 0.090),
        ((0.33, 0.28, 3.76), 0.118, 0.094),
        ((0.57, 0.27, 3.68), 0.105, 0.082),
        ((0.74, 0.21, 3.47), 0.082, 0.064),
        ((0.78, 0.15, 3.18), 0.059, 0.047),
        ((0.66, 0.08, 2.95), 0.036, 0.029),
    ]
    add(scene, loft_mesh("MESH_CometTail_Base", smooth_rings(ponytail[:6], subdivisions=3), hair, "M_Hair_BlueBlack", sides=20), "MESH_CometTail_Base")
    add(scene, loft_mesh("MESH_CometTail_CyanTip", smooth_rings(ponytail[5:] + [((0.43, 0.01, 2.80), 0.012, 0.010)], subdivisions=3), hair_tip, "M_Hair_CyanTip", sides=14), "MESH_CometTail_CyanTip")
    add(scene, torus_xz("MESH_PonytailBand", (0.04, 0.17, 3.47), 0.090, 0.018, gold, "M_Hardware_PaleGold", major_steps=18, minor_steps=8), "MESH_PonytailBand")

    # Armor silhouette, chest core, belt, left-only mantle, and quiver.
    chest = [(-0.20, 2.14), (-0.17, 2.36), (0.0, 2.48), (0.17, 2.36), (0.20, 2.14), (0.11, 1.99), (0.0, 1.95), (-0.11, 1.99)]
    add(scene, extruded_polygon_xz("MESH_ChestArmor", chest, -0.302, 0.042, armor, "M_Armor_Cobalt"), "MESH_ChestArmor")
    core_outer = [(0.0, 2.45), (0.105, 2.345), (0.0, 2.24), (-0.105, 2.345)]
    core_inner = [(0.0, 2.415), (0.062, 2.345), (0.0, 2.275), (-0.062, 2.345)]
    add(scene, extruded_polygon_xz("MESH_ChestCoreGold", core_outer, -0.336, 0.042, gold, "M_Hardware_PaleGold"), "MESH_ChestCoreGold")
    add(scene, extruded_polygon_xz("MESH_ChestCoreLumen", core_inner, -0.365, 0.028, energy, "M_Energy_LumenCyan"), "MESH_ChestCoreLumen")
    # Twin inset channels give the suit a deliberately designed celestial read rather than a plain bodysuit.
    add(scene, loft_mesh("MESH_TorsoLumen_Left", [((-0.22, -0.314, 2.20), 0.015, 0.011), ((-0.27, -0.300, 2.02), 0.013, 0.010), ((-0.19, -0.285, 1.84), 0.010, 0.008)], energy, "M_Energy_LumenCyan", sides=8), "MESH_TorsoLumen_Left")
    add(scene, loft_mesh("MESH_TorsoLumen_Right", [((0.22, -0.314, 2.20), 0.015, 0.011), ((0.27, -0.300, 2.02), 0.013, 0.010), ((0.19, -0.285, 1.84), 0.010, 0.008)], energy, "M_Energy_LumenCyan", sides=8), "MESH_TorsoLumen_Right")
    for side, label in ((-1.0, "L"), (1.0, "R")):
        shoulder = [(side * 0.38, 2.48), (side * 0.57, 2.43), (side * 0.61, 2.29), (side * 0.44, 2.25), (side * 0.34, 2.34)]
        add(scene, extruded_polygon_xz(f"MESH_ShoulderArmor_{label}", shoulder, -0.02, 0.075, armor, "M_Armor_Cobalt"), f"MESH_ShoulderArmor_{label}")
    belt_path = [((-0.45, 0.0, 1.62), 0.045, 0.030), ((0.0, -0.04, 1.56), 0.045, 0.030), ((0.45, 0.0, 1.62), 0.045, 0.030)]
    add(scene, loft_mesh("MESH_BeltFront", belt_path, gold, "M_Hardware_PaleGold", sides=8), "MESH_BeltFront")
    add(scene, mantle_mesh("MESH_AuroraMantle_Left", mantle, "M_Mantle_Aurora"), "MESH_AuroraMantle_Left")
    clasp = [(-0.62, 2.61), (-0.52, 2.70), (-0.42, 2.61), (-0.52, 2.52)]
    add(scene, extruded_polygon_xz("MESH_MantleClasp", clasp, -0.06, 0.06, gold, "M_Hardware_PaleGold"), "MESH_MantleClasp")
    # Rear-right compact photon quiver with five tapered shafts.
    add(scene, loft_mesh("MESH_PhotonQuiver", [((0.42, 0.22, 1.60), 0.15, 0.10), ((0.50, 0.25, 1.86), 0.13, 0.09), ((0.47, 0.23, 2.05), 0.12, 0.08)], armor, "M_Armor_Cobalt", sides=10), "MESH_PhotonQuiver")
    for index in range(5):
        x = 0.40 + (index - 2) * 0.035
        add(scene, loft_mesh(f"MESH_PhotonArrow_{index + 1}", [((x, 0.19, 1.86), 0.018, 0.018), ((x + 0.04, 0.20, 2.18 + (index % 2) * 0.03), 0.011, 0.011)], energy, "M_Energy_LumenCyan", sides=6), f"MESH_PhotonArrow_{index + 1}")

    # Aster Arc: crescent limbs, compass riser, cyan string, shards, and arrow socket.
    bow_x = 1.28
    upper_limb = [((bow_x - 0.12, -0.14, 2.28), 0.070, 0.055), ((bow_x + 0.05, -0.14, 2.56), 0.065, 0.052), ((bow_x + 0.18, -0.14, 2.92), 0.055, 0.045), ((bow_x + 0.21, -0.14, 3.31), 0.035, 0.030)]
    lower_limb = [((bow_x - 0.12, -0.14, 2.16), 0.070, 0.055), ((bow_x + 0.04, -0.14, 1.92), 0.065, 0.052), ((bow_x + 0.15, -0.14, 1.55), 0.055, 0.045), ((bow_x + 0.17, -0.14, 1.24), 0.035, 0.030)]
    add(scene, loft_mesh("MESH_AsterArc_UpperIndigo", upper_limb, suit, "M_Suit_MidnightIndigo", sides=10), "MESH_AsterArc_UpperIndigo")
    add(scene, loft_mesh("MESH_AsterArc_LowerIndigo", lower_limb, suit, "M_Suit_MidnightIndigo", sides=10), "MESH_AsterArc_LowerIndigo")
    upper_gold = [(point, radius_a * 0.50, radius_b * 0.50) for point, radius_a, radius_b in upper_limb]
    lower_gold = [(point, radius_a * 0.50, radius_b * 0.50) for point, radius_a, radius_b in lower_limb]
    # Offset gold trim slightly toward screen/right so the two material bands remain visible.
    upper_gold = [((point[0] + 0.038, point[1] + 0.018, point[2]), radius_a, radius_b) for point, radius_a, radius_b in upper_gold]
    lower_gold = [((point[0] + 0.038, point[1] + 0.018, point[2]), radius_a, radius_b) for point, radius_a, radius_b in lower_gold]
    add(scene, loft_mesh("MESH_AsterArc_UpperGold", upper_gold, gold, "M_Hardware_PaleGold", sides=8), "MESH_AsterArc_UpperGold")
    add(scene, loft_mesh("MESH_AsterArc_LowerGold", lower_gold, gold, "M_Hardware_PaleGold", sides=8), "MESH_AsterArc_LowerGold")
    add(scene, torus_xz("MESH_AsterArc_Compass", (bow_x - 0.14, -0.14, 2.22), 0.23, 0.048, gold, "M_Hardware_PaleGold", major_steps=18, minor_steps=8), "MESH_AsterArc_Compass")
    star = []
    for point in range(8):
        angle = math.pi / 2.0 + point * math.pi / 4.0
        radius = 0.16 if point % 2 == 0 else 0.072
        star.append((bow_x - 0.14 + math.cos(angle) * radius, 2.22 + math.sin(angle) * radius))
    add(scene, extruded_polygon_xz("MESH_AsterArc_StarCore", star, -0.205, 0.052, energy, "M_Energy_LumenCyan"), "MESH_AsterArc_StarCore")
    string = [((bow_x + 0.21, -0.16, 3.31), 0.013, 0.013), ((bow_x - 0.14, -0.18, 2.22), 0.013, 0.013), ((bow_x + 0.17, -0.16, 1.24), 0.013, 0.013)]
    add(scene, loft_mesh("MESH_AsterArc_EnergyString", string, energy, "M_Energy_LumenCyan", sides=6), "MESH_AsterArc_EnergyString")
    for index, position in enumerate(((1.55, -0.13, 3.35), (1.67, -0.12, 3.15), (1.48, -0.12, 3.02))):
        add(scene, prism_crystal(f"MESH_AsterArc_LightShard_{index + 1}", position, 0.065, 0.19, energy, "M_Energy_LumenCyan"), f"MESH_AsterArc_LightShard_{index + 1}")
    arrow_path = [((bow_x - 0.14, -0.31, 2.22), 0.025, 0.025), ((bow_x - 0.70, -0.31, 2.22), 0.018, 0.018)]
    add(scene, loft_mesh("MESH_AsterArc_DisplayArrow", arrow_path, energy, "M_Energy_LumenCyan", sides=8), "MESH_AsterArc_DisplayArrow")
    add(scene, prism_crystal("MESH_AsterArc_ArrowHead", (bow_x - 0.79, -0.31, 2.22), 0.065, 0.18, energy, "M_Energy_LumenCyan"), "MESH_AsterArc_ArrowHead")

    replace_procedural_anatomy(scene, materials)
    return compact_scene(scene)


def material_color(mesh: trimesh.Trimesh, render_colors: dict[str, tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    return render_colors.get(mesh.metadata.get("material_name", ""), (0.6, 0.6, 0.6, 1.0))


def render_scene(scene: trimesh.Scene, render_colors: dict[str, tuple[float, float, float, float]], filename: str, azimuth: float) -> None:
    """Render a software turntable proof using matplotlib; no GPU or Blender required."""

    RENDERS.mkdir(parents=True, exist_ok=True)
    figure = plt.figure(figsize=(7.5, 8.5), dpi=170, facecolor="#e8ebf2")
    axis = figure.add_subplot(111, projection="3d")
    axis.set_facecolor("#e8ebf2")
    light = normalized(np.array((-0.7, -0.8, 1.2), dtype=float))
    # Opaque meshes first; the mantle's transparency remains readable afterward.
    meshes = sorted(scene.geometry.values(), key=lambda item: material_color(item, render_colors)[3])
    for mesh in meshes:
        triangles = mesh.vertices[mesh.faces]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        normal_lengths = np.maximum(np.linalg.norm(normals, axis=1), EPSILON)
        normals = normals / normal_lengths[:, None]
        shade = 0.44 + 0.56 * np.clip(normals @ light, 0.0, 1.0)
        base = np.array(material_color(mesh, render_colors), dtype=float)
        colors = np.empty((len(triangles), 4), dtype=float)
        colors[:, :3] = np.clip(base[:3] * shade[:, None], 0.0, 1.0)
        colors[:, 3] = base[3]
        collection = Poly3DCollection(triangles, facecolors=colors, edgecolors="none", linewidths=0.0)
        axis.add_collection3d(collection)
    # Soft ground plane is presentation-only and never enters the GLB.
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


def set_glb_buffer_targets() -> None:
    """Add glTF buffer target hints omitted by trimesh's generic exporter.

    The hints are not required to parse a GLB, but they improve strict validator and
    runtime upload behavior. Image buffer views are intentionally untouched.
    """

    gltf = GLTF2().load_binary(GLB_PATH)
    targets: dict[int, int] = {}
    for mesh in gltf.meshes or []:
        for primitive in mesh.primitives:
            for accessor_index in primitive.attributes.__dict__.values():
                if accessor_index is None:
                    continue
                buffer_view_index = gltf.accessors[accessor_index].bufferView
                if buffer_view_index is not None:
                    targets[buffer_view_index] = ARRAY_BUFFER
            if primitive.indices is not None:
                buffer_view_index = gltf.accessors[primitive.indices].bufferView
                if buffer_view_index is not None:
                    existing = targets.get(buffer_view_index)
                    if existing not in (None, ELEMENT_ARRAY_BUFFER):
                        raise RuntimeError("A GLB buffer view was unexpectedly shared by indices and vertex attributes.")
                    targets[buffer_view_index] = ELEMENT_ARRAY_BUFFER
    for buffer_view_index, target in targets.items():
        gltf.bufferViews[buffer_view_index].target = target
    gltf.save_binary(GLB_PATH)


def write_manifest(scene: trimesh.Scene) -> None:
    meshes = list(scene.geometry.values())
    bounds = scene.bounds
    texture_files = sorted(path.name for path in TEXTURES.glob("*.png"))
    manifest = {
        "asset": "Lyra Vesper — Phase 2 authored 3D mesh",
        "format": "glTF 2.0 binary (.glb)",
        "source_generator": "character_final/source/build_lyra_phase2.py",
        "phase_scope": "Mesh + provisional PBR materials/textures only; retopology, final UV review, LOD, rig, and animation are subsequent phases.",
        "mesh_count": len(meshes),
        "vertices": int(sum(len(mesh.vertices) for mesh in meshes)),
        "triangles": int(sum(len(mesh.faces) for mesh in meshes)),
        "materials": sorted({mesh.metadata.get("material_name", "") for mesh in meshes}),
        "textures": texture_files,
        "bounds_meters": {
            "minimum": [round(float(value), 5) for value in bounds[0]],
            "maximum": [round(float(value), 5) for value in bounds[1]],
            "extent": [round(float(value), 5) for value in scene.extents],
        },
        "prohibited_final_primitives": ["BoxMesh", "SphereMesh", "CapsuleMesh", "CylinderMesh", "Godot runtime primitive assembly"],
        "parts": sorted(scene.geometry.keys()),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def validate_export(scene: trimesh.Scene) -> None:
    """Fail fast if the GLB is not a healthy, textured multi-part 3D mesh package."""

    if not GLB_PATH.is_file() or GLB_PATH.stat().st_size < 40_000:
        raise RuntimeError("GLB export is missing or implausibly small.")
    forbidden_names = ("cube", "sphere", "capsule", "cylinder", "mannequin", "placeholder")
    names = [name.lower() for name in scene.geometry]
    if any(word in name for word in forbidden_names for name in names):
        raise RuntimeError("A prohibited primitive/placeholder name was found in exported geometry.")
    if len(scene.geometry) < 25:
        raise RuntimeError("Character scene has too few authored components to be a complete Phase 2 hero.")
    if sum(len(mesh.faces) for mesh in scene.geometry.values()) < 2_500:
        raise RuntimeError("Character mesh triangle count is too low for this authored Phase 2 handoff.")
    reloaded = trimesh.load(GLB_PATH, force="scene")
    if not isinstance(reloaded, trimesh.Scene) or len(reloaded.geometry) < 25:
        raise RuntimeError("GLB reload validation failed.")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    materials, render_colors = save_material_textures()
    scene = build_scene(materials)
    scene.export(GLB_PATH, file_type="glb")
    set_glb_buffer_targets()
    write_manifest(scene)
    validate_export(scene)
    render_scene(scene, render_colors, "lyra_phase2_front.png", azimuth=-90.0)
    render_scene(scene, render_colors, "lyra_phase2_three_quarter.png", azimuth=-58.0)
    render_scene(scene, render_colors, "lyra_phase2_back.png", azimuth=90.0)
    print(f"Exported {GLB_PATH.relative_to(ROOT)}")
    print(f"Meshes: {len(scene.geometry)} | triangles: {sum(len(mesh.faces) for mesh in scene.geometry.values())}")


if __name__ == "__main__":
    main()
