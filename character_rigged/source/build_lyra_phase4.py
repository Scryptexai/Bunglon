#!/usr/bin/env python3
"""Build Lyra Vesper's Phase 4 skinned GLB handoff from the Phase 3 mobile assets.

This builder creates a compact, explicit deform skeleton; assigns four-influence skin
weights to the actual Phase 3 optimized meshes; adds gameplay-neutral helper sockets;
and emits matching rigged LOD0 and LOD1 GLBs. It deliberately does not add production
animation clips — named animation actions are Phase 5 work.

Run from the repository root:
    python3 -m venv /tmp/lyra-phase4-venv
    /tmp/lyra-phase4-venv/bin/pip install -r character_rigged/source/requirements.txt
    /tmp/lyra-phase4-venv/bin/python character_rigged/source/build_lyra_phase4.py
"""

from __future__ import annotations

import json
import struct
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from pygltflib import (
    ARRAY_BUFFER,
    ELEMENT_ARRAY_BUFFER,
    Accessor,
    BufferView,
    GLTF2,
    Node,
    Skin,
)

ROOT = Path(__file__).resolve().parents[2]
P3_LOD0 = ROOT / "character_optimized" / "lyra_vesper_optimized.glb"
P3_LOD1 = ROOT / "character_lod" / "lyra_vesper_lod1.glb"
OUTPUT = ROOT / "character_rigged"
LOD0_OUTPUT = OUTPUT / "lyra_vesper_rigged.glb"
LOD1_OUTPUT = OUTPUT / "lyra_vesper_rigged_lod1.glb"
MANIFEST_PATH = OUTPUT / "rig_manifest.json"
CLI = ("npx", "--yes", "@gltf-transform/cli@4.5.0")

# glTF component types and shape widths used by the narrow binary accessor reader below.
COMPONENT_DTYPES = {
    5120: np.dtype("<i1"),
    5121: np.dtype("<u1"),
    5122: np.dtype("<i2"),
    5123: np.dtype("<u2"),
    5125: np.dtype("<u4"),
    5126: np.dtype("<f4"),
}
ACCESSOR_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


@dataclass(frozen=True)
class BoneSpec:
    name: str
    parent: str | None
    world_position: tuple[float, float, float]
    deform: bool
    role: str


# All positions use the Phase 2/3 meter-scale convention: X left/right, Y depth, Z up.
# The 48 deform joints stay under the 55-bone mobile budget. Six helper nodes do not
# enter skin.joints and therefore do not add skinning palette cost.
BONES: tuple[BoneSpec, ...] = (
    BoneSpec("root", None, (0.0, 0.0, 0.0), False, "skeleton motion root"),
    BoneSpec("pelvis", "root", (0.0, 0.0, 1.67), True, "pelvis deform"),
    BoneSpec("spine_01", "pelvis", (0.0, 0.0, 1.94), True, "lower torso deform"),
    BoneSpec("spine_02", "spine_01", (0.0, 0.0, 2.20), True, "upper torso deform"),
    BoneSpec("chest", "spine_02", (0.0, -0.01, 2.47), True, "chest/shoulder deform"),
    BoneSpec("neck", "chest", (0.0, -0.01, 2.76), True, "neck deform"),
    BoneSpec("head", "neck", (0.0, -0.02, 3.08), True, "head and facial deform"),
    BoneSpec("clavicle_l", "chest", (-0.22, -0.01, 2.56), True, "left clavicle"),
    BoneSpec("upperarm_l", "clavicle_l", (-0.52, -0.04, 2.42), True, "left upper arm"),
    BoneSpec("lowerarm_l", "upperarm_l", (-0.76, -0.14, 2.20), True, "left lower arm"),
    BoneSpec("hand_l", "lowerarm_l", (-0.89, -0.29, 2.02), True, "left hand"),
    BoneSpec("clavicle_r", "chest", (0.22, -0.01, 2.56), True, "right clavicle"),
    BoneSpec("upperarm_r", "clavicle_r", (0.52, -0.04, 2.42), True, "right upper arm"),
    BoneSpec("lowerarm_r", "upperarm_r", (0.76, -0.14, 2.20), True, "right lower arm"),
    BoneSpec("hand_r", "lowerarm_r", (0.89, -0.29, 2.02), True, "right hand / bow carrier"),
    BoneSpec("thigh_l", "pelvis", (-0.22, 0.0, 1.54), True, "left thigh"),
    BoneSpec("calf_l", "thigh_l", (-0.25, 0.0, 0.88), True, "left calf"),
    BoneSpec("foot_l", "calf_l", (-0.27, -0.10, 0.28), True, "left foot"),
    BoneSpec("toe_l", "foot_l", (-0.27, -0.31, 0.10), True, "left toe"),
    BoneSpec("thigh_r", "pelvis", (0.22, 0.0, 1.54), True, "right thigh"),
    BoneSpec("calf_r", "thigh_r", (0.25, 0.0, 0.88), True, "right calf"),
    BoneSpec("foot_r", "calf_r", (0.27, -0.10, 0.28), True, "right foot"),
    BoneSpec("toe_r", "foot_r", (0.27, -0.31, 0.10), True, "right toe"),
    # Two joints per compact digit provide a real bend chain without spending a
    # disproportionate mobile palette on a close-up cinematic hand rig.
    BoneSpec("thumb_01_l", "hand_l", (-0.93, -0.34, 2.03), True, "left thumb base"),
    BoneSpec("thumb_02_l", "thumb_01_l", (-0.99, -0.37, 2.00), True, "left thumb tip"),
    BoneSpec("index_01_l", "hand_l", (-0.94, -0.35, 2.01), True, "left index base"),
    BoneSpec("index_02_l", "index_01_l", (-1.00, -0.38, 1.98), True, "left index tip"),
    BoneSpec("middle_01_l", "hand_l", (-0.95, -0.32, 1.99), True, "left middle base"),
    BoneSpec("middle_02_l", "middle_01_l", (-1.01, -0.35, 1.96), True, "left middle tip"),
    BoneSpec("ring_01_l", "hand_l", (-0.94, -0.29, 1.97), True, "left ring base"),
    BoneSpec("ring_02_l", "ring_01_l", (-1.00, -0.32, 1.94), True, "left ring tip"),
    BoneSpec("pinky_01_l", "hand_l", (-0.93, -0.26, 1.95), True, "left pinky base"),
    BoneSpec("pinky_02_l", "pinky_01_l", (-0.98, -0.29, 1.92), True, "left pinky tip"),
    BoneSpec("thumb_01_r", "hand_r", (0.93, -0.34, 2.03), True, "right thumb base"),
    BoneSpec("thumb_02_r", "thumb_01_r", (0.99, -0.37, 2.00), True, "right thumb tip"),
    BoneSpec("index_01_r", "hand_r", (0.94, -0.35, 2.01), True, "right index base"),
    BoneSpec("index_02_r", "index_01_r", (1.00, -0.38, 1.98), True, "right index tip"),
    BoneSpec("middle_01_r", "hand_r", (0.95, -0.32, 1.99), True, "right middle base"),
    BoneSpec("middle_02_r", "middle_01_r", (1.01, -0.35, 1.96), True, "right middle tip"),
    BoneSpec("ring_01_r", "hand_r", (0.94, -0.29, 1.97), True, "right ring base"),
    BoneSpec("ring_02_r", "ring_01_r", (1.00, -0.32, 1.94), True, "right ring tip"),
    BoneSpec("pinky_01_r", "hand_r", (0.93, -0.26, 1.95), True, "right pinky base"),
    BoneSpec("pinky_02_r", "pinky_01_r", (0.98, -0.29, 1.92), True, "right pinky tip"),
    BoneSpec("hair_root", "head", (0.04, 0.17, 3.47), True, "comet-tail root"),
    BoneSpec("hair_mid", "hair_root", (0.33, 0.28, 3.76), True, "comet-tail mid"),
    BoneSpec("hair_tip", "hair_mid", (0.66, 0.08, 2.95), True, "comet-tail tip"),
    BoneSpec("mantle_root", "chest", (-0.52, 0.02, 2.61), True, "left mantle clasp"),
    BoneSpec("mantle_mid", "mantle_root", (-0.61, 0.14, 2.16), True, "left mantle mid"),
    BoneSpec("mantle_tip", "mantle_mid", (-0.72, 0.13, 1.62), True, "left mantle tip"),
    # Gameplay-neutral attachment helpers. These are nodes, not skin palette joints.
    BoneSpec("socket_weapon", "hand_r", (1.14, -0.14, 2.22), False, "Aster Arc grip attachment"),
    BoneSpec("socket_projectile", "socket_weapon", (0.44, -0.31, 2.22), False, "Aster Arc projectile release"),
    BoneSpec("socket_camera_body", "pelvis", (0.0, 0.0, 1.60), False, "body camera anchor"),
    BoneSpec("socket_camera_chest", "chest", (0.0, -0.08, 2.47), False, "chest camera anchor"),
    BoneSpec("socket_camera_head", "head", (0.0, -0.10, 3.15), False, "head camera anchor"),
    BoneSpec("socket_aim", "chest", (0.0, -0.55, 2.30), False, "aim/targeting anchor"),
)

BONE_BY_NAME = {bone.name: bone for bone in BONES}
DEFORM_BONES = tuple(bone for bone in BONES if bone.deform)
# Leaf helper nodes are included in the skin palette (but never receive vertex weights).
# That keeps the named socket hierarchy explicit in pure core glTF and avoids empty-node
# validation findings without a renderable proxy mesh. Total palette cost remains <= 55.
PALETTE_HELPERS = tuple(bone for bone in BONES if not bone.deform and bone.name != "root")
SKIN_PALETTE_BONES = DEFORM_BONES + PALETTE_HELPERS
DEFORM_NAMES = tuple(bone.name for bone in DEFORM_BONES)
BODY_JOINT_NAMES = tuple(
    name
    for name in DEFORM_NAMES
    if not name.startswith(("hair_", "mantle_", "thumb_", "index_", "middle_", "ring_", "pinky_"))
)
MANTLE_JOINT_NAMES = ("chest", "clavicle_l", "mantle_root", "mantle_mid", "mantle_tip")
HAIR_JOINT_NAMES = ("head", "hair_root", "hair_mid", "hair_tip")
FINGER_PAIRS = {
    "l": (
        ("thumb_01_l", "thumb_02_l"),
        ("index_01_l", "index_02_l"),
        ("middle_01_l", "middle_02_l"),
        ("ring_01_l", "ring_02_l"),
        ("pinky_01_l", "pinky_02_l"),
    ),
    "r": (
        ("thumb_01_r", "thumb_02_r"),
        ("index_01_r", "index_02_r"),
        ("middle_01_r", "middle_02_r"),
        ("ring_01_r", "ring_02_r"),
        ("pinky_01_r", "pinky_02_r"),
    ),
}


@dataclass(frozen=True)
class RiggedMetrics:
    filename: str
    bytes: int
    meshes: int
    nodes: int
    materials: int
    textures: int
    triangles: int
    vertices: int
    geometry_bytes: int
    skin_joints: int
    weighted_vertices: int
    dominant_bone_counts: dict[str, int]


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


def read_accessor(gltf: GLTF2, binary: bytearray, accessor_index: int) -> np.ndarray:
    """Read a non-sparse GLB accessor while honoring byte offsets/strides."""

    accessor = gltf.accessors[accessor_index]
    if accessor.sparse is not None or accessor.bufferView is None:
        raise RuntimeError("Phase 4 supports only non-sparse, buffer-backed accessors.")
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


def append_accessor(
    gltf: GLTF2,
    binary: bytearray,
    values: np.ndarray,
    component_type: int,
    accessor_type: str,
    name: str,
    *,
    normalized: bool = False,
    target: int | None = ARRAY_BUFFER,
) -> tuple[int, bytearray]:
    """Append packed accessor data and return its index plus the extended binary blob."""

    dtype = COMPONENT_DTYPES[component_type]
    values = np.ascontiguousarray(values, dtype=dtype)
    padding = (-len(binary)) % 4
    if padding:
        binary.extend(b"\0" * padding)
    offset = len(binary)
    encoded = values.tobytes(order="C")
    binary.extend(encoded)
    gltf.bufferViews.append(
        BufferView(buffer=0, byteOffset=offset, byteLength=len(encoded), target=target, name=name)
    )
    accessor_index = len(gltf.accessors)
    gltf.accessors.append(
        Accessor(
            bufferView=len(gltf.bufferViews) - 1,
            componentType=component_type,
            normalized=normalized,
            count=len(values),
            type=accessor_type,
            name=name,
        )
    )
    return accessor_index, binary


def set_buffer_targets(gltf: GLTF2) -> None:
    """Apply strict-validator target hints to all vertex/index resource views."""

    vertex_semantics = ("POSITION", "NORMAL", "TANGENT", "TEXCOORD_0", "JOINTS_0", "WEIGHTS_0")
    targets: dict[int, int] = {}
    for mesh in gltf.meshes or []:
        for primitive in mesh.primitives:
            for semantic in vertex_semantics:
                accessor_index = getattr(primitive.attributes, semantic, None)
                if accessor_index is not None:
                    view_index = gltf.accessors[accessor_index].bufferView
                    if view_index is not None:
                        targets[view_index] = ARRAY_BUFFER
            if primitive.indices is not None:
                view_index = gltf.accessors[primitive.indices].bufferView
                if view_index is not None:
                    existing = targets.get(view_index)
                    if existing not in (None, ELEMENT_ARRAY_BUFFER):
                        raise RuntimeError("One bufferView was unexpectedly shared by indices and vertex attributes.")
                    targets[view_index] = ELEMENT_ARRAY_BUFFER
    for view_index, target in targets.items():
        gltf.bufferViews[view_index].target = target


def inverse_distance_weights(position: np.ndarray, candidates: Iterable[str], joint_lookup: dict[str, int]) -> tuple[np.ndarray, np.ndarray]:
    """Give a vertex up to four normalized influences from anatomically local joints."""

    candidate_names = tuple(candidates)
    centers = np.asarray([BONE_BY_NAME[name].world_position for name in candidate_names], dtype=np.float64)
    distances_sq = np.sum((centers - position) ** 2, axis=1)
    count = min(4, len(candidate_names))
    selected = np.argsort(distances_sq, kind="stable")[:count]
    # The small floor prevents a vertex exactly at a joint from erasing useful adjacent
    # influences, while keeping the closest articulated bone dominant.
    inverse = 1.0 / (distances_sq[selected] + 0.0035)
    weights = inverse / inverse.sum()
    joints = np.zeros(4, dtype=np.uint8)
    packed_weights = np.zeros(4, dtype=np.uint8)
    joints[:count] = [joint_lookup[candidate_names[index]] for index in selected]
    encoded = np.rint(weights * 255.0).astype(np.int16)
    encoded[np.argmax(encoded)] += 255 - int(encoded.sum())
    if np.any(encoded < 0) or np.any(encoded > 255):
        raise RuntimeError("Could not quantize skin weights to normalized unsigned bytes.")
    packed_weights[:count] = encoded.astype(np.uint8)
    return joints, packed_weights


def connected_vertex_groups(indices: np.ndarray, vertex_count: int) -> list[np.ndarray]:
    """Return disconnected topology islands so armor/accessory parts can stay rigid.

    The P3 draw-call join intentionally leaves authored components disconnected inside one
    mesh primitive. Skinning every such component per vertex makes hard armor plates shear
    in a bend pose, so Phase 4 preserves rigid component behavior where appropriate.
    """

    parent = np.arange(vertex_count, dtype=np.int64)

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = int(parent[value])
        return value

    def union(first: int, second: int) -> None:
        root_first = find(first)
        root_second = find(second)
        if root_first != root_second:
            parent[root_second] = root_first

    for first, second, third in indices.reshape((-1, 3)):
        union(int(first), int(second))
        union(int(first), int(third))
    groups: dict[int, list[int]] = {}
    for vertex in range(vertex_count):
        groups.setdefault(find(vertex), []).append(vertex)
    return [np.asarray(group, dtype=np.int64) for group in groups.values()]


def needs_blended_component_weights(positions: np.ndarray) -> bool:
    """Recognize a broad anatomical island consistently across the two LOD densities."""

    if len(positions) >= 120:
        return True
    spans = np.ptp(positions, axis=0)
    # LOD1 can reduce a continuous arm/torso island below the raw vertex threshold.
    # Its broad multi-axis extent distinguishes it from a compact rigid armor plate.
    return bool(np.linalg.norm(spans) >= 0.80 and np.count_nonzero(spans >= 0.15) >= 2)


def finger_region(position: np.ndarray) -> str | None:
    """Return hand side for the compact articulated finger region, if applicable."""

    x, y, z = position
    if abs(x) > 0.88 and y < -0.20 and 1.88 < z < 2.08:
        return "l" if x < 0.0 else "r"
    return None


def nearest_finger_pair(position: np.ndarray, side: str) -> tuple[str, ...]:
    """Return two nearest compact digit chains (four joints) for a hand-region vertex."""

    pairs = FINGER_PAIRS[side]
    centers = np.asarray(
        [
            (np.asarray(BONE_BY_NAME[first].world_position) + np.asarray(BONE_BY_NAME[second].world_position)) * 0.5
            for first, second in pairs
        ],
        dtype=np.float64,
    )
    nearest = np.argsort(np.sum((centers - position) ** 2, axis=1), kind="stable")[:2]
    return tuple(name for pair_index in nearest for name in pairs[int(pair_index)])


def weapon_bound(position: np.ndarray, material_name: str) -> bool:
    """Identify the spatially separated Aster Arc and its release arrow region."""

    x, y, z = position
    if x > 1.02:
        return True
    # The arrow/release volume overlaps the right forearm in position space, so only the
    # dedicated energy material may use this secondary test. It intentionally excludes
    # the nearby opaque hand/finger and body geometry.
    return bool(
        material_name == "M_Lyra_LumenEnergy" and x > 0.40 and y < -0.25 and 2.10 < z < 2.34
    )


def weapon_component_bound(positions: np.ndarray, material_name: str) -> bool:
    """Keep every disconnected bow island on the single right-hand carrier chain."""

    # Bow limbs may have centroids just inside the x=1.02 point test even though their
    # outer vertices clearly belong to the right-side Aster Arc. Any such component must
    # move as one rigid held object rather than splitting across forearm/hand weights.
    return bool(any(weapon_bound(position, material_name) for position in positions))


def hair_bound(position: np.ndarray) -> bool:
    """Capture Lyra's high rear comet-tail without binding her face to secondary bones."""

    x, y, z = position
    return bool((z > 3.33 and y > -0.10 and x < 0.95) or (x > 0.24 and y > 0.02 and z > 2.72))


def rigid_weight(joint_name: str, joint_lookup: dict[str, int]) -> tuple[np.ndarray, np.ndarray]:
    joints = np.zeros(4, dtype=np.uint8)
    weights = np.zeros(4, dtype=np.uint8)
    joints[0] = joint_lookup[joint_name]
    weights[0] = 255
    return joints, weights


def closest_joint_name(position: np.ndarray, candidates: Iterable[str]) -> str:
    names = tuple(candidates)
    centers = np.asarray([BONE_BY_NAME[name].world_position for name in names], dtype=np.float64)
    return names[int(np.argmin(np.sum((centers - position) ** 2, axis=1)))]


def assign_vertex_weights(
    position: np.ndarray,
    material_name: str,
    joint_lookup: dict[str, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Choose a stable articulated family, then quantize four local bone influences."""

    if material_name == "M_Lyra_AuroraMantle":
        return inverse_distance_weights(position, MANTLE_JOINT_NAMES, joint_lookup)
    side = finger_region(position)
    if side:
        return inverse_distance_weights(position, nearest_finger_pair(position, side), joint_lookup)
    if weapon_bound(position, material_name):
        # Rigid attachment avoids a rubbery bow when the right arm rotates. The future
        # weapon socket is parented under the same hand bone.
        return rigid_weight("hand_r", joint_lookup)
    if hair_bound(position):
        return inverse_distance_weights(position, HAIR_JOINT_NAMES, joint_lookup)
    return inverse_distance_weights(position, BODY_JOINT_NAMES, joint_lookup)


def assign_rigid_component_weights(
    centroid: np.ndarray,
    material_name: str,
    joint_lookup: dict[str, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Attach an authored disconnected plate/accessory to its nearest appropriate bone."""

    if material_name == "M_Lyra_AuroraMantle":
        return inverse_distance_weights(centroid, MANTLE_JOINT_NAMES, joint_lookup)
    side = finger_region(centroid)
    if side:
        return inverse_distance_weights(centroid, nearest_finger_pair(centroid, side), joint_lookup)
    if weapon_bound(centroid, material_name):
        return rigid_weight("hand_r", joint_lookup)
    candidates = HAIR_JOINT_NAMES if hair_bound(centroid) else BODY_JOINT_NAMES
    return rigid_weight(closest_joint_name(centroid, candidates), joint_lookup)


def add_skeleton(gltf: GLTF2, binary: bytearray) -> tuple[dict[str, int], dict[str, int], bytearray]:
    """Append hierarchy nodes and one skin with inverse bind matrices."""

    if gltf.skins:
        raise RuntimeError("Phase 3 input unexpectedly already contains a skin.")
    if gltf.nodes is None:
        gltf.nodes = []
    node_indices: dict[str, int] = {}
    world_positions = {bone.name: np.asarray(bone.world_position, dtype=float) for bone in BONES}
    for bone in BONES:
        parent_world = world_positions[bone.parent] if bone.parent else np.zeros(3)
        local = world_positions[bone.name] - parent_world
        node_indices[bone.name] = len(gltf.nodes)
        gltf.nodes.append(Node(name=bone.name, translation=local.tolist(), children=[]))
    for bone in BONES:
        if bone.parent:
            gltf.nodes[node_indices[bone.parent]].children.append(node_indices[bone.name])

    if gltf.scenes is None or not gltf.scenes:
        raise RuntimeError("Phase 3 input has no scene to receive the armature root.")
    scene_index = gltf.scene if gltf.scene is not None else 0
    if gltf.scenes[scene_index].nodes is None:
        gltf.scenes[scene_index].nodes = []
    gltf.scenes[scene_index].nodes.append(node_indices["root"])

    joint_nodes = [node_indices[bone.name] for bone in SKIN_PALETTE_BONES]
    # Vertex weights deliberately use only the first 48 deform-joint palette entries;
    # helper entries are skeleton/socket handles, not deform influences.
    joint_lookup = {bone.name: index for index, bone in enumerate(DEFORM_BONES)}
    inverse_bind = []
    for bone in SKIN_PALETTE_BONES:
        matrix = np.identity(4, dtype=np.float32)
        matrix[:3, 3] = -world_positions[bone.name]
        # glTF matrices are stored column-major.
        inverse_bind.append(matrix.T.reshape(16))
    inverse_accessor, binary = append_accessor(
        gltf,
        binary,
        np.asarray(inverse_bind, dtype=np.float32),
        5126,
        "MAT4",
        "LyraVesper_InverseBindMatrices",
        target=None,
    )
    gltf.skins = [
        Skin(
            name="LyraVesper_DeformRig",
            joints=joint_nodes,
            skeleton=node_indices["root"],
            inverseBindMatrices=inverse_accessor,
        )
    ]
    return node_indices, joint_lookup, binary


def attach_skin_and_weights(gltf: GLTF2, binary: bytearray, joint_lookup: dict[str, int]) -> tuple[bytearray, dict[str, int]]:
    """Attach the skin to every P3 mesh node and write JOINTS_0/WEIGHTS_0 streams."""

    mesh_nodes = [node for node in gltf.nodes if node.mesh is not None]
    if len(mesh_nodes) != 3:
        raise RuntimeError(f"Expected the three Phase 3 runtime mesh nodes, found {len(mesh_nodes)}.")
    for node in mesh_nodes:
        node.skin = 0

    dominant_counts = {name: 0 for name in DEFORM_NAMES}
    for mesh in gltf.meshes or []:
        for primitive in mesh.primitives:
            if primitive.attributes.POSITION is None:
                raise RuntimeError("Mesh primitive has no POSITION data.")
            material_name = gltf.materials[primitive.material].name
            positions = read_accessor(gltf, binary, primitive.attributes.POSITION).astype(np.float64)
            if primitive.indices is None:
                raise RuntimeError("Phase 3 primitive unexpectedly has no triangle indices.")
            indices = read_accessor(gltf, binary, primitive.indices).reshape(-1).astype(np.int64)
            if len(indices) % 3:
                raise RuntimeError("A triangle primitive had a non-triple index count.")
            components = connected_vertex_groups(indices, len(positions))
            joints = np.empty((len(positions), 4), dtype=np.uint8)
            weights = np.empty((len(positions), 4), dtype=np.uint8)
            for component in components:
                component_positions = positions[component]
                centroid = component_positions.mean(axis=0)
                # Large connected anatomy and hair sections need blended vertex weights.
                # Small disconnected armor, facial, quiver, and bow pieces stay rigid at
                # their closest appropriate joint to prevent plate/shear artifacts.
                if weapon_component_bound(component_positions, material_name):
                    vertex_joints, vertex_weights = rigid_weight("hand_r", joint_lookup)
                    joints[component] = vertex_joints
                    weights[component] = vertex_weights
                    dominant_counts["hand_r"] += len(component)
                    continue
                use_blended_weights = (
                    material_name == "M_Lyra_AuroraMantle"
                    or needs_blended_component_weights(component_positions)
                    or hair_bound(centroid)
                )
                if use_blended_weights:
                    for index in component:
                        vertex_joints, vertex_weights = assign_vertex_weights(
                            positions[index], material_name, joint_lookup
                        )
                        joints[index] = vertex_joints
                        weights[index] = vertex_weights
                        dominant_counts[DEFORM_NAMES[int(vertex_joints[0])]] += 1
                else:
                    vertex_joints, vertex_weights = assign_rigid_component_weights(
                        centroid, material_name, joint_lookup
                    )
                    joints[component] = vertex_joints
                    weights[component] = vertex_weights
                    dominant_counts[DEFORM_NAMES[int(vertex_joints[0])]] += len(component)
            joint_accessor, binary = append_accessor(
                gltf, binary, joints, 5121, "VEC4", f"{mesh.name}_JOINTS_0", normalized=False
            )
            weight_accessor, binary = append_accessor(
                gltf, binary, weights, 5121, "VEC4", f"{mesh.name}_WEIGHTS_0", normalized=True
            )
            primitive.attributes.JOINTS_0 = joint_accessor
            primitive.attributes.WEIGHTS_0 = weight_accessor
    return binary, dominant_counts


def rig_asset(source: Path, destination: Path) -> RiggedMetrics:
    if not source.is_file():
        raise RuntimeError(f"Missing Phase 3 input: {source}")
    gltf = GLTF2().load_binary(source)
    binary = bytearray(gltf.binary_blob())
    _, joint_lookup, binary = add_skeleton(gltf, binary)
    binary, dominant_counts = attach_skin_and_weights(gltf, binary, joint_lookup)
    gltf.set_binary_blob(bytes(binary))
    gltf.buffers[0].byteLength = len(binary)
    set_buffer_targets(gltf)
    destination.parent.mkdir(parents=True, exist_ok=True)
    gltf.save_binary(destination)
    command(*CLI, "validate", str(destination))
    return collect_metrics(destination, dominant_counts)


def collect_metrics(path: Path, dominant_counts: dict[str, int] | None = None) -> RiggedMetrics:
    document = load_glb_json(path)
    triangles = 0
    vertices = 0
    weighted_vertices = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh["primitives"]:
            triangles += document["accessors"][primitive["indices"]]["count"] // 3
            position_count = document["accessors"][primitive["attributes"]["POSITION"]]["count"]
            vertices += position_count
            if "WEIGHTS_0" in primitive["attributes"]:
                weighted_vertices += document["accessors"][primitive["attributes"]["WEIGHTS_0"]]["count"]
    geometry_bytes = sum(
        view["byteLength"]
        for view in document.get("bufferViews", [])
        if view.get("target") in (ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER)
    )
    skin_joints = len(document.get("skins", [{}])[0].get("joints", []))
    return RiggedMetrics(
        filename=path.name,
        bytes=path.stat().st_size,
        meshes=len(document.get("meshes", [])),
        nodes=len(document.get("nodes", [])),
        materials=len(document.get("materials", [])),
        textures=len(document.get("textures", [])),
        triangles=triangles,
        vertices=vertices,
        geometry_bytes=geometry_bytes,
        skin_joints=skin_joints,
        weighted_vertices=weighted_vertices,
        dominant_bone_counts=dominant_counts or {},
    )


def verify_rig_metrics(lod0: RiggedMetrics, lod1: RiggedMetrics) -> None:
    for asset in (lod0, lod1):
        if asset.skin_joints != len(SKIN_PALETTE_BONES):
            raise RuntimeError(f"{asset.filename}: expected {len(SKIN_PALETTE_BONES)} skin-palette joints.")
        if asset.nodes != 3 + len(BONES):
            raise RuntimeError(f"{asset.filename}: unexpected node count {asset.nodes}.")
        if asset.weighted_vertices != asset.vertices:
            raise RuntimeError(f"{asset.filename}: not every vertex has a skin-weight record.")
        if asset.triangles < 3_500:
            raise RuntimeError(f"{asset.filename}: damaged Phase 3 triangle count.")
        missing_used = [name for name, count in asset.dominant_bone_counts.items() if count == 0]
        # Not every fine finger tip must be dominant in the low-distance LOD; the skeleton
        # remains valid. Core/hair/mantle chains must all affect the actual asset.
        critical = {"pelvis", "chest", "head", "hand_l", "hand_r", "thigh_l", "thigh_r", "hair_root", "mantle_root", "mantle_tip"}
        if critical.intersection(missing_used):
            raise RuntimeError(f"{asset.filename}: critical deform bones received no dominant weights: {sorted(critical.intersection(missing_used))}")


def write_manifest(lod0: RiggedMetrics, lod1: RiggedMetrics) -> None:
    helper_bones = [bone.name for bone in BONES if not bone.deform and bone.name != "root"]
    payload = {
        "phase": 4,
        "asset": "Lyra Vesper rigging and skinning handoff",
        "source_assets": {
            "lod0": str(P3_LOD0.relative_to(ROOT)),
            "lod1": str(P3_LOD1.relative_to(ROOT)),
        },
        "rigged_lod0": asdict(lod0),
        "rigged_lod1": asdict(lod1),
        "skeleton": {
            "coordinate_convention": "X left/right, Y depth, Z up; meter scale",
            "root": "root",
            "deform_joint_count": len(DEFORM_BONES),
            "skin_palette_joint_count": len(SKIN_PALETTE_BONES),
            "total_skeleton_node_count": len(BONES),
            "helper_node_count": len(helper_bones),
            "deform_bones": [asdict(bone) for bone in DEFORM_BONES],
            "helpers": [asdict(BONE_BY_NAME[name]) for name in helper_bones],
        },
        "skinning": {
            "skin_name": "LyraVesper_DeformRig",
            "joint_attribute": "JOINTS_0 UNSIGNED_BYTE VEC4",
            "weight_attribute": "WEIGHTS_0 normalized UNSIGNED_BYTE VEC4",
            "max_influences": 4,
            "weight_policy": "Large connected anatomy, hair, and mantle regions use local inverse-distance blends; small disconnected hard-surface/accessory islands use cohesive nearest-joint binding; compact finger regions blend their two nearest digit chains; the Aster Arc and release geometry bind rigidly to hand_r.",
            "inverse_bind_matrices": "One float MAT4 per skin-palette joint, generated from the explicit rest hierarchy.",
        },
        "phase_boundary": {
            "production_animations": "Not included — Phase 5 owns named animation actions.",
            "godot_import": "Not yet verified — Phase 6 owns real engine import validation.",
            "deformation_evidence": "Generated by source/render_phase4_validation.py into validation/deformation_report.json and renders/.",
        },
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    lod0 = rig_asset(P3_LOD0, LOD0_OUTPUT)
    lod1 = rig_asset(P3_LOD1, LOD1_OUTPUT)
    verify_rig_metrics(lod0, lod1)
    write_manifest(lod0, lod1)
    print("Phase 4 rigged assets exported")
    print(f"  LOD0: {len(DEFORM_BONES)} deform / {lod0.skin_joints} palette joints, {lod0.vertices} weighted vertices, {lod0.bytes} bytes")
    print(f"  LOD1: {len(DEFORM_BONES)} deform / {lod1.skin_joints} palette joints, {lod1.vertices} weighted vertices, {lod1.bytes} bytes")


if __name__ == "__main__":
    main()
