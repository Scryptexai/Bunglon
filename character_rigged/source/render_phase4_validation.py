#!/usr/bin/env python3
"""Evaluate and render Phase 4 skin deformation poses without requiring a GPU DCC.

The script reads the actual rigged GLBs, evaluates their glTF skin attributes with linear
blend skinning, records deterministic numerical checks, and writes CPU/Matplotlib review
renders. It does not add animation clips to the delivery asset; those belong to Phase 5.
"""

from __future__ import annotations

import json
import math
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image
from pygltflib import GLTF2

from build_lyra_phase4 import ACCESSOR_COMPONENTS, COMPONENT_DTYPES, ROOT, read_accessor

OUTPUT = ROOT / "character_rigged"
LOD0 = OUTPUT / "lyra_vesper_rigged.glb"
LOD1 = OUTPUT / "lyra_vesper_rigged_lod1.glb"
RENDERS = OUTPUT / "renders"
VALIDATION = OUTPUT / "validation"
REPORT = VALIDATION / "deformation_report.json"
EPSILON = 1e-8
HELPER_PARENTS = {
    "socket_weapon": "hand_r",
    "socket_projectile": "socket_weapon",
    "socket_camera_body": "pelvis",
    "socket_camera_chest": "chest",
    "socket_camera_head": "head",
    "socket_aim": "chest",
}

# These are inspection poses, not shipping actions. They exercise the high-risk chains:
# knees/hips, shoulders/elbows/wrists, fingers, bow carrier, hair, and mantle.
POSE_ROTATIONS: dict[str, dict[str, tuple[tuple[float, float, float], float]]] = {
    "bind": {},
    "draw": {
        # A deliberately moderate aim/draw exercise. It is strong enough to test the
        # shoulder/elbow/wrist/bow chain but avoids pretending this static QA pose is
        # a polished Phase 5 attack animation.
        "spine_02": ((0.0, 1.0, 0.0), -3.0),
        "chest": ((0.0, 1.0, 0.0), -4.0),
        "clavicle_l": ((0.0, 1.0, 0.0), 6.0),
        "upperarm_l": ((0.0, 1.0, 0.0), 11.0),
        "lowerarm_l": ((0.0, 1.0, 0.0), 15.0),
        "hand_l": ((1.0, 0.0, 0.0), -7.0),
        "thumb_01_l": ((0.0, 1.0, 0.0), 4.0),
        "thumb_02_l": ((0.0, 1.0, 0.0), 6.0),
        "index_01_l": ((0.0, 1.0, 0.0), 8.0),
        "index_02_l": ((0.0, 1.0, 0.0), 9.0),
        "middle_01_l": ((0.0, 1.0, 0.0), 7.0),
        "middle_02_l": ((0.0, 1.0, 0.0), 8.0),
        "ring_01_l": ((0.0, 1.0, 0.0), 6.0),
        "ring_02_l": ((0.0, 1.0, 0.0), 7.0),
        "pinky_01_l": ((0.0, 1.0, 0.0), 5.0),
        "pinky_02_l": ((0.0, 1.0, 0.0), 6.0),
        "clavicle_r": ((0.0, 1.0, 0.0), -5.0),
        "upperarm_r": ((0.0, 1.0, 0.0), -10.0),
        "lowerarm_r": ((0.0, 1.0, 0.0), -14.0),
        "hand_r": ((1.0, 0.0, 0.0), 6.0),
        "thumb_01_r": ((0.0, 1.0, 0.0), -4.0),
        "thumb_02_r": ((0.0, 1.0, 0.0), -6.0),
        "index_01_r": ((0.0, 1.0, 0.0), -8.0),
        "index_02_r": ((0.0, 1.0, 0.0), -9.0),
        "middle_01_r": ((0.0, 1.0, 0.0), -7.0),
        "middle_02_r": ((0.0, 1.0, 0.0), -8.0),
        "ring_01_r": ((0.0, 1.0, 0.0), -6.0),
        "ring_02_r": ((0.0, 1.0, 0.0), -7.0),
        "pinky_01_r": ((0.0, 1.0, 0.0), -5.0),
        "pinky_02_r": ((0.0, 1.0, 0.0), -6.0),
        "hair_mid": ((0.0, 1.0, 0.0), -9.0),
        "hair_tip": ((0.0, 1.0, 0.0), -14.0),
        "mantle_mid": ((1.0, 0.0, 0.0), 7.0),
        "mantle_tip": ((1.0, 0.0, 0.0), 12.0),
    },
    "crouch": {
        "pelvis": ((1.0, 0.0, 0.0), 8.0),
        "spine_01": ((1.0, 0.0, 0.0), -10.0),
        "spine_02": ((1.0, 0.0, 0.0), -12.0),
        "thigh_l": ((1.0, 0.0, 0.0), 29.0),
        "calf_l": ((1.0, 0.0, 0.0), -52.0),
        "foot_l": ((1.0, 0.0, 0.0), 16.0),
        "thigh_r": ((1.0, 0.0, 0.0), 29.0),
        "calf_r": ((1.0, 0.0, 0.0), -52.0),
        "foot_r": ((1.0, 0.0, 0.0), 16.0),
        "upperarm_l": ((0.0, 1.0, 0.0), 10.0),
        "upperarm_r": ((0.0, 1.0, 0.0), -10.0),
        "hair_mid": ((0.0, 1.0, 0.0), 15.0),
        "hair_tip": ((0.0, 1.0, 0.0), 25.0),
        "mantle_mid": ((1.0, 0.0, 0.0), 18.0),
        "mantle_tip": ((1.0, 0.0, 0.0), 30.0),
    },
}


def translation_matrix(values: list[float] | None) -> np.ndarray:
    matrix = np.identity(4, dtype=np.float64)
    if values:
        matrix[:3, 3] = values
    return matrix


def rotation_matrix(axis: tuple[float, float, float], degrees: float) -> np.ndarray:
    unit = np.asarray(axis, dtype=np.float64)
    unit /= max(float(np.linalg.norm(unit)), EPSILON)
    x, y, z = unit
    angle = math.radians(degrees)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    complement = 1.0 - cosine
    result = np.identity(4, dtype=np.float64)
    result[:3, :3] = np.array(
        (
            (cosine + x * x * complement, x * y * complement - z * sine, x * z * complement + y * sine),
            (y * x * complement + z * sine, cosine + y * y * complement, y * z * complement - x * sine),
            (z * x * complement - y * sine, z * y * complement + x * sine, cosine + z * z * complement),
        )
    )
    return result


def node_parents(gltf: GLTF2) -> dict[int, int | None]:
    parents: dict[int, int | None] = {index: None for index in range(len(gltf.nodes))}
    for parent_index, node in enumerate(gltf.nodes):
        for child_index in node.children or []:
            if parents[child_index] is not None:
                raise RuntimeError(f"Node {child_index} has multiple parents.")
            parents[child_index] = parent_index
    return parents


def node_local_matrix(node, pose: dict[str, tuple[tuple[float, float, float], float]]) -> np.ndarray:
    if node.matrix:
        # Phase 4 builder emits translation-only hierarchy nodes. Supporting matrix nodes
        # here prevents silently evaluating an incompatible input as identity.
        values = np.asarray(node.matrix, dtype=float).reshape((4, 4), order="F")
        if node.name in pose:
            raise RuntimeError(f"Pose rotation requested for matrix-authored node {node.name}.")
        return values
    matrix = translation_matrix(node.translation)
    if node.name in pose:
        axis, degrees = pose[node.name]
        matrix = matrix @ rotation_matrix(axis, degrees)
    return matrix


def global_matrices(gltf: GLTF2, pose: dict[str, tuple[tuple[float, float, float], float]]) -> list[np.ndarray]:
    parents = node_parents(gltf)
    cache: list[np.ndarray | None] = [None] * len(gltf.nodes)

    def resolve(index: int) -> np.ndarray:
        if cache[index] is not None:
            return cache[index]
        local = node_local_matrix(gltf.nodes[index], pose)
        parent = parents[index]
        cache[index] = local if parent is None else resolve(parent) @ local
        return cache[index]

    return [resolve(index) for index in range(len(gltf.nodes))]


def helper_socket_audit(path: Path) -> dict[str, dict[str, object]]:
    """Confirm named helper nodes are in the exported hierarchy and follow their parents."""

    gltf = GLTF2().load_binary(path)
    if not gltf.skins or len(gltf.skins) != 1:
        raise RuntimeError("Expected exactly one Phase 4 skin for helper audit.")
    names = {node.name: index for index, node in enumerate(gltf.nodes) if node.name}
    parents = node_parents(gltf)
    rest = global_matrices(gltf, {})
    draw = global_matrices(gltf, POSE_ROTATIONS["draw"])
    crouch = global_matrices(gltf, POSE_ROTATIONS["crouch"])
    palette = set(gltf.skins[0].joints)
    result: dict[str, dict[str, object]] = {}
    for helper_name, expected_parent_name in HELPER_PARENTS.items():
        if helper_name not in names or expected_parent_name not in names:
            raise RuntimeError(f"Missing required helper or parent: {helper_name} -> {expected_parent_name}")
        helper_index = names[helper_name]
        parent_index = parents[helper_index]
        actual_parent_name = gltf.nodes[parent_index].name if parent_index is not None else None
        if actual_parent_name != expected_parent_name:
            raise RuntimeError(
                f"{helper_name} parent mismatch: expected {expected_parent_name}, got {actual_parent_name}"
            )
        if helper_index not in palette:
            raise RuntimeError(f"{helper_name} is absent from the skin palette.")
        rest_position = rest[helper_index][:3, 3]
        result[helper_name] = {
            "parent": actual_parent_name,
            "palette_joint": True,
            "rest_position": [round(float(value), 6) for value in rest_position],
            "draw_displacement_m": round(
                float(np.linalg.norm(draw[helper_index][:3, 3] - rest_position)), 6
            ),
            "crouch_displacement_m": round(
                float(np.linalg.norm(crouch[helper_index][:3, 3] - rest_position)), 6
            ),
        }
    if result["socket_weapon"]["draw_displacement_m"] <= 0.001:
        raise RuntimeError("Weapon socket did not follow the draw hand chain.")
    if result["socket_projectile"]["draw_displacement_m"] <= 0.001:
        raise RuntimeError("Projectile socket did not follow the weapon/hand chain.")
    if result["socket_camera_body"]["crouch_displacement_m"] <= 0.001:
        raise RuntimeError("Body camera socket did not follow the crouch pelvis chain.")
    return result


def skin_matrices(
    gltf: GLTF2,
    binary: bytearray,
    pose: dict[str, tuple[tuple[float, float, float], float]],
) -> tuple[np.ndarray, list[np.ndarray], float]:
    """Use and validate the actual exported inverse-bind accessor for an LBS pose."""

    if not gltf.skins or len(gltf.skins) != 1:
        raise RuntimeError("Expected exactly one Phase 4 skin.")
    skin = gltf.skins[0]
    if skin.inverseBindMatrices is None:
        raise RuntimeError("Phase 4 skin is missing inverse bind matrices.")
    rest = global_matrices(gltf, {})
    posed = global_matrices(gltf, pose)
    raw_inverse_bind = read_accessor(gltf, binary, skin.inverseBindMatrices).astype(np.float64)
    if len(raw_inverse_bind) != len(skin.joints):
        raise RuntimeError("Inverse-bind matrix count does not match the skin palette.")
    # glTF stores MAT4 values in column-major order. The builder writes matrix.T as
    # packed rows, so transpose each decoded record back to a conventional matrix.
    exported_inverse_bind = raw_inverse_bind.reshape((-1, 4, 4)).transpose((0, 2, 1))
    expected_inverse_bind = np.asarray([np.linalg.inv(rest[node_index]) for node_index in skin.joints])
    maximum_error = float(np.max(np.abs(exported_inverse_bind - expected_inverse_bind)))
    if maximum_error > 2e-6:
        raise RuntimeError(f"Exported inverse-bind matrices do not match rest hierarchy ({maximum_error:.8f}).")
    matrices = np.asarray(
        [posed[node_index] @ exported_inverse_bind[index] for index, node_index in enumerate(skin.joints)]
    )
    return matrices, posed, maximum_error


def decode_weights(gltf: GLTF2, binary: bytearray, accessor_index: int) -> np.ndarray:
    accessor = gltf.accessors[accessor_index]
    weights = read_accessor(gltf, binary, accessor_index).astype(np.float64)
    if accessor.normalized:
        maximum = {5121: 255.0, 5123: 65535.0, 5125: 4294967295.0}[accessor.componentType]
        weights /= maximum
    return weights


def deform_primitive(gltf: GLTF2, binary: bytearray, primitive, matrices: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    attributes = primitive.attributes
    positions = read_accessor(gltf, binary, attributes.POSITION).astype(np.float64)
    uvs = read_accessor(gltf, binary, attributes.TEXCOORD_0).astype(np.float64)
    joints = read_accessor(gltf, binary, attributes.JOINTS_0).astype(np.int64)
    weights = decode_weights(gltf, binary, attributes.WEIGHTS_0)
    if not np.allclose(weights.sum(axis=1), 1.0, atol=1.0 / 255.0 + 1e-8):
        raise RuntimeError("A skin weight row does not sum to one.")
    if int(joints.max()) >= len(matrices):
        raise RuntimeError("A skin joint index exceeds the skin palette.")
    homogeneous = np.concatenate((positions, np.ones((len(positions), 1))), axis=1)
    deformed = np.zeros((len(positions), 4), dtype=np.float64)
    for influence in range(4):
        per_vertex_matrices = matrices[joints[:, influence]]
        transformed = np.einsum("nij,nj->ni", per_vertex_matrices, homogeneous)
        deformed += transformed * weights[:, influence, None]
    if not np.allclose(deformed[:, 3], 1.0, atol=1e-5):
        deformed[:, :3] /= np.maximum(deformed[:, 3:4], EPSILON)
    faces = read_accessor(gltf, binary, primitive.indices).reshape(-1, 3).astype(np.int64)
    return positions, deformed[:, :3], uvs, faces


def image_for_material(gltf: GLTF2, binary: bytearray, material_index: int) -> Image.Image:
    material = gltf.materials[material_index]
    texture_index = material.pbrMetallicRoughness.baseColorTexture.index
    texture = gltf.textures[texture_index]
    image = gltf.images[texture.source]
    view = gltf.bufferViews[image.bufferView]
    start = int(view.byteOffset or 0)
    encoded = bytes(binary[start : start + view.byteLength])
    return Image.open(BytesIO(encoded)).convert("RGB")


def face_colors(texture: Image.Image, uvs: np.ndarray, faces: np.ndarray, material_name: str, normals: np.ndarray) -> np.ndarray:
    pixels = np.asarray(texture, dtype=np.float32) / 255.0
    height, width = pixels.shape[:2]
    centers = uvs[faces].mean(axis=1)
    # The P3 atlas was written in the same top-origin convention as its packed glTF
    # UV values. This raw accessor evaluator must not apply trimesh's convenience V flip.
    x = np.clip((centers[:, 0] * (width - 1)).astype(np.int32), 0, width - 1)
    y = np.clip((centers[:, 1] * (height - 1)).astype(np.int32), 0, height - 1)
    colors = pixels[y, x]
    if material_name == "M_Lyra_LumenEnergy":
        colors = np.clip(colors * np.array((0.68, 1.15, 1.20)), 0.0, 1.0)
    light = np.asarray((-0.72, -0.84, 1.18), dtype=np.float64)
    light /= np.linalg.norm(light)
    shade = 0.42 + 0.58 * np.clip(normals @ light, 0.0, 1.0)
    rgba = np.empty((len(colors), 4), dtype=np.float32)
    rgba[:, :3] = np.clip(colors * shade[:, None], 0.0, 1.0)
    rgba[:, 3] = 0.78 if material_name == "M_Lyra_AuroraMantle" else 1.0
    return rgba


def draw_skeleton(axis, gltf: GLTF2, posed: list[np.ndarray]) -> None:
    parents = node_parents(gltf)
    skin_nodes = set(gltf.skins[0].joints)
    for child_index in skin_nodes:
        parent_index = parents[child_index]
        if parent_index not in skin_nodes:
            continue
        start = posed[parent_index][:3, 3]
        end = posed[child_index][:3, 3]
        axis.plot(
            (start[0], end[0]),
            (start[1], end[1]),
            (start[2], end[2]),
            color="#84efff",
            linewidth=0.45,
            alpha=0.40,
            zorder=10,
        )


def render_pose(path: Path, pose_name: str, filename: str, azimuth: float) -> dict[str, object]:
    gltf = GLTF2().load_binary(path)
    binary = bytearray(gltf.binary_blob())
    matrices, posed, inverse_bind_error = skin_matrices(gltf, binary, POSE_ROTATIONS[pose_name])
    figure = plt.figure(figsize=(7.5, 8.5), dpi=170, facecolor="#e8ebf2")
    axis = figure.add_subplot(111, projection="3d")
    axis.set_facecolor("#e8ebf2")
    all_rest: list[np.ndarray] = []
    all_deformed: list[np.ndarray] = []
    primitive_data = []
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            rest, deformed, uvs, faces = deform_primitive(gltf, binary, primitive, matrices)
            normals = np.cross(
                deformed[faces[:, 1]] - deformed[faces[:, 0]],
                deformed[faces[:, 2]] - deformed[faces[:, 0]],
            )
            normal_lengths = np.maximum(np.linalg.norm(normals, axis=1), EPSILON)
            normals /= normal_lengths[:, None]
            material_name = gltf.materials[primitive.material].name
            primitive_data.append((deformed, faces, face_colors(image_for_material(gltf, binary, primitive.material), uvs, faces, material_name, normals), material_name))
            all_rest.append(rest)
            all_deformed.append(deformed)
    # Opaque groups first, double-sided mantle last for a more legible static proof.
    for deformed, faces, colors, material_name in sorted(
        primitive_data, key=lambda entry: entry[3] == "M_Lyra_AuroraMantle"
    ):
        axis.add_collection3d(Poly3DCollection(deformed[faces], facecolors=colors, edgecolors="none", linewidths=0.0))
    draw_skeleton(axis, gltf, posed)
    grid_x, grid_y = np.meshgrid(np.linspace(-2.0, 2.0, 2), np.linspace(-1.5, 1.5, 2))
    axis.plot_surface(grid_x, grid_y, np.zeros_like(grid_x) - 0.015, color="#c9ceda", alpha=0.28, shade=False)
    axis.set_proj_type("ortho")
    axis.view_init(elev=8.5, azim=azimuth)
    axis.set_xlim(-1.75, 2.15)
    axis.set_ylim(-1.45, 1.25)
    axis.set_zlim(-0.18, 3.95)
    axis.set_box_aspect((3.9, 2.7, 4.1))
    axis.set_axis_off()
    figure.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
    RENDERS.mkdir(parents=True, exist_ok=True)
    figure.savefig(RENDERS / filename, facecolor=figure.get_facecolor(), transparent=False)
    plt.close(figure)

    rest_points = np.concatenate(all_rest, axis=0)
    deformed_points = np.concatenate(all_deformed, axis=0)
    displacement = np.linalg.norm(deformed_points - rest_points, axis=1)
    return {
        "pose": pose_name,
        "vertices": int(len(rest_points)),
        "vertices_moved_over_1mm": int(np.count_nonzero(displacement > 0.001)),
        "mean_displacement_m": round(float(displacement.mean()), 6),
        "max_displacement_m": round(float(displacement.max()), 6),
        "inverse_bind_max_abs_error": round(inverse_bind_error, 9),
        "rest_bounds": {
            "min": [round(float(value), 6) for value in rest_points.min(axis=0)],
            "max": [round(float(value), 6) for value in rest_points.max(axis=0)],
        },
        "deformed_bounds": {
            "min": [round(float(value), 6) for value in deformed_points.min(axis=0)],
            "max": [round(float(value), 6) for value in deformed_points.max(axis=0)],
        },
        "rotated_bones": sorted(POSE_ROTATIONS[pose_name]),
    }


def audit_weights(path: Path) -> dict[str, object]:
    gltf = GLTF2().load_binary(path)
    binary = bytearray(gltf.binary_blob())
    skin = gltf.skins[0]
    joint_names = [gltf.nodes[node_index].name for node_index in skin.joints]
    influence_counts = {name: 0 for name in joint_names}
    dominant_counts = {name: 0 for name in joint_names}
    sums: list[np.ndarray] = []
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            joints = read_accessor(gltf, binary, primitive.attributes.JOINTS_0).astype(np.int64)
            weights = decode_weights(gltf, binary, primitive.attributes.WEIGHTS_0)
            sums.append(weights.sum(axis=1))
            for column in range(4):
                active = weights[:, column] > 0.0
                for joint_index, count in zip(*np.unique(joints[active, column], return_counts=True)):
                    influence_counts[joint_names[int(joint_index)]] += int(count)
            dominant = joints[np.arange(len(joints)), np.argmax(weights, axis=1)]
            for joint_index, count in zip(*np.unique(dominant, return_counts=True)):
                dominant_counts[joint_names[int(joint_index)]] += int(count)
    total_sums = np.concatenate(sums)
    return {
        "skin_palette_joint_count": len(joint_names),
        "weighted_vertex_count": int(len(total_sums)),
        "weight_sum_min": round(float(total_sums.min()), 8),
        "weight_sum_max": round(float(total_sums.max()), 8),
        "weight_sum_mean": round(float(total_sums.mean()), 8),
        "influence_counts": influence_counts,
        "dominant_bone_counts": dominant_counts,
        "unused_deform_joints": [name for name, count in influence_counts.items() if count == 0 and not name.startswith("socket_")],
    }


def assert_pose_quality(report: dict[str, object]) -> None:
    for label in ("lod0", "lod1"):
        audit = report[label]["weight_audit"]
        if audit["weight_sum_min"] < 0.995 or audit["weight_sum_max"] > 1.005:
            raise RuntimeError(f"{label}: invalid normalized skin weight sum range.")
        if audit["unused_deform_joints"]:
            raise RuntimeError(f"{label}: deform joints without nonzero influences: {audit['unused_deform_joints']}")
        for pose_name in ("bind", "draw", "crouch"):
            pose = report[label]["poses"][pose_name]
            if pose["inverse_bind_max_abs_error"] > 0.000002:
                raise RuntimeError(f"{label}/{pose_name}: inverse-bind accessor is inconsistent with rest hierarchy.")
            if pose_name == "bind":
                continue
            if pose["vertices_moved_over_1mm"] < 100:
                raise RuntimeError(f"{label}/{pose_name}: deformation pose moved too few vertices.")
            if not np.isfinite(pose["max_displacement_m"]) or pose["max_displacement_m"] > 3.0:
                raise RuntimeError(f"{label}/{pose_name}: deformation has invalid displacement.")


def main() -> None:
    if not LOD0.is_file() or not LOD1.is_file():
        raise RuntimeError("Build Phase 4 rigged GLBs before running deformation validation.")
    # LOD0 supplies 360° bind proof plus two high-risk deformations; LOD1 draw proof
    # verifies that the lower-density mesh retains the same skeleton contract.
    rendered = {
        "bind": render_pose(LOD0, "bind", "lyra_phase4_bind_three_quarter.png", -58.0),
        "draw": render_pose(LOD0, "draw", "lyra_phase4_draw_three_quarter.png", -58.0),
        "crouch": render_pose(LOD0, "crouch", "lyra_phase4_crouch_three_quarter.png", -58.0),
        "lod1_draw": render_pose(LOD1, "draw", "lyra_phase4_lod1_draw_three_quarter.png", -58.0),
    }
    # Evaluate both density tiers for every test pose, even where a render is not emitted.
    report = {
        "phase": 4,
        "method": "CPU linear-blend skinning of actual GLB JOINTS_0/WEIGHTS_0 against the explicit rest hierarchy; poses are QA-only, not exported animation clips.",
        "lod0": {
            "asset": LOD0.name,
            "weight_audit": audit_weights(LOD0),
            "helper_socket_audit": helper_socket_audit(LOD0),
            "poses": {
                "bind": rendered["bind"],
                "draw": rendered["draw"],
                "crouch": rendered["crouch"],
            },
        },
        "lod1": {
            "asset": LOD1.name,
            "weight_audit": audit_weights(LOD1),
            "helper_socket_audit": helper_socket_audit(LOD1),
            "poses": {
                "draw": rendered["lod1_draw"],
                # Evaluate non-rendered bounds/displacement deterministically as well.
                "bind": render_pose(LOD1, "bind", "lyra_phase4_lod1_bind_reference.png", -58.0),
                "crouch": render_pose(LOD1, "crouch", "lyra_phase4_lod1_crouch_reference.png", -58.0),
            },
        },
        "render_files": [
            "renders/lyra_phase4_bind_three_quarter.png",
            "renders/lyra_phase4_draw_three_quarter.png",
            "renders/lyra_phase4_crouch_three_quarter.png",
            "renders/lyra_phase4_lod1_draw_three_quarter.png",
            "renders/lyra_phase4_lod1_bind_reference.png",
            "renders/lyra_phase4_lod1_crouch_reference.png",
        ],
    }
    assert_pose_quality(report)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Phase 4 deformation validation passed")
    for label in ("lod0", "lod1"):
        for pose_name, pose in report[label]["poses"].items():
            print(f"  {label}/{pose_name}: {pose['vertices_moved_over_1mm']} vertices moved, max {pose['max_displacement_m']:.3f} m")


if __name__ == "__main__":
    main()
