#!/usr/bin/env python3
"""Validate and render actual Phase 5 glTF animation curves on Lyra's Phase 4 skin.

This software QA tool decodes the exported glTF animation samplers/channels, samples
LINEAR quaternion tracks at actual key/event times, evaluates exported inverse-bind
matrices plus JOINTS_0/WEIGHTS_0 with CPU linear-blend skinning, and produces review
renders. It does not claim real Godot import/runtime validation; that is Phase 6 work.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image
from pygltflib import GLTF2

ROOT = Path(__file__).resolve().parents[2]
PHASE4_SOURCE = ROOT / "character_rigged" / "source"
PHASE5_SOURCE = ROOT / "character_animated" / "source"
for source_path in (PHASE4_SOURCE, PHASE5_SOURCE):
    if str(source_path) not in sys.path:
        sys.path.insert(0, str(source_path))

from build_lyra_phase4 import read_accessor  # noqa: E402
from build_lyra_phase5 import CANONICAL_CLIPS, CLIP_SPECS, event_payload  # noqa: E402

OUTPUT = ROOT / "character_animated"
LOD0 = OUTPUT / "lyra_vesper_animated.glb"
LOD1 = OUTPUT / "lyra_vesper_animated_lod1.glb"
RENDERS = OUTPUT / "renders"
VALIDATION = OUTPUT / "validation"
REPORT = VALIDATION / "animation_report.json"
EPSILON = 1e-8
HELPER_PARENTS = {
    "socket_weapon": "hand_r",
    "socket_projectile": "socket_weapon",
    "socket_camera_body": "pelvis",
    "socket_camera_chest": "chest",
    "socket_camera_head": "head",
    "socket_aim": "chest",
}
RENDER_SAMPLES = (
    ("idle", 0.25, "lyra_phase5_idle_mid.png", "LOD0 idle — breathing midpoint"),
    ("run", 0.00, "lyra_phase5_run_stride.png", "LOD0 run — stride"),
    ("basic_attack", 0.70, "lyra_phase5_basic_attack_release.png", "LOD0 basic attack — release"),
    ("skill_01", 0.61, "lyra_phase5_prism_volley.png", "LOD0 skill 01 — Prism Volley"),
    ("skill_02", 0.36, "lyra_phase5_phase_step.png", "LOD0 skill 02 — Phase Step"),
    ("skill_03", 0.70, "lyra_phase5_tether_release.png", "LOD0 skill 03 — Tether Snare release"),
    ("ultimate", 0.68, "lyra_phase5_ultimate_release.png", "LOD0 ultimate — constellation release"),
    ("death", 1.00, "lyra_phase5_death_end.png", "LOD0 death — held end pose"),
)
LOD1_RENDER_SAMPLES = (
    ("run", 0.00, "lyra_phase5_lod1_run_stride.png", "LOD1 run — stride"),
    ("basic_attack", 0.70, "lyra_phase5_lod1_basic_attack_release.png", "LOD1 basic attack — release"),
)


@dataclass(frozen=True)
class PrimitiveData:
    positions: np.ndarray
    uvs: np.ndarray
    joints: np.ndarray
    weights: np.ndarray
    faces: np.ndarray
    material_index: int


@dataclass(frozen=True)
class AssetContext:
    path: Path
    gltf: GLTF2
    binary: bytearray
    primitives: tuple[PrimitiveData, ...]
    names: dict[str, int]
    parents: dict[int, int | None]
    rest_matrices: tuple[np.ndarray, ...]
    inverse_bind: np.ndarray
    inverse_bind_max_abs_error: float


def node_parents(gltf: GLTF2) -> dict[int, int | None]:
    parents: dict[int, int | None] = {index: None for index in range(len(gltf.nodes))}
    for parent_index, node in enumerate(gltf.nodes):
        for child_index in node.children or []:
            if parents[child_index] is not None:
                raise RuntimeError(f"Node {child_index} has multiple parents.")
            parents[child_index] = parent_index
    return parents


def translation_matrix(values: list[float] | None) -> np.ndarray:
    matrix = np.identity(4, dtype=np.float64)
    if values:
        matrix[:3, 3] = values
    return matrix


def quaternion_matrix(quaternion: np.ndarray) -> np.ndarray:
    x, y, z, w = np.asarray(quaternion, dtype=np.float64)
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length < EPSILON:
        raise RuntimeError("Animation supplied a zero-length quaternion.")
    x, y, z, w = x / length, y / length, z / length, w / length
    matrix = np.identity(4, dtype=np.float64)
    matrix[:3, :3] = np.array(
        (
            (1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)),
            (2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)),
            (2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)),
        )
    )
    return matrix


def node_local_matrix(node, node_index: int, rotations: dict[int, np.ndarray]) -> np.ndarray:
    if node.matrix:
        if node_index in rotations:
            raise RuntimeError("Phase 5 cannot layer a rotation channel over a matrix-authored node.")
        return np.asarray(node.matrix, dtype=float).reshape((4, 4), order="F")
    matrix = translation_matrix(node.translation)
    rotation = rotations.get(node_index)
    if rotation is not None:
        matrix = matrix @ quaternion_matrix(rotation)
    return matrix


def global_matrices(gltf: GLTF2, parents: dict[int, int | None], rotations: dict[int, np.ndarray]) -> tuple[np.ndarray, ...]:
    cache: list[np.ndarray | None] = [None] * len(gltf.nodes)

    def resolve(index: int) -> np.ndarray:
        if cache[index] is not None:
            return cache[index]
        node = gltf.nodes[index]
        local = node_local_matrix(node, index, rotations)
        parent = parents[index]
        cache[index] = local if parent is None else resolve(parent) @ local
        return cache[index]

    return tuple(resolve(index) for index in range(len(gltf.nodes)))


def decode_weights(gltf: GLTF2, binary: bytearray, accessor_index: int) -> np.ndarray:
    accessor = gltf.accessors[accessor_index]
    weights = read_accessor(gltf, binary, accessor_index).astype(np.float64)
    if accessor.normalized:
        maximum = {5121: 255.0, 5123: 65535.0, 5125: 4294967295.0}[accessor.componentType]
        weights /= maximum
    return weights


def load_context(path: Path) -> AssetContext:
    gltf = GLTF2().load_binary(path)
    binary = bytearray(gltf.binary_blob())
    if not gltf.skins or len(gltf.skins) != 1:
        raise RuntimeError(f"{path.name}: expected exactly one Phase 4 skin.")
    if tuple(animation.name for animation in gltf.animations or []) != CANONICAL_CLIPS:
        raise RuntimeError(f"{path.name}: missing canonical Phase 5 animations.")
    names = {node.name: index for index, node in enumerate(gltf.nodes) if node.name}
    missing_helpers = set(HELPER_PARENTS).difference(names)
    if missing_helpers:
        raise RuntimeError(f"{path.name}: missing helper nodes {sorted(missing_helpers)}")
    parents = node_parents(gltf)
    rest_matrices = global_matrices(gltf, parents, {})
    skin = gltf.skins[0]
    raw_inverse_bind = read_accessor(gltf, binary, skin.inverseBindMatrices).astype(np.float64)
    inverse_bind = raw_inverse_bind.reshape((-1, 4, 4)).transpose((0, 2, 1))
    expected_inverse_bind = np.asarray([np.linalg.inv(rest_matrices[node]) for node in skin.joints])
    inverse_bind_error = float(np.max(np.abs(inverse_bind - expected_inverse_bind)))
    if inverse_bind_error > 2e-6:
        raise RuntimeError(f"{path.name}: exported inverse bind data mismatches rest hierarchy.")
    primitives: list[PrimitiveData] = []
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            attributes = primitive.attributes
            primitives.append(
                PrimitiveData(
                    positions=read_accessor(gltf, binary, attributes.POSITION).astype(np.float64),
                    uvs=read_accessor(gltf, binary, attributes.TEXCOORD_0).astype(np.float64),
                    joints=read_accessor(gltf, binary, attributes.JOINTS_0).astype(np.int64),
                    weights=decode_weights(gltf, binary, attributes.WEIGHTS_0),
                    faces=read_accessor(gltf, binary, primitive.indices).reshape((-1, 3)).astype(np.int64),
                    material_index=primitive.material,
                )
            )
    return AssetContext(
        path=path,
        gltf=gltf,
        binary=binary,
        primitives=tuple(primitives),
        names=names,
        parents=parents,
        rest_matrices=rest_matrices,
        inverse_bind=inverse_bind,
        inverse_bind_max_abs_error=inverse_bind_error,
    )


def slerp(first: np.ndarray, second: np.ndarray, fraction: float) -> np.ndarray:
    """Sample a glTF LINEAR quaternion curve with shortest-path spherical interpolation."""

    start = np.asarray(first, dtype=np.float64)
    end = np.asarray(second, dtype=np.float64)
    dot = float(np.dot(start, end))
    if dot < 0.0:
        end = -end
        dot = -dot
    dot = float(np.clip(dot, -1.0, 1.0))
    if dot > 0.9995:
        result = start + fraction * (end - start)
    else:
        angle = math.acos(dot)
        sine = math.sin(angle)
        result = math.sin((1.0 - fraction) * angle) / sine * start + math.sin(fraction * angle) / sine * end
    return result / np.linalg.norm(result)


def animation_by_name(context: AssetContext, clip_name: str):
    for animation in context.gltf.animations:
        if animation.name == clip_name:
            return animation
    raise RuntimeError(f"{context.path.name}: missing animation {clip_name}")


def sample_rotations(context: AssetContext, clip_name: str, seconds: float) -> dict[int, np.ndarray]:
    animation = animation_by_name(context, clip_name)
    rotations: dict[int, np.ndarray] = {}
    for channel in animation.channels:
        if channel.target.path != "rotation" or channel.target.node is None:
            raise RuntimeError(f"{clip_name}: expected rotation-only channels.")
        sampler = animation.samplers[channel.sampler]
        if sampler.interpolation != "LINEAR":
            raise RuntimeError(f"{clip_name}: expected LINEAR interpolation.")
        times = read_accessor(context.gltf, context.binary, sampler.input).reshape(-1).astype(np.float64)
        values = read_accessor(context.gltf, context.binary, sampler.output).astype(np.float64)
        if seconds <= times[0]:
            rotations[channel.target.node] = values[0]
        elif seconds >= times[-1]:
            rotations[channel.target.node] = values[-1]
        else:
            next_index = int(np.searchsorted(times, seconds, side="right"))
            previous_index = next_index - 1
            fraction = float((seconds - times[previous_index]) / (times[next_index] - times[previous_index]))
            rotations[channel.target.node] = slerp(values[previous_index], values[next_index], fraction)
    return rotations


def skin_matrices(context: AssetContext, rotations: dict[int, np.ndarray]) -> tuple[np.ndarray, tuple[np.ndarray, ...]]:
    posed = global_matrices(context.gltf, context.parents, rotations)
    skin = context.gltf.skins[0]
    matrices = np.asarray(
        [posed[node_index] @ context.inverse_bind[index] for index, node_index in enumerate(skin.joints)]
    )
    return matrices, posed


def deform_primitive(primitive: PrimitiveData, matrices: np.ndarray) -> np.ndarray:
    if not np.allclose(primitive.weights.sum(axis=1), 1.0, atol=1.0 / 255.0 + 1e-8):
        raise RuntimeError("A Phase 5 primitive has invalid inherited normalized weights.")
    if int(primitive.joints.max()) >= len(matrices):
        raise RuntimeError("A Phase 5 primitive references a joint outside its skin palette.")
    homogeneous = np.concatenate((primitive.positions, np.ones((len(primitive.positions), 1))), axis=1)
    deformed = np.zeros((len(primitive.positions), 4), dtype=np.float64)
    for influence in range(4):
        transformed = np.einsum("nij,nj->ni", matrices[primitive.joints[:, influence]], homogeneous)
        deformed += transformed * primitive.weights[:, influence, None]
    deformed[:, :3] /= np.maximum(deformed[:, 3:4], EPSILON)
    return deformed[:, :3]


def evaluate_sample(context: AssetContext, clip_name: str, seconds: float) -> tuple[list[np.ndarray], tuple[np.ndarray, ...], dict[str, object]]:
    rotations = sample_rotations(context, clip_name, seconds)
    matrices, posed = skin_matrices(context, rotations)
    deformed_primitives = [deform_primitive(primitive, matrices) for primitive in context.primitives]
    rest = np.concatenate([primitive.positions for primitive in context.primitives], axis=0)
    deformed = np.concatenate(deformed_primitives, axis=0)
    displacement = np.linalg.norm(deformed - rest, axis=1)
    return deformed_primitives, posed, {
        "time_s": round(seconds, 6),
        "vertices": int(len(rest)),
        "vertices_moved_over_1mm": int(np.count_nonzero(displacement > 0.001)),
        "mean_displacement_m": round(float(displacement.mean()), 6),
        "max_displacement_m": round(float(displacement.max()), 6),
    }


def clip_duration(context: AssetContext, clip_name: str) -> float:
    animation = animation_by_name(context, clip_name)
    sampler = animation.samplers[0]
    values = read_accessor(context.gltf, context.binary, sampler.input).reshape(-1)
    return float(values[-1])


def clip_events(context: AssetContext, clip_name: str) -> list[dict[str, object]]:
    animation = animation_by_name(context, clip_name)
    extras = animation.extras or {}
    events = extras.get("semantic_events", [])
    if not isinstance(events, list):
        raise RuntimeError(f"{clip_name}: semantic_events extras are malformed.")
    return events


def helper_positions(context: AssetContext, posed: tuple[np.ndarray, ...]) -> dict[str, list[float]]:
    return {
        helper_name: [round(float(value), 6) for value in posed[context.names[helper_name]][:3, 3]]
        for helper_name in HELPER_PARENTS
    }


def clip_audit(context: AssetContext, clip_name: str) -> dict[str, object]:
    duration = clip_duration(context, clip_name)
    animation = animation_by_name(context, clip_name)
    spec = next(spec for spec in CLIP_SPECS if spec.name == clip_name)
    events = clip_events(context, clip_name)
    if events != event_payload(spec):
        raise RuntimeError(f"{context.path.name}/{clip_name}: event extras differ from Phase 5 source contract.")
    sample_times = sorted(
        {
            *(round(spec.duration_s * normalized_time, 6) for normalized_time, _ in spec.frames),
            *(round(float(event["time_s"]), 6) for event in events),
        }
    )
    samples = []
    max_moved = 0
    max_mean = 0.0
    max_displacement = 0.0
    for sample_time in sample_times:
        _, _, result = evaluate_sample(context, clip_name, sample_time)
        samples.append(result)
        max_moved = max(max_moved, result["vertices_moved_over_1mm"])
        max_mean = max(max_mean, result["mean_displacement_m"])
        max_displacement = max(max_displacement, result["max_displacement_m"])
    direct_nodes = sorted(
        context.gltf.nodes[channel.target.node].name for channel in animation.channels
    )
    return {
        "duration_s": round(duration, 6),
        "loop": bool((animation.extras or {}).get("loop")),
        "channels": len(animation.channels),
        "samplers": len(animation.samplers),
        "direct_rotation_nodes": direct_nodes,
        "semantic_events": events,
        "sample_times_s": sample_times,
        "max_vertices_moved_over_1mm": max_moved,
        "max_mean_displacement_m": round(max_mean, 6),
        "max_displacement_m": round(max_displacement, 6),
        "samples": samples,
    }


def helper_motion_audit(context: AssetContext) -> dict[str, object]:
    """Verify inherited socket motion in actual basic-attack/dash curves."""

    for helper_name, expected_parent in HELPER_PARENTS.items():
        parent_index = context.parents[context.names[helper_name]]
        actual_parent = context.gltf.nodes[parent_index].name if parent_index is not None else None
        if actual_parent != expected_parent:
            raise RuntimeError(f"{context.path.name}: {helper_name} parent is {actual_parent}, expected {expected_parent}")
    rest = global_matrices(context.gltf, context.parents, {})
    checks = (
        ("basic_attack", 0.70, "socket_weapon"),
        ("basic_attack", 0.70, "socket_projectile"),
        ("skill_02", 0.36, "socket_camera_body"),
        ("ultimate", 0.68, "socket_aim"),
    )
    values: dict[str, object] = {}
    for clip_name, normalized_time, helper_name in checks:
        duration = clip_duration(context, clip_name)
        time = duration * normalized_time
        _, posed, _ = evaluate_sample(context, clip_name, time)
        displacement = float(
            np.linalg.norm(posed[context.names[helper_name]][:3, 3] - rest[context.names[helper_name]][:3, 3])
        )
        if displacement <= 0.001:
            raise RuntimeError(f"{context.path.name}/{clip_name}: {helper_name} did not inherit meaningful motion.")
        values[f"{clip_name}:{helper_name}"] = {
            "time_s": round(time, 6),
            "displacement_m": round(displacement, 6),
            "position": helper_positions(context, posed)[helper_name],
        }
    return values


def event_socket_audit(context: AssetContext) -> dict[str, object]:
    """Sample exported helpers at every semantic-event time and verify parent continuity.

    The stored values are presentation handoff data: they establish that the exported
    socket hierarchy follows the actual curves. They are deliberately not collision,
    projectile, or Godot-event dispatch logic.
    """

    rest = global_matrices(context.gltf, context.parents, {})
    hand_r = context.names["hand_r"]
    weapon = context.names["socket_weapon"]
    projectile = context.names["socket_projectile"]
    hand_to_weapon = np.linalg.inv(rest[hand_r]) @ rest[weapon]
    weapon_to_projectile = np.linalg.inv(rest[weapon]) @ rest[projectile]
    root_position = rest[context.names["root"]][:3, 3]
    values: dict[str, object] = {}
    max_hand_error = 0.0
    max_projectile_error = 0.0
    max_root_position_error = 0.0
    for clip_name in CANONICAL_CLIPS:
        for event in clip_events(context, clip_name):
            time = float(event["time_s"])
            rotations = sample_rotations(context, clip_name, time)
            _, posed = skin_matrices(context, rotations)
            hand_error = float(np.max(np.abs(posed[hand_r] @ hand_to_weapon - posed[weapon])))
            projectile_error = float(np.max(np.abs(posed[weapon] @ weapon_to_projectile - posed[projectile])))
            root_error = float(np.linalg.norm(posed[context.names["root"]][:3, 3] - root_position))
            max_hand_error = max(max_hand_error, hand_error)
            max_projectile_error = max(max_projectile_error, projectile_error)
            max_root_position_error = max(max_root_position_error, root_error)
            values[f"{clip_name}:{event['name']}"] = {
                "time_s": round(time, 6),
                "socket_positions": helper_positions(context, posed),
                "hand_to_weapon_max_abs_error": round(hand_error, 9),
                "weapon_to_projectile_max_abs_error": round(projectile_error, 9),
                "root_position_error_m": round(root_error, 9),
            }
    if max_hand_error > 2e-6 or max_projectile_error > 2e-6 or max_root_position_error > 2e-6:
        raise RuntimeError(f"{context.path.name}: socket continuity or in-place root check failed at an event time.")
    return {
        "event_sample_count": len(values),
        "max_hand_to_weapon_abs_error": round(max_hand_error, 9),
        "max_weapon_to_projectile_abs_error": round(max_projectile_error, 9),
        "max_root_position_error_m": round(max_root_position_error, 9),
        "samples": values,
    }


def image_for_material(context: AssetContext, material_index: int) -> Image.Image:
    material = context.gltf.materials[material_index]
    texture_index = material.pbrMetallicRoughness.baseColorTexture.index
    texture = context.gltf.textures[texture_index]
    image = context.gltf.images[texture.source]
    view = context.gltf.bufferViews[image.bufferView]
    start = int(view.byteOffset or 0)
    encoded = bytes(context.binary[start : start + view.byteLength])
    return Image.open(BytesIO(encoded)).convert("RGB")


def face_colors(texture: Image.Image, uvs: np.ndarray, faces: np.ndarray, material_name: str, normals: np.ndarray) -> np.ndarray:
    pixels = np.asarray(texture, dtype=np.float32) / 255.0
    height, width = pixels.shape[:2]
    centers = uvs[faces].mean(axis=1)
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


def draw_skeleton(axis, context: AssetContext, posed: tuple[np.ndarray, ...]) -> None:
    skin_nodes = set(context.gltf.skins[0].joints)
    for child_index in skin_nodes:
        parent_index = context.parents[child_index]
        if parent_index not in skin_nodes:
            continue
        start = posed[parent_index][:3, 3]
        end = posed[child_index][:3, 3]
        axis.plot(
            (start[0], end[0]), (start[1], end[1]), (start[2], end[2]),
            color="#84efff", linewidth=0.45, alpha=0.40, zorder=10,
        )


def render_sample(context: AssetContext, clip_name: str, normalized_time: float, filename: str, title: str) -> dict[str, object]:
    duration = clip_duration(context, clip_name)
    seconds = duration * normalized_time
    deformed, posed, result = evaluate_sample(context, clip_name, seconds)
    figure = plt.figure(figsize=(7.5, 8.5), dpi=170, facecolor="#e8ebf2")
    axis = figure.add_subplot(111, projection="3d")
    axis.set_facecolor("#e8ebf2")
    primitive_data = []
    for primitive, positions in zip(context.primitives, deformed):
        normals = np.cross(
            positions[primitive.faces[:, 1]] - positions[primitive.faces[:, 0]],
            positions[primitive.faces[:, 2]] - positions[primitive.faces[:, 0]],
        )
        normals /= np.maximum(np.linalg.norm(normals, axis=1), EPSILON)[:, None]
        material_name = context.gltf.materials[primitive.material_index].name
        primitive_data.append(
            (
                positions,
                primitive.faces,
                face_colors(image_for_material(context, primitive.material_index), primitive.uvs, primitive.faces, material_name, normals),
                material_name,
            )
        )
    for positions, faces, colors, material_name in sorted(
        primitive_data, key=lambda entry: entry[3] == "M_Lyra_AuroraMantle"
    ):
        axis.add_collection3d(Poly3DCollection(positions[faces], facecolors=colors, edgecolors="none", linewidths=0.0))
    draw_skeleton(axis, context, posed)
    grid_x, grid_y = np.meshgrid(np.linspace(-2.4, 2.4, 2), np.linspace(-2.0, 2.0, 2))
    axis.plot_surface(grid_x, grid_y, np.zeros_like(grid_x) - 0.015, color="#c9ceda", alpha=0.28, shade=False)
    axis.set_proj_type("ortho")
    axis.view_init(elev=8.5, azim=-58.0)
    axis.set_xlim(-2.6, 2.6)
    axis.set_ylim(-2.3, 2.3)
    axis.set_zlim(-2.0, 4.05)
    axis.set_box_aspect((5.2, 4.6, 6.05))
    axis.set_axis_off()
    axis.text2D(0.03, 0.95, title, transform=axis.transAxes, color="#26324d", fontsize=8.5, fontweight="bold")
    figure.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
    RENDERS.mkdir(parents=True, exist_ok=True)
    figure.savefig(RENDERS / filename, facecolor=figure.get_facecolor(), transparent=False)
    plt.close(figure)
    result["clip"] = clip_name
    result["normalized_time"] = normalized_time
    result["file"] = f"renders/{filename}"
    return result


def assert_quality(report: dict[str, object]) -> None:
    for label in ("lod0", "lod1"):
        asset = report[label]
        if asset["inverse_bind_max_abs_error"] > 0.000002:
            raise RuntimeError(f"{label}: inverse-bind validation did not meet tolerance.")
        if asset["translation_channels"] != 0 or asset["root_translation_channels"] != 0:
            raise RuntimeError(f"{label}: in-place root-motion policy was violated.")
        if asset["event_socket_audit"]["event_sample_count"] < 20:
            raise RuntimeError(f"{label}: event-time socket sampling is incomplete.")
        if set(asset["clips"]) != set(CANONICAL_CLIPS):
            raise RuntimeError(f"{label}: canonical clip coverage is incomplete.")
        for clip_name, clip in asset["clips"].items():
            if clip["channels"] < 2 or clip["samplers"] != clip["channels"]:
                raise RuntimeError(f"{label}/{clip_name}: insufficient actual animation tracks.")
            if clip["max_vertices_moved_over_1mm"] < 100:
                raise RuntimeError(f"{label}/{clip_name}: clip has no meaningful skinned deformation.")
            if not np.isfinite(clip["max_displacement_m"]) or clip["max_displacement_m"] > 4.5:
                raise RuntimeError(f"{label}/{clip_name}: invalid deformation magnitude.")
    for required_key in (
        "basic_attack:socket_weapon",
        "basic_attack:socket_projectile",
        "skill_02:socket_camera_body",
        "ultimate:socket_aim",
    ):
        if report["lod0"]["helper_motion"][required_key]["displacement_m"] <= 0.001:
            raise RuntimeError(f"lod0: helper-motion evidence missing {required_key}.")


def evaluate_asset(context: AssetContext) -> dict[str, object]:
    clips = {clip_name: clip_audit(context, clip_name) for clip_name in CANONICAL_CLIPS}
    root_index = context.names["root"]
    translation_channels = sum(
        channel.target.path == "translation"
        for animation in context.gltf.animations
        for channel in animation.channels
    )
    root_translation_channels = sum(
        channel.target.path == "translation" and channel.target.node == root_index
        for animation in context.gltf.animations
        for channel in animation.channels
    )
    return {
        "asset": context.path.name,
        "sha256": hashlib.sha256(context.path.read_bytes()).hexdigest(),
        "inverse_bind_max_abs_error": round(context.inverse_bind_max_abs_error, 9),
        "animation_count": len(context.gltf.animations),
        "translation_channels": translation_channels,
        "root_translation_channels": root_translation_channels,
        "clips": clips,
        "helper_motion": helper_motion_audit(context),
        "event_socket_audit": event_socket_audit(context),
    }


def main() -> None:
    if not LOD0.is_file() or not LOD1.is_file():
        raise RuntimeError("Build Phase 5 animated GLBs before running validation.")
    lod0 = load_context(LOD0)
    lod1 = load_context(LOD1)
    report = {
        "phase": 5,
        "method": "CPU samples actual standard glTF LINEAR quaternion animation channels and semantic-event times, then evaluates exported inverse-bind matrices plus JOINTS_0/WEIGHTS_0 with linear-blend skinning. Renders are offline review evidence, not a Godot runtime claim.",
        "lod0": evaluate_asset(lod0),
        "lod1": evaluate_asset(lod1),
        "render_samples": [],
    }
    for clip_name, normalized_time, filename, title in RENDER_SAMPLES:
        report["render_samples"].append(render_sample(lod0, clip_name, normalized_time, filename, title))
    for clip_name, normalized_time, filename, title in LOD1_RENDER_SAMPLES:
        report["render_samples"].append(render_sample(lod1, clip_name, normalized_time, filename, title))
    assert_quality(report)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Phase 5 animation validation passed")
    for label in ("lod0", "lod1"):
        clips = report[label]["clips"]
        print(f"  {label}: {len(clips)} clips, max sampled deformation {max(item['max_displacement_m'] for item in clips.values()):.3f} m")


if __name__ == "__main__":
    main()
