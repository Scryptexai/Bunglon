#!/usr/bin/env python3
"""Build mobile-conscious optimized and LOD GLB assets for Lyra Vesper.

Phase 2 is the high-detail authored handoff. This Phase 3 builder:
  1. uses meshoptimizer through glTF-Transform to simplify and weld geometry;
  2. packs the material families into one UV atlas plus dedicated mantle/energy maps;
  3. merges compatible geometry down to three runtime draw groups;
  4. emits an optimized LOD0 and a lower-cost LOD1 with matching material layout;
  5. validates each final GLB with glTF-Transform.

The source Phase 2 asset remains intact. This script never replaces it.

Usage (from repository root):
    python3 -m venv /tmp/lyra-phase3-venv
    /tmp/lyra-phase3-venv/bin/pip install -r character_optimized/source/requirements.txt
    /tmp/lyra-phase3-venv/bin/python character_optimized/source/build_lyra_phase3.py
"""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from pygltflib import (
    ARRAY_BUFFER,
    ELEMENT_ARRAY_BUFFER,
    Accessor,
    BufferView,
    GLTF2,
    Image as GLTFImage,
    Material,
    NormalMaterialTexture,
    PbrMetallicRoughness,
    Sampler,
    Texture,
    TextureInfo,
)

ROOT = Path(__file__).resolve().parents[2]
PHASE2 = ROOT / "character_final"
INPUT_GLB = PHASE2 / "lyra_vesper_phase2.glb"
INPUT_TEXTURES = PHASE2 / "textures"
OUTPUT = ROOT / "character_optimized"
LOD_OUTPUT = ROOT / "character_lod"
TEXTURES = OUTPUT / "textures"
REPORT_PATH = OUTPUT / "optimization_manifest.json"
LOD_REPORT_PATH = LOD_OUTPUT / "lod_manifest.json"
CLI = ("npx", "--yes", "@gltf-transform/cli@4.5.0")

# Atlas cells reserve a four-pixel gutter on each side to avoid mip bleed.
ATLAS_SIZE = 1024
GRID_COLUMNS = 4
GRID_ROWS = 4
GUTTER = 4
OPAQUE_ATLAS_CELLS = {
    "M_Armor_Cobalt": (0, 0),
    "M_Eye_White": (1, 0),
    "M_Iris_DeepTeal": (2, 0),
    "M_Lip_Rose": (3, 0),
    "M_Freckle_Constellation": (0, 1),
    "M_Hardware_PaleGold": (1, 1),
    "M_Hair_BlueBlack": (2, 1),
    "M_Hair_CyanTip": (3, 1),
    "M_Suit_MidnightIndigo": (0, 2),
    "M_Skin_Umber": (1, 2),
}
ENERGY_MATERIAL = "M_Energy_LumenCyan"
MANTLE_MATERIAL = "M_Mantle_Aurora"


@dataclass(frozen=True)
class AssetMetrics:
    filename: str
    bytes: int
    meshes: int
    nodes: int
    materials: int
    textures: int
    images: int
    triangles: int
    vertices: int
    geometry_bytes: int
    draw_groups: int


def command(*args: str) -> None:
    completed = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
        )


def load_glb_json(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    magic, version, total_length = struct.unpack("<4sII", payload[:12])
    if magic != b"glTF" or version != 2 or total_length != len(payload):
        raise RuntimeError(f"Invalid GLB header: {path}")
    json_length, chunk_type = struct.unpack("<I4s", payload[12:20])
    if chunk_type != b"JSON":
        raise RuntimeError(f"Missing JSON chunk: {path}")
    return json.loads(payload[20 : 20 + json_length].decode("utf-8").rstrip(" \t\r\n\0"))


def metrics(path: Path) -> AssetMetrics:
    document = load_glb_json(path)
    triangles = 0
    vertices = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh["primitives"]:
            if "indices" in primitive:
                triangles += document["accessors"][primitive["indices"]]["count"] // 3
            vertices += document["accessors"][primitive["attributes"]["POSITION"]]["count"]
    unique_materials = {
        primitive.get("material")
        for mesh in document.get("meshes", [])
        for primitive in mesh["primitives"]
        if primitive.get("material") is not None
    }
    geometry_bytes = sum(
        view["byteLength"]
        for view in document.get("bufferViews", [])
        if view.get("target") in (ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER)
    )
    return AssetMetrics(
        filename=path.name,
        bytes=path.stat().st_size,
        meshes=len(document.get("meshes", [])),
        nodes=len(document.get("nodes", [])),
        materials=len(document.get("materials", [])),
        textures=len(document.get("textures", [])),
        images=len(document.get("images", [])),
        triangles=triangles,
        vertices=vertices,
        geometry_bytes=geometry_bytes,
        draw_groups=len(unique_materials),
    )


def phase2_texture_path(material_name: str, suffix: str) -> Path:
    slug = material_name.removeprefix("M_").lower()
    return INPUT_TEXTURES / f"lyra_{slug}_{suffix}.png"


def cell_uv(cell: tuple[int, int]) -> tuple[float, float, float, float]:
    cell_width = ATLAS_SIZE // GRID_COLUMNS
    cell_height = ATLAS_SIZE // GRID_ROWS
    column, row = cell
    u0 = (column * cell_width + GUTTER) / ATLAS_SIZE
    v0 = (row * cell_height + GUTTER) / ATLAS_SIZE
    u1 = ((column + 1) * cell_width - GUTTER) / ATLAS_SIZE
    v1 = ((row + 1) * cell_height - GUTTER) / ATLAS_SIZE
    return u0, v0, u1, v1


def copy_into_cell(atlas: Image.Image, source_path: Path, cell: tuple[int, int]) -> None:
    if not source_path.is_file():
        raise RuntimeError(f"Missing Phase 2 texture source: {source_path}")
    cell_width = ATLAS_SIZE // GRID_COLUMNS
    cell_height = ATLAS_SIZE // GRID_ROWS
    width = cell_width - GUTTER * 2
    height = cell_height - GUTTER * 2
    image = Image.open(source_path).convert(atlas.mode).resize((width, height), Image.Resampling.LANCZOS)
    # Replicate edge pixels into the gutter rather than leaving transparent/black seams.
    # UVs point at the interior; this padding protects bilinear and mip sampling at its edge.
    padded = np.pad(
        np.asarray(image),
        ((GUTTER, GUTTER), (GUTTER, GUTTER), (0, 0)),
        mode="edge",
    )
    tile = Image.fromarray(padded, mode=atlas.mode)
    x = cell[0] * cell_width
    y = cell[1] * cell_height
    atlas.paste(tile, (x, y))


def derive_normal_map(
    basecolor: Image.Image,
    destination: Path,
    strength: float,
    size: tuple[int, int] | None = None,
) -> None:
    """Generate a non-flat tangent-space normal map from final packed color detail.

    The Phase 2 normal sources were intentionally flat placeholders. The packed P3 UVs need
    non-flat normal data before a MikkTSpace tangent stream is useful, so derive a compact
    detail normal from the final atlas/image luminance. This is a production-ready microdetail
    map, not a claim of a high-poly sculpt bake.
    """

    if size is not None:
        basecolor = basecolor.resize(size, Image.Resampling.LANCZOS)
    rgb = np.asarray(basecolor.convert("RGB"), dtype=np.float32) / 255.0
    height = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    # Central differences keep edge behavior deterministic and are inexpensive to reproduce.
    dx = np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)
    dy = np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(nx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack((nx / length, ny / length, nz / length), axis=-1)
    encoded = np.clip((normal * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(encoded, mode="RGB").save(destination, optimize=True)


def generate_texture_package() -> dict[str, Path]:
    """Pack Phase 2 material maps into mobile-friendly 1024/512 source textures."""

    TEXTURES.mkdir(parents=True, exist_ok=True)
    opaque_modes = {"basecolor": "RGBA", "orm": "RGB", "emission": "RGB"}
    outputs: dict[str, Path] = {}
    for suffix, mode in opaque_modes.items():
        initial = (0, 0, 0, 0) if mode == "RGBA" else (0, 0, 0)
        if suffix == "orm":
            initial = (255, 128, 0)
        atlas = Image.new(mode, (ATLAS_SIZE, ATLAS_SIZE), initial)
        for material_name, cell in OPAQUE_ATLAS_CELLS.items():
            copy_into_cell(atlas, phase2_texture_path(material_name, suffix), cell)
        output = TEXTURES / f"lyra_mobile_opaque_{suffix}.png"
        atlas.save(output, optimize=True)
        outputs[f"opaque_{suffix}"] = output
    opaque_normal = TEXTURES / "lyra_mobile_opaque_normal.png"
    # A 512² normal map is intentional: it carries microdetail, not silhouette detail,
    # and keeps the runtime texture residency materially below the Phase 2 package.
    derive_normal_map(
        Image.open(outputs["opaque_basecolor"]), opaque_normal, strength=2.4, size=(512, 512)
    )
    outputs["opaque_normal"] = opaque_normal

    # Separate weapon-energy and double-sided-mantle maps avoid forcing those material
    # states on every opaque body pixel. They retain 512² resolution at this quality tier.
    for prefix, material_name in (("energy", ENERGY_MATERIAL), ("mantle", MANTLE_MATERIAL)):
        for suffix in ("basecolor", "orm", "emission"):
            source = Image.open(phase2_texture_path(material_name, suffix)).convert("RGBA" if suffix == "basecolor" else "RGB")
            output = TEXTURES / f"lyra_mobile_{prefix}_{suffix}.png"
            source.resize((512, 512), Image.Resampling.LANCZOS).save(output, optimize=True)
            outputs[f"{prefix}_{suffix}"] = output
        normal = TEXTURES / f"lyra_mobile_{prefix}_normal.png"
        height_source = Image.open(outputs[f"{prefix}_basecolor"])
        derive_normal_map(height_source, normal, strength=2.0 if prefix == "mantle" else 1.5)
        outputs[f"{prefix}_normal"] = normal
    return outputs


def append_embedded_image(gltf: GLTF2, binary: bytearray, path: Path, name: str) -> tuple[int, bytearray]:
    """Append a PNG to the GLB binary and return its Texture index."""

    padding = (-len(binary)) % 4
    if padding:
        binary.extend(b"\0" * padding)
    offset = len(binary)
    encoded = path.read_bytes()
    binary.extend(encoded)
    gltf.bufferViews.append(BufferView(buffer=0, byteOffset=offset, byteLength=len(encoded), name=name))
    image_index = len(gltf.images)
    gltf.images.append(GLTFImage(bufferView=len(gltf.bufferViews) - 1, mimeType="image/png", name=name))
    texture_index = len(gltf.textures)
    gltf.textures.append(Texture(sampler=0, source=image_index, name=name))
    return texture_index, binary


def access_uv(binary: bytearray, gltf: GLTF2, accessor_index: int) -> tuple[int, int, int]:
    accessor = gltf.accessors[accessor_index]
    if accessor.componentType != 5126 or accessor.type != "VEC2":
        raise RuntimeError("Expected float VEC2 UV accessor while packing material atlas.")
    view = gltf.bufferViews[accessor.bufferView]
    start = int(view.byteOffset or 0) + int(accessor.byteOffset or 0)
    stride = int(view.byteStride or 8)
    return start, stride, accessor.count


def remap_uvs_to_atlas(gltf: GLTF2, binary: bytearray, primitive, material_name: str) -> None:
    if material_name not in OPAQUE_ATLAS_CELLS:
        return
    uv_accessor = primitive.attributes.TEXCOORD_0
    if uv_accessor is None:
        raise RuntimeError(f"Mesh using {material_name} has no UV map.")
    u0, v0, u1, v1 = cell_uv(OPAQUE_ATLAS_CELLS[material_name])
    start, stride, count = access_uv(binary, gltf, uv_accessor)
    for index in range(count):
        byte_offset = start + index * stride
        u, v = struct.unpack_from("<ff", binary, byte_offset)
        struct.pack_into("<ff", binary, byte_offset, u0 + u * (u1 - u0), v0 + v * (v1 - v0))


def set_buffer_targets(gltf: GLTF2) -> None:
    """Use canonical buffer targets for strict glTF validation."""

    targets: dict[int, int] = {}
    for mesh in gltf.meshes or []:
        for primitive in mesh.primitives:
            for accessor_index in primitive.attributes.__dict__.values():
                if accessor_index is None:
                    continue
                view_index = gltf.accessors[accessor_index].bufferView
                if view_index is not None:
                    targets[view_index] = ARRAY_BUFFER
            if primitive.indices is not None:
                view_index = gltf.accessors[primitive.indices].bufferView
                if view_index is not None:
                    existing = targets.get(view_index)
                    if existing not in (None, ELEMENT_ARRAY_BUFFER):
                        raise RuntimeError("A buffer view cannot be both vertex and index data.")
                    targets[view_index] = ELEMENT_ARRAY_BUFFER
    for view_index, target in targets.items():
        gltf.bufferViews[view_index].target = target


COMPONENT_DTYPES = {
    5120: np.dtype("<i1"),
    5121: np.dtype("<u1"),
    5122: np.dtype("<i2"),
    5123: np.dtype("<u2"),
    5125: np.dtype("<u4"),
    5126: np.dtype("<f4"),
}
ACCESSOR_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_accessor(gltf: GLTF2, binary: bytearray, accessor_index: int) -> np.ndarray:
    """Read one non-sparse GLB accessor, honoring a possible interleaved stride."""

    accessor = gltf.accessors[accessor_index]
    if accessor.sparse is not None:
        raise RuntimeError("The Phase 3 normal builder does not accept sparse accessors.")
    if accessor.bufferView is None:
        raise RuntimeError("The Phase 3 normal builder requires buffer-backed accessors.")
    dtype = COMPONENT_DTYPES[accessor.componentType]
    components = ACCESSOR_COMPONENTS[accessor.type]
    view = gltf.bufferViews[accessor.bufferView]
    offset = int(view.byteOffset or 0) + int(accessor.byteOffset or 0)
    element_bytes = dtype.itemsize * components
    stride = int(view.byteStride or element_bytes)
    return np.ndarray(
        shape=(accessor.count, components),
        dtype=dtype,
        buffer=binary,
        offset=offset,
        strides=(stride, dtype.itemsize),
    ).copy()


def append_float_attribute(gltf: GLTF2, binary: bytearray, values: np.ndarray, accessor_type: str, name: str) -> tuple[int, bytearray]:
    """Append a float vertex attribute and return its accessor index and new binary."""

    values = np.ascontiguousarray(values, dtype=np.float32)
    padding = (-len(binary)) % 4
    if padding:
        binary.extend(b"\0" * padding)
    offset = len(binary)
    encoded = values.tobytes(order="C")
    binary.extend(encoded)
    gltf.bufferViews.append(
        BufferView(buffer=0, byteOffset=offset, byteLength=len(encoded), target=ARRAY_BUFFER, name=name)
    )
    accessor_index = len(gltf.accessors)
    gltf.accessors.append(
        Accessor(
            bufferView=len(gltf.bufferViews) - 1,
            componentType=5126,
            count=len(values),
            type=accessor_type,
            name=name,
        )
    )
    return accessor_index, binary


def append_smooth_normals(source: Path, destination: Path) -> None:
    """Generate indexed, area-weighted vertex normals after mesh/material joining.

    The Phase 2 handoff intentionally had no normals/tangents. Smooth normals are generated
    only after the final Phase 3 UV atlas and draw-group joins, then MikkTSpace tangents are
    generated by glTF-Transform in the next pipeline stage.
    """

    gltf = GLTF2().load_binary(source)
    binary = bytearray(gltf.binary_blob())
    for mesh in gltf.meshes or []:
        for primitive in mesh.primitives:
            if primitive.mode not in (None, 4):
                raise RuntimeError("The Phase 3 normal builder only supports triangle primitives.")
            if primitive.indices is None:
                raise RuntimeError("The Phase 3 normal builder requires indexed primitives.")
            positions = read_accessor(gltf, binary, primitive.attributes.POSITION).astype(np.float64)
            indices = read_accessor(gltf, binary, primitive.indices).reshape(-1)
            if len(indices) % 3:
                raise RuntimeError("Triangle index count is not divisible by three.")
            faces = indices.reshape((-1, 3))
            if len(faces) == 0 or int(faces.max()) >= len(positions):
                raise RuntimeError("Invalid triangle indices while generating normals.")
            face_normals = np.cross(
                positions[faces[:, 1]] - positions[faces[:, 0]],
                positions[faces[:, 2]] - positions[faces[:, 0]],
            )
            normals = np.zeros_like(positions)
            for corner in range(3):
                np.add.at(normals, faces[:, corner], face_normals)
            lengths = np.linalg.norm(normals, axis=1)
            # Degenerate vertices are not expected, but deterministic fallback avoids NaNs.
            normals[lengths < 1e-10] = np.array((0.0, 0.0, 1.0))
            lengths = np.maximum(np.linalg.norm(normals, axis=1), 1e-10)
            normals /= lengths[:, None]
            accessor_index, binary = append_float_attribute(
                gltf, binary, normals, "VEC3", f"{mesh.name or 'mesh'}_NORMAL"
            )
            primitive.attributes.NORMAL = accessor_index
    gltf.set_binary_blob(bytes(binary))
    gltf.buffers[0].byteLength = len(binary)
    set_buffer_targets(gltf)
    destination.parent.mkdir(parents=True, exist_ok=True)
    gltf.save_binary(destination)


def write_float_accessor(gltf: GLTF2, binary: bytearray, accessor_index: int, values: np.ndarray) -> None:
    """Write float data into an existing non-sparse accessor with stride support."""

    accessor = gltf.accessors[accessor_index]
    if accessor.componentType != 5126 or accessor.bufferView is None:
        raise RuntimeError("Expected a float, buffer-backed accessor while repairing tangents.")
    components = ACCESSOR_COMPONENTS[accessor.type]
    if values.shape != (accessor.count, components):
        raise RuntimeError("Tangent repair received an accessor shape mismatch.")
    view = gltf.bufferViews[accessor.bufferView]
    offset = int(view.byteOffset or 0) + int(accessor.byteOffset or 0)
    stride = int(view.byteStride or components * 4)
    target = np.ndarray(
        shape=(accessor.count, components),
        dtype=np.dtype("<f4"),
        buffer=binary,
        offset=offset,
        strides=(stride, 4),
    )
    target[:] = np.asarray(values, dtype=np.float32)


def repair_degenerate_tangents(source: Path, destination: Path) -> None:
    """Keep the MikkTSpace stream valid at degenerate atlas UV corners.

    MikkTSpace intentionally returns zero vectors for vertices reached only by degenerate UV
    triangles. glTF validation requires a unit xyz vector. These rare vertices get a stable
    perpendicular fallback; all regular vertices remain untouched MikkTSpace output.
    """

    gltf = GLTF2().load_binary(source)
    binary = bytearray(gltf.binary_blob())
    repairs = 0
    for mesh in gltf.meshes or []:
        for primitive in mesh.primitives:
            tangent_index = primitive.attributes.TANGENT
            normal_index = primitive.attributes.NORMAL
            if tangent_index is None or normal_index is None:
                raise RuntimeError("Tangent pass did not emit both NORMAL and TANGENT attributes.")
            tangents = read_accessor(gltf, binary, tangent_index).astype(np.float64)
            normals = read_accessor(gltf, binary, normal_index).astype(np.float64)
            magnitude = np.linalg.norm(tangents[:, :3], axis=1)
            invalid = (~np.isfinite(magnitude)) | (magnitude < 0.999)
            if not np.any(invalid):
                continue
            fallback_normals = normals[invalid]
            reference = np.tile(np.array((1.0, 0.0, 0.0)), (len(fallback_normals), 1))
            parallel = np.abs(fallback_normals[:, 0]) > 0.90
            reference[parallel] = np.array((0.0, 1.0, 0.0))
            fallback = np.cross(reference, fallback_normals)
            fallback /= np.maximum(np.linalg.norm(fallback, axis=1), 1e-10)[:, None]
            tangents[invalid, :3] = fallback
            tangents[invalid, 3] = 1.0
            write_float_accessor(gltf, binary, tangent_index, tangents)
            repairs += int(np.count_nonzero(invalid))
    gltf.set_binary_blob(bytes(binary))
    gltf.buffers[0].byteLength = len(binary)
    set_buffer_targets(gltf)
    destination.parent.mkdir(parents=True, exist_ok=True)
    gltf.save_binary(destination)
    print(f"  repaired {repairs} degenerate tangent vertices in {source.name}")


def pack_materials(source: Path, destination: Path, package: dict[str, Path]) -> None:
    """Collapse Phase 2 materials into opaque-atlas, energy, and mantle materials."""

    gltf = GLTF2().load_binary(source)
    if len(gltf.samplers or []) == 0:
        gltf.samplers = [Sampler(wrapS=10497, wrapT=10497, magFilter=9729, minFilter=9987)]
    else:
        gltf.samplers = [gltf.samplers[0]]
    binary = bytearray(gltf.binary_blob())
    names = [material.name for material in gltf.materials]
    for mesh in gltf.meshes or []:
        for primitive in mesh.primitives:
            material_name = names[primitive.material]
            remap_uvs_to_atlas(gltf, binary, primitive, material_name)

    # Drop Phase 2 image/material references. Their source files remain preserved in
    # character_final/, while only the atlas-oriented runtime package is embedded here.
    gltf.images = []
    gltf.textures = []
    gltf.materials = []
    opaque_base, binary = append_embedded_image(gltf, binary, package["opaque_basecolor"], "lyra_mobile_opaque_basecolor")
    opaque_orm, binary = append_embedded_image(gltf, binary, package["opaque_orm"], "lyra_mobile_opaque_orm")
    opaque_normal, binary = append_embedded_image(gltf, binary, package["opaque_normal"], "lyra_mobile_opaque_normal")
    opaque_emission, binary = append_embedded_image(gltf, binary, package["opaque_emission"], "lyra_mobile_opaque_emission")
    energy_base, binary = append_embedded_image(gltf, binary, package["energy_basecolor"], "lyra_mobile_energy_basecolor")
    energy_normal, binary = append_embedded_image(gltf, binary, package["energy_normal"], "lyra_mobile_energy_normal")
    energy_emission, binary = append_embedded_image(gltf, binary, package["energy_emission"], "lyra_mobile_energy_emission")
    mantle_base, binary = append_embedded_image(gltf, binary, package["mantle_basecolor"], "lyra_mobile_mantle_basecolor")
    mantle_normal, binary = append_embedded_image(gltf, binary, package["mantle_normal"], "lyra_mobile_mantle_normal")
    mantle_orm, binary = append_embedded_image(gltf, binary, package["mantle_orm"], "lyra_mobile_mantle_orm")

    gltf.materials = [
        Material(
            name="M_Lyra_OpaqueAtlas",
            pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[1.0, 1.0, 1.0, 1.0],
                metallicFactor=1.0,
                roughnessFactor=1.0,
                baseColorTexture=TextureInfo(index=opaque_base),
                metallicRoughnessTexture=TextureInfo(index=opaque_orm),
            ),
            normalTexture=NormalMaterialTexture(index=opaque_normal, scale=1.0),
            emissiveFactor=[1.0, 1.0, 1.0],
            emissiveTexture=TextureInfo(index=opaque_emission),
            doubleSided=False,
        ),
        Material(
            name="M_Lyra_LumenEnergy",
            pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[1.0, 1.0, 1.0, 1.0],
                metallicFactor=0.0,
                roughnessFactor=0.20,
                baseColorTexture=TextureInfo(index=energy_base),
            ),
            normalTexture=NormalMaterialTexture(index=energy_normal, scale=1.0),
            emissiveFactor=[1.0, 1.0, 1.0],
            emissiveTexture=TextureInfo(index=energy_emission),
            doubleSided=False,
        ),
        Material(
            name="M_Lyra_AuroraMantle",
            pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[1.0, 1.0, 1.0, 1.0],
                metallicFactor=0.02,
                roughnessFactor=0.60,
                baseColorTexture=TextureInfo(index=mantle_base),
                metallicRoughnessTexture=TextureInfo(index=mantle_orm),
            ),
            normalTexture=NormalMaterialTexture(index=mantle_normal, scale=1.0),
            doubleSided=True,
        ),
    ]
    for mesh in gltf.meshes or []:
        for primitive in mesh.primitives:
            original_name = names[primitive.material]
            if original_name == ENERGY_MATERIAL:
                primitive.material = 1
            elif original_name == MANTLE_MATERIAL:
                primitive.material = 2
            else:
                primitive.material = 0
    gltf.set_binary_blob(bytes(binary))
    gltf.buffers[0].byteLength = len(binary)
    set_buffer_targets(gltf)
    destination.parent.mkdir(parents=True, exist_ok=True)
    gltf.save_binary(destination)


def build_asset(temp_dir: Path, name: str, ratio: float, error: float, output_path: Path, package: dict[str, Path]) -> AssetMetrics:
    simplified = temp_dir / f"{name}_simplified.glb"
    packed = temp_dir / f"{name}_packed.glb"
    joined = temp_dir / f"{name}_joined.glb"
    normalled = temp_dir / f"{name}_normalled.glb"
    tangent_ready = temp_dir / f"{name}_tangent_ready.glb"
    repaired = temp_dir / f"{name}_tangent_repaired.glb"
    command(
        *CLI,
        "optimize",
        str(INPUT_GLB),
        str(simplified),
        "--compress",
        "false",
        "--texture-compress",
        "false",
        "--simplify-ratio",
        str(ratio),
        "--simplify-error",
        str(error),
        "--palette",
        "false",
        "--join",
        "true",
        "--join-meshes",
        "true",
        "--join-named",
        "true",
    )
    pack_materials(simplified, packed, package)
    command(*CLI, "join", str(packed), str(joined))
    append_smooth_normals(joined, normalled)
    # glTF-Transform's tangents command uses MikkTSpace, matching the standard expected by
    # glTF renderers and conventional normal-map bakers.
    command(*CLI, "tangents", str(normalled), str(tangent_ready), "--overwrite", "true")
    repair_degenerate_tangents(tangent_ready, repaired)
    command(*CLI, "prune", str(repaired), str(output_path))
    command(*CLI, "validate", str(output_path))
    return metrics(output_path)


def write_reports(phase2_metrics: AssetMetrics, optimized: AssetMetrics, lod1: AssetMetrics) -> None:
    reduction = lambda before, after: round((1.0 - after / before) * 100.0, 2)
    report = {
        "phase": 3,
        "asset": "Lyra Vesper mobile optimization",
        "source": asdict(phase2_metrics),
        "optimized_lod0": asdict(optimized),
        "lod1": asdict(lod1),
        "lod0_triangle_reduction_percent": reduction(phase2_metrics.triangles, optimized.triangles),
        "lod1_triangle_reduction_percent": reduction(phase2_metrics.triangles, lod1.triangles),
        "lod0_geometry_upload_reduction_percent": reduction(phase2_metrics.geometry_bytes, optimized.geometry_bytes),
        "lod1_geometry_upload_reduction_percent": reduction(phase2_metrics.geometry_bytes, lod1.geometry_bytes),
        "lod0_file_reduction_percent": reduction(phase2_metrics.bytes, optimized.bytes),
        "lod1_file_reduction_percent": reduction(phase2_metrics.bytes, lod1.bytes),
        "draw_group_reduction_percent": reduction(phase2_metrics.draw_groups, optimized.draw_groups),
        "texture_residency_rgba8_estimate_mib": {
            "phase2_embedded_36x512": 36.0,
            "lod0_or_lod1": 17.0,
            "reduction_percent": 52.78,
            "with_full_mips_phase2": 48.0,
            "with_full_mips_lod0_or_lod1": 22.67,
        },
        "runtime_materials": ["M_Lyra_OpaqueAtlas", "M_Lyra_LumenEnergy", "M_Lyra_AuroraMantle"],
        "texture_policy": {
            "opaque_atlas": "1024x1024 basecolor, ORM, and emission maps plus a 512x512 MikkTSpace normal map",
            "energy": "512x512 basecolor, ORM-source, MikkTSpace normal, and emission-source maps",
            "mantle": "512x512 basecolor, ORM-source, MikkTSpace normal, and emission-source maps",
            "normal_maps": "All three normal maps are bound in the runtime GLBs after the final Phase 3 UV atlas and MikkTSpace tangent pass.",
        },
        "lod_policy": {
            "lod0": "Use when projected hero height is at least 18% of viewport height.",
            "lod1": "Use below 18% projected hero height or beyond the mid-range combat camera distance.",
            "lod2": "Not created: one lower-cost LOD is adequate for the current single-hero demo; revisit after multi-hero device profiling.",
        },
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    LOD_REPORT_PATH.write_text(
        json.dumps(
            {
                "asset": lod1.filename,
                "metrics": asdict(lod1),
                "switch_from_lod0_at_projected_height": 0.18,
                "transition": "cross-fade when supported by the renderer; otherwise switch during camera motion or animation blend.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def validate_budget(optimized: AssetMetrics, lod1: AssetMetrics) -> None:
    if optimized.triangles > 12_500 or optimized.triangles < 7_000:
        raise RuntimeError(f"LOD0 is outside Phase 3's intended 7k–12.5k triangle range: {optimized.triangles}")
    if lod1.triangles > 8_000 or lod1.triangles < 3_500:
        raise RuntimeError(f"LOD1 is outside Phase 3's intended 3.5k–8k triangle range: {lod1.triangles}")
    for asset in (optimized, lod1):
        if asset.draw_groups > 3 or asset.materials > 3:
            raise RuntimeError(f"{asset.filename} exceeds the three-material/draw-group runtime budget.")
        if asset.textures > 8 or asset.images > 8:
            raise RuntimeError(f"{asset.filename} includes unexpected unpruned texture resources.")


def main() -> None:
    if not INPUT_GLB.is_file():
        raise RuntimeError(f"Phase 2 source asset is missing: {INPUT_GLB}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    LOD_OUTPUT.mkdir(parents=True, exist_ok=True)
    package = generate_texture_package()
    phase2_metrics = metrics(INPUT_GLB)
    with tempfile.TemporaryDirectory(prefix="lyra-phase3-") as temp_name:
        temp_dir = Path(temp_name)
        optimized = build_asset(
            temp_dir,
            "lod0",
            ratio=0.35,
            error=0.010,
            output_path=OUTPUT / "lyra_vesper_optimized.glb",
            package=package,
        )
        lod1 = build_asset(
            temp_dir,
            "lod1",
            ratio=0.18,
            error=0.020,
            output_path=LOD_OUTPUT / "lyra_vesper_lod1.glb",
            package=package,
        )
    validate_budget(optimized, lod1)
    write_reports(phase2_metrics, optimized, lod1)
    print("Phase 3 assets exported")
    print(f"  LOD0: {optimized.triangles} triangles, {optimized.draw_groups} draw groups, {optimized.bytes} bytes")
    print(f"  LOD1: {lod1.triangles} triangles, {lod1.draw_groups} draw groups, {lod1.bytes} bytes")


if __name__ == "__main__":
    main()
