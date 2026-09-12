"""Static contract checks for the self-contained Godot hero foundation.

These tests intentionally avoid requiring a Godot executable. The engine-facing Phase 6
smoke suite lives in ``tests/godot/`` and is run with a real Godot 4.3 editor/headless
binary; these checks protect its checked-in composition and asset contracts.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "heroes" / "hero_agile_hunter"
PHASE5 = ROOT / "character_animated"
PHASE5_CANONICAL_CLIPS = (
    "idle",
    "idle_variation",
    "walk",
    "run",
    "turn_left",
    "turn_right",
    "start_run",
    "stop_run",
    "basic_attack",
    "basic_attack_recovery",
    "attack_variant",
    "charged_attack",
    "hit_light",
    "hit_heavy",
    "knockback",
    "stun",
    "death",
    "victory",
    "spawn",
    "skill_01",
    "skill_02",
    "skill_03",
    "ultimate",
)
# Duration, direct track count, normalized baked key times, intended loop policy, and
# gameplay/presentation event name + seconds. Keep this independently explicit so the
# project contract does not merely trust the generated manifest it is checking.
PHASE5_CLIP_CONTRACT = {
    "idle": (2.00, 10, (0.00, 0.25, 0.50, 0.75, 1.00), True, ()),
    "idle_variation": (3.20, 14, (0.00, 0.25, 0.55, 0.78, 1.00), True, ()),
    "walk": (1.00, 21, (0.00, 0.25, 0.50, 0.75, 1.00), True, (("footstep_left", 0.0800), ("footstep_right", 0.5800))),
    "run": (0.72, 21, (0.00, 0.25, 0.50, 0.75, 1.00), True, (("footstep_left", 0.0432), ("footstep_right", 0.4032))),
    "turn_left": (0.42, 12, (0.00, 0.45, 0.78, 1.00), False, ()),
    "turn_right": (0.42, 12, (0.00, 0.45, 0.78, 1.00), False, ()),
    "start_run": (0.36, 22, (0.00, 0.35, 0.72, 1.00), False, (("locomotion_commit", 0.1872),)),
    "stop_run": (0.42, 23, (0.00, 0.32, 0.66, 1.00), False, (("locomotion_stop", 0.2604),)),
    "basic_attack": (0.76, 38, (0.00, 0.20, 0.52, 0.70, 0.86, 1.00), False, (("weapon_draw", 0.3192), ("projectile_release", 0.5320), ("recovery_open", 0.6840))),
    "basic_attack_recovery": (0.34, 35, (0.00, 0.46, 1.00), False, (("recovery_open", 0.2788),)),
    "attack_variant": (0.80, 40, (0.00, 0.22, 0.51, 0.69, 0.87, 1.00), False, (("weapon_draw", 0.3200), ("projectile_release", 0.5520), ("recovery_open", 0.7280))),
    "charged_attack": (1.18, 38, (0.00, 0.18, 0.46, 0.70, 0.82, 0.94, 1.00), False, (("charge_start", 0.3422), ("charge_ready", 0.8024), ("projectile_release", 0.9676), ("recovery_open", 1.1210))),
    "hit_light": (0.34, 10, (0.00, 0.25, 0.58, 1.00), False, (("hit_react", 0.0850),)),
    "hit_heavy": (0.52, 14, (0.00, 0.22, 0.56, 1.00), False, (("hit_react", 0.1144), ("recovery_open", 0.4576))),
    "knockback": (0.62, 16, (0.00, 0.22, 0.58, 1.00), False, (("knockback_peak", 0.1860), ("recovery_open", 0.5580))),
    "stun": (1.00, 9, (0.00, 0.25, 0.50, 0.75, 1.00), True, (("stun_loop", 0.0000),)),
    "death": (1.18, 17, (0.00, 0.20, 0.62, 1.00), False, (("death_impact", 0.7316), ("death_complete", 1.1800))),
    "victory": (1.55, 24, (0.00, 0.28, 0.56, 0.78, 1.00), False, (("victory_pose", 0.8680),)),
    "spawn": (1.02, 18, (0.00, 0.30, 0.66, 1.00), False, (("spawn_ready", 0.8976),)),
    "skill_01": (0.92, 38, (0.00, 0.20, 0.44, 0.54, 0.64, 0.72, 0.86, 1.00), False, (("volley_release_1", 0.4600), ("volley_release_2", 0.5612), ("volley_release_3", 0.6624), ("recovery_open", 0.8280))),
    "skill_02": (0.48, 17, (0.00, 0.18, 0.36, 0.60, 0.82, 1.00), False, (("dash_start", 0.1344), ("dash_end", 0.3168), ("recovery_open", 0.4224))),
    "skill_03": (1.04, 38, (0.00, 0.20, 0.52, 0.70, 0.87, 1.00), False, (("tether_ready", 0.5200), ("projectile_release", 0.7280), ("recovery_open", 0.9464))),
    "ultimate": (1.82, 36, (0.00, 0.18, 0.46, 0.68, 0.82, 0.94, 1.00), False, (("ultimate_charge", 0.6552), ("ultimate_release", 1.2376), ("ultimate_impact_window", 1.4924), ("recovery_open", 1.7290))),
}
PHASE5_ACTION_CLIPS = ("basic_attack", "attack_variant", "charged_attack", "skill_01", "skill_03", "ultimate")
PHASE5_FINGER_TRACKS = {
    "thumb_01_l", "thumb_02_l", "index_01_l", "index_02_l", "middle_01_l", "middle_02_l", "ring_01_l", "ring_02_l", "pinky_01_l", "pinky_02_l",
    "thumb_01_r", "thumb_02_r", "index_01_r", "index_02_r", "middle_01_r", "middle_02_r", "ring_01_r", "ring_02_r", "pinky_01_r", "pinky_02_r",
}


def load_glb_json(path: Path) -> dict[str, object]:
    """Read the JSON chunk of a GLB using only the Python standard library."""

    payload = path.read_bytes()
    magic, version, total_length = struct.unpack("<4sII", payload[:12])
    if magic != b"glTF" or version != 2 or total_length != len(payload):
        raise ValueError(f"Invalid GLB header: {path}")
    json_length, chunk_type = struct.unpack("<I4s", payload[12:20])
    if chunk_type != b"JSON":
        raise ValueError(f"First GLB chunk is not JSON: {path}")
    return json.loads(payload[20 : 20 + json_length].decode("utf-8").rstrip(" \t\r\n\x00"))


def load_glb_binary_chunk(path: Path) -> bytes:
    """Return the BIN chunk from a binary glTF without adding a test dependency."""

    payload = path.read_bytes()
    magic, version, total_length = struct.unpack("<4sII", payload[:12])
    if magic != b"glTF" or version != 2 or total_length != len(payload):
        raise ValueError(f"Invalid GLB header: {path}")
    offset = 12
    while offset < len(payload):
        chunk_length, chunk_type = struct.unpack("<I4s", payload[offset : offset + 8])
        offset += 8
        chunk = payload[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == b"BIN\x00":
            return chunk
    raise ValueError(f"GLB has no BIN chunk: {path}")


def accessor_rows(document: dict[str, object], binary: bytes, accessor_index: int) -> list[tuple[int | float, ...]]:
    """Decode a non-sparse GLB accessor for contract assertions."""

    accessor = document["accessors"][accessor_index]
    if "sparse" in accessor:
        raise ValueError("Contract helper does not support sparse accessors.")
    view = document["bufferViews"][accessor["bufferView"]]
    format_characters = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
    component_counts = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    component_type = accessor["componentType"]
    component_count = component_counts[accessor["type"]]
    component_size = struct.calcsize("<" + format_characters[component_type])
    packed_size = component_size * component_count
    stride = view.get("byteStride", packed_size)
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    unpack_format = "<" + format_characters[component_type] * component_count
    return [
        struct.unpack_from(unpack_format, binary, start + row_index * stride)
        for row_index in range(accessor["count"])
    ]


def animation_curve_signature(document: dict[str, object], binary: bytes) -> tuple[object, ...]:
    """Make an exact comparable representation of core glTF animation payloads."""

    node_names = {index: node.get("name") for index, node in enumerate(document["nodes"])}
    signature = []
    for animation in document.get("animations", []):
        curves = []
        for channel in animation["channels"]:
            sampler = animation["samplers"][channel["sampler"]]
            curves.append(
                (
                    node_names[channel["target"]["node"]],
                    channel["target"]["path"],
                    sampler.get("interpolation", "LINEAR"),
                    tuple(accessor_rows(document, binary, sampler["input"])),
                    tuple(accessor_rows(document, binary, sampler["output"])),
                )
            )
        signature.append((animation["name"], animation.get("extras", {}), tuple(curves)))
    return tuple(signature)


class HeroProjectContractTests(unittest.TestCase):
    def test_phase_zero_production_docs_exist(self) -> None:
        expected_markers = {
            "PROJECT_PLAN.md": "Concept",
            "ASSET_PIPELINE.md": "GLB",
            "ARCHITECTURE.md": "CharacterController",
        }
        for filename, marker in expected_markers.items():
            with self.subTest(document=filename):
                document = ROOT / filename
                self.assertTrue(document.is_file())
                self.assertIn(marker, document.read_text(encoding="utf-8"))

    def test_phase_one_character_design_package_is_complete(self) -> None:
        design_document = ROOT / "character_design.md"
        self.assertTrue(design_document.is_file())
        design_text = design_document.read_text(encoding="utf-8")
        self.assertIn("Phase 1 result:** Pass", design_text)
        self.assertIn("Must not do", design_text)
        required_references = (
            "concept/lyra_master_concept.png",
            "references/lyra_turnaround_front.png",
            "references/lyra_turnaround_back.png",
            "references/lyra_turnaround_left.png",
            "references/lyra_turnaround_right.png",
            "references/lyra_three_quarter_front.png",
            "references/lyra_three_quarter_back.png",
            "references/lyra_face_sheet.png",
            "references/lyra_weapon_sheet.png",
            "references/lyra_costume_details.png",
        )
        for relative_path in required_references:
            with self.subTest(reference=relative_path):
                reference = ROOT / relative_path
                self.assertTrue(reference.is_file())
                self.assertGreater(reference.stat().st_size, 10_000)
                self.assertEqual(reference.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_phase_two_authored_glb_package_is_complete(self) -> None:
        asset_root = ROOT / "character_final"
        glb = asset_root / "lyra_vesper_phase2.glb"
        manifest_path = asset_root / "asset_manifest.json"
        self.assertTrue(glb.is_file())
        self.assertGreater(glb.stat().st_size, 500_000)
        self.assertTrue(manifest_path.is_file())
        self.assertTrue((asset_root / "source" / "build_lyra_phase2.py").is_file())
        self.assertTrue((asset_root / "source" / "makehuman_base_cc0.obj").is_file())
        self.assertTrue((asset_root / "source" / "MAKEHUMAN_CC0_NOTICE.md").is_file())

        document = load_glb_json(glb)
        self.assertEqual(document["asset"]["version"], "2.0")
        self.assertGreaterEqual(len(document["meshes"]), 50)
        self.assertGreaterEqual(len(document["materials"]), 10)
        self.assertGreaterEqual(len(document["images"]), 12)
        self.assertGreaterEqual(len(document["textures"]), 12)
        required_parts = {"MESH_Lyra_BaseSuit", "MESH_Lyra_HeadAndHands", "MESH_AuroraMantle_Left", "MESH_AsterArc_Compass", "MESH_CometTail_Base"}
        node_names = {node.get("name") for node in document["nodes"]}
        self.assertTrue(required_parts.issubset(node_names))
        forbidden = ("boxmesh", "spheremesh", "capsulemesh", "cylindermesh", "placeholder", "mannequin")
        self.assertFalse(any(word in str(name).lower() for name in node_names for word in forbidden))
        for mesh in document["meshes"]:
            for primitive in mesh["primitives"]:
                self.assertIn("TEXCOORD_0", primitive["attributes"])

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(manifest["triangles"], 25_000)
        self.assertGreaterEqual(manifest["mesh_count"], 50)
        self.assertIn("Godot runtime primitive assembly", manifest["prohibited_final_primitives"])
        for render_name in ("lyra_phase2_front.png", "lyra_phase2_three_quarter.png", "lyra_phase2_back.png"):
            render = asset_root / "renders" / render_name
            with self.subTest(render=render_name):
                self.assertTrue(render.is_file())
                self.assertGreater(render.stat().st_size, 10_000)
                self.assertEqual(render.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_phase_three_mobile_optimized_glbs_are_complete(self) -> None:
        """Require a real, measurable mobile package rather than a substitute primitive asset."""

        optimized_root = ROOT / "character_optimized"
        lod_root = ROOT / "character_lod"
        lod0 = optimized_root / "lyra_vesper_optimized.glb"
        lod1 = lod_root / "lyra_vesper_lod1.glb"
        phase2 = ROOT / "character_final" / "lyra_vesper_phase2.glb"
        for asset in (lod0, lod1):
            with self.subTest(asset=asset.name):
                self.assertTrue(asset.is_file())
                self.assertGreater(asset.stat().st_size, 100_000)
                self.assertEqual(asset.read_bytes()[:4], b"glTF")

        self.assertTrue((optimized_root / "source" / "build_lyra_phase3.py").is_file())
        self.assertTrue((optimized_root / "source" / "render_phase3_review.py").is_file())
        self.assertTrue((optimized_root / "source" / "requirements.txt").is_file())
        self.assertTrue((optimized_root / "optimization_manifest.json").is_file())
        self.assertTrue((lod_root / "lod_manifest.json").is_file())

        source_document = load_glb_json(phase2)
        source_triangles = sum(
            source_document["accessors"][primitive["indices"]]["count"] // 3
            for mesh in source_document["meshes"]
            for primitive in mesh["primitives"]
        )
        source_geometry_bytes = sum(
            view["byteLength"]
            for view in source_document["bufferViews"]
            if view.get("target") in (34962, 34963)
        )
        asset_metrics: dict[str, dict[str, int]] = {}
        expected_materials = {"M_Lyra_OpaqueAtlas", "M_Lyra_LumenEnergy", "M_Lyra_AuroraMantle"}
        for label, asset in (("lod0", lod0), ("lod1", lod1)):
            document = load_glb_json(asset)
            triangles = sum(
                document["accessors"][primitive["indices"]]["count"] // 3
                for mesh in document["meshes"]
                for primitive in mesh["primitives"]
            )
            vertices = sum(
                document["accessors"][primitive["attributes"]["POSITION"]]["count"]
                for mesh in document["meshes"]
                for primitive in mesh["primitives"]
            )
            geometry_bytes = sum(
                view["byteLength"]
                for view in document["bufferViews"]
                if view.get("target") in (34962, 34963)
            )
            with self.subTest(asset=label):
                self.assertEqual(document["asset"]["version"], "2.0")
                self.assertFalse(document.get("extensionsRequired"))
                self.assertEqual(len(document["meshes"]), 3)
                self.assertEqual(len(document["nodes"]), 3)
                self.assertEqual(len(document["materials"]), 3)
                self.assertEqual(len(document["textures"]), 8)
                self.assertEqual(len(document["images"]), 8)
                self.assertEqual({material["name"] for material in document["materials"]}, expected_materials)
                self.assertTrue(any("emissiveTexture" in material for material in document["materials"]))
                self.assertTrue(any(material.get("emissiveFactor") for material in document["materials"]))
                self.assertTrue(all("normalTexture" in material for material in document["materials"]))
                self.assertLess(triangles, source_triangles)
                self.assertLess(vertices, 10_000)
                for mesh in document["meshes"]:
                    for primitive in mesh["primitives"]:
                        self.assertIn("TEXCOORD_0", primitive["attributes"])
                        self.assertIn("NORMAL", primitive["attributes"])
                        self.assertIn("TANGENT", primitive["attributes"])
                        self.assertIn("material", primitive)
            asset_metrics[label] = {
                "triangles": triangles,
                "vertices": vertices,
                "geometry_bytes": geometry_bytes,
            }

        self.assertGreaterEqual(asset_metrics["lod0"]["triangles"], 7_000)
        self.assertLessEqual(asset_metrics["lod0"]["triangles"], 12_500)
        self.assertGreaterEqual(asset_metrics["lod1"]["triangles"], 3_500)
        self.assertLess(asset_metrics["lod1"]["triangles"], asset_metrics["lod0"]["triangles"])
        self.assertLess(asset_metrics["lod1"]["vertices"], asset_metrics["lod0"]["vertices"])
        self.assertLess(asset_metrics["lod0"]["geometry_bytes"], source_geometry_bytes)
        self.assertLess(asset_metrics["lod1"]["geometry_bytes"], asset_metrics["lod0"]["geometry_bytes"])

        manifest = json.loads((optimized_root / "optimization_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["phase"], 3)
        self.assertEqual(manifest["source"]["triangles"], source_triangles)
        self.assertEqual(manifest["optimized_lod0"]["triangles"], asset_metrics["lod0"]["triangles"])
        self.assertEqual(manifest["lod1"]["triangles"], asset_metrics["lod1"]["triangles"])
        self.assertEqual(manifest["source"]["geometry_bytes"], source_geometry_bytes)
        self.assertEqual(manifest["optimized_lod0"]["geometry_bytes"], asset_metrics["lod0"]["geometry_bytes"])
        self.assertEqual(manifest["lod1"]["geometry_bytes"], asset_metrics["lod1"]["geometry_bytes"])
        self.assertGreaterEqual(manifest["lod0_triangle_reduction_percent"], 60.0)
        self.assertGreaterEqual(manifest["lod0_geometry_upload_reduction_percent"], 30.0)
        self.assertEqual(manifest["optimized_lod0"]["draw_groups"], 3)
        self.assertEqual(manifest["texture_residency_rgba8_estimate_mib"]["lod0_or_lod1"], 17.0)

        expected_textures = (
            "lyra_mobile_opaque_basecolor.png",
            "lyra_mobile_opaque_orm.png",
            "lyra_mobile_opaque_normal.png",
            "lyra_mobile_opaque_emission.png",
            "lyra_mobile_energy_basecolor.png",
            "lyra_mobile_energy_normal.png",
            "lyra_mobile_mantle_basecolor.png",
            "lyra_mobile_mantle_normal.png",
        )
        for filename in expected_textures:
            texture = optimized_root / "textures" / filename
            with self.subTest(texture=filename):
                self.assertTrue(texture.is_file())
                self.assertEqual(texture.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        # The opaque material atlas deliberately gets the larger 1024² allocation.
        opaque_png = (optimized_root / "textures" / "lyra_mobile_opaque_basecolor.png").read_bytes()
        self.assertEqual(struct.unpack(">II", opaque_png[16:24]), (1024, 1024))
        opaque_normal = (optimized_root / "textures" / "lyra_mobile_opaque_normal.png").read_bytes()
        self.assertEqual(struct.unpack(">II", opaque_normal[16:24]), (512, 512))

        for render_name in (
            "lyra_phase3_lod0_front.png",
            "lyra_phase3_lod0_three_quarter.png",
            "lyra_phase3_lod0_back.png",
            "lyra_phase3_lod1_three_quarter.png",
        ):
            render = optimized_root / "renders" / render_name
            with self.subTest(render=render_name):
                self.assertTrue(render.is_file())
                self.assertGreater(render.stat().st_size, 10_000)
                self.assertEqual(render.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_phase_four_rigged_glbs_are_complete(self) -> None:
        """Require real skinned Phase 3 derivatives, not static mesh or metadata stand-ins."""

        rigged_root = ROOT / "character_rigged"
        source_lod0 = ROOT / "character_optimized" / "lyra_vesper_optimized.glb"
        source_lod1 = ROOT / "character_lod" / "lyra_vesper_lod1.glb"
        assets = {
            "lod0": (rigged_root / "lyra_vesper_rigged.glb", source_lod0),
            "lod1": (rigged_root / "lyra_vesper_rigged_lod1.glb", source_lod1),
        }
        manifest_path = rigged_root / "rig_manifest.json"
        report_path = rigged_root / "validation" / "deformation_report.json"
        for path in (
            rigged_root / "README.md",
            rigged_root / "RIG_SPECIFICATION.md",
            rigged_root / "PHASE_4_QA.md",
            rigged_root / "source" / "build_lyra_phase4.py",
            rigged_root / "source" / "render_phase4_validation.py",
            rigged_root / "source" / "requirements.txt",
            manifest_path,
            report_path,
        ):
            with self.subTest(required_file=path.relative_to(ROOT)):
                self.assertTrue(path.is_file())

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["phase"], 4)
        self.assertEqual(manifest["source_assets"], {
            "lod0": "character_optimized/lyra_vesper_optimized.glb",
            "lod1": "character_lod/lyra_vesper_lod1.glb",
        })
        self.assertEqual(manifest["skeleton"]["deform_joint_count"], 48)
        self.assertEqual(manifest["skeleton"]["skin_palette_joint_count"], 54)
        self.assertEqual(manifest["skeleton"]["helper_node_count"], 6)
        self.assertEqual(manifest["skinning"]["max_influences"], 4)
        self.assertIn("disconnected", manifest["skinning"]["weight_policy"])
        self.assertIn("Phase 5", manifest["phase_boundary"]["production_animations"])
        self.assertEqual(report["phase"], 4)
        self.assertIn("not exported animation clips", report["method"])

        expected_materials = {"M_Lyra_OpaqueAtlas", "M_Lyra_LumenEnergy", "M_Lyra_AuroraMantle"}
        deform_names = {bone["name"] for bone in manifest["skeleton"]["deform_bones"]}
        helper_names = {bone["name"] for bone in manifest["skeleton"]["helpers"]}
        self.assertEqual(len(deform_names), 48)
        self.assertEqual(
            helper_names,
            {
                "socket_weapon",
                "socket_projectile",
                "socket_camera_body",
                "socket_camera_chest",
                "socket_camera_head",
                "socket_aim",
            },
        )
        expected_parent = {
            "socket_weapon": "hand_r",
            "socket_projectile": "socket_weapon",
            "socket_camera_body": "pelvis",
            "socket_camera_chest": "chest",
            "socket_camera_head": "head",
            "socket_aim": "chest",
        }
        source_metrics: dict[str, dict[str, int]] = {}
        for label, (asset, source) in assets.items():
            source_document = load_glb_json(source)
            source_triangles = sum(
                source_document["accessors"][primitive["indices"]]["count"] // 3
                for mesh in source_document["meshes"]
                for primitive in mesh["primitives"]
            )
            source_vertices = sum(
                source_document["accessors"][primitive["attributes"]["POSITION"]]["count"]
                for mesh in source_document["meshes"]
                for primitive in mesh["primitives"]
            )
            source_metrics[label] = {"triangles": source_triangles, "vertices": source_vertices}

            with self.subTest(asset=label):
                self.assertTrue(asset.is_file())
                self.assertGreater(asset.stat().st_size, 500_000)
                self.assertEqual(asset.read_bytes()[:4], b"glTF")
                document = load_glb_json(asset)
                binary = load_glb_binary_chunk(asset)
                self.assertEqual(document["asset"]["version"], "2.0")
                self.assertFalse(document.get("extensionsRequired"))
                self.assertEqual(len(document["meshes"]), 3)
                self.assertEqual(len(document["materials"]), 3)
                self.assertEqual(len(document["textures"]), 8)
                self.assertEqual(len(document["images"]), 8)
                self.assertEqual(len(document["nodes"]), 58)
                self.assertEqual({material["name"] for material in document["materials"]}, expected_materials)
                self.assertFalse(document.get("animations"))
                self.assertEqual(len(document["skins"]), 1)

                skin = document["skins"][0]
                self.assertEqual(skin["name"], "LyraVesper_DeformRig")
                self.assertEqual(len(skin["joints"]), 54)
                self.assertEqual(len(set(skin["joints"])), 54)
                self.assertIn(skin["skeleton"], range(len(document["nodes"])))
                inverse_bind = document["accessors"][skin["inverseBindMatrices"]]
                self.assertEqual(inverse_bind["componentType"], 5126)
                self.assertEqual(inverse_bind["type"], "MAT4")
                self.assertEqual(inverse_bind["count"], 54)
                self.assertEqual(len(accessor_rows(document, binary, skin["inverseBindMatrices"])), 54)

                node_names = {index: node.get("name") for index, node in enumerate(document["nodes"])}
                named_nodes = {name: index for index, name in node_names.items() if name}
                self.assertTrue({"root", *deform_names, *helper_names}.issubset(named_nodes))
                palette_names = {node_names[index] for index in skin["joints"]}
                self.assertEqual(palette_names, deform_names | helper_names)
                children = {
                    node_names[parent]: {node_names[child] for child in node.get("children", [])}
                    for parent, node in enumerate(document["nodes"])
                    if node.get("name")
                }
                for child_name, parent_name in expected_parent.items():
                    self.assertIn(child_name, children[parent_name])

                triangles = 0
                vertices = 0
                active_joints: set[int] = set()
                for mesh in document["meshes"]:
                    for primitive in mesh["primitives"]:
                        attributes = primitive["attributes"]
                        self.assertTrue({"POSITION", "NORMAL", "TANGENT", "TEXCOORD_0", "JOINTS_0", "WEIGHTS_0"}.issubset(attributes))
                        self.assertIn("material", primitive)
                        position_accessor = document["accessors"][attributes["POSITION"]]
                        joint_accessor = document["accessors"][attributes["JOINTS_0"]]
                        weight_accessor = document["accessors"][attributes["WEIGHTS_0"]]
                        self.assertEqual(joint_accessor["componentType"], 5121)
                        self.assertEqual(joint_accessor["type"], "VEC4")
                        self.assertEqual(weight_accessor["componentType"], 5121)
                        self.assertEqual(weight_accessor["type"], "VEC4")
                        self.assertTrue(weight_accessor["normalized"])
                        self.assertEqual(joint_accessor["count"], position_accessor["count"])
                        self.assertEqual(weight_accessor["count"], position_accessor["count"])
                        joint_rows = accessor_rows(document, binary, attributes["JOINTS_0"])
                        weight_rows = accessor_rows(document, binary, attributes["WEIGHTS_0"])
                        for joints, weights in zip(joint_rows, weight_rows):
                            self.assertEqual(sum(weights), 255)
                            self.assertLessEqual(sum(weight > 0 for weight in weights), 4)
                            for joint, weight in zip(joints, weights):
                                if weight:
                                    self.assertGreaterEqual(joint, 0)
                                    self.assertLess(joint, 54)
                                    active_joints.add(joint)
                        triangles += document["accessors"][primitive["indices"]]["count"] // 3
                        vertices += position_accessor["count"]
                self.assertEqual(active_joints, set(range(48)))
                self.assertEqual(triangles, source_metrics[label]["triangles"])
                self.assertEqual(vertices, source_metrics[label]["vertices"])
                self.assertEqual(manifest[f"rigged_{label}"]["triangles"], triangles)
                self.assertEqual(manifest[f"rigged_{label}"]["vertices"], vertices)
                self.assertEqual(manifest[f"rigged_{label}"]["weighted_vertices"], vertices)

                audit = report[label]["weight_audit"]
                self.assertEqual(audit["skin_palette_joint_count"], 54)
                self.assertEqual(audit["weighted_vertex_count"], vertices)
                self.assertEqual(audit["weight_sum_min"], 1.0)
                self.assertEqual(audit["weight_sum_max"], 1.0)
                self.assertFalse(audit["unused_deform_joints"])
                self.assertEqual(set(audit["influence_counts"]), deform_names | helper_names)
                socket_audit = report[label]["helper_socket_audit"]
                self.assertEqual(set(socket_audit), helper_names)
                for helper_name, parent_name in expected_parent.items():
                    self.assertEqual(socket_audit[helper_name]["parent"], parent_name)
                    self.assertTrue(socket_audit[helper_name]["palette_joint"])
                self.assertGreater(socket_audit["socket_weapon"]["draw_displacement_m"], 0.001)
                self.assertGreater(socket_audit["socket_projectile"]["draw_displacement_m"], 0.001)
                self.assertGreater(socket_audit["socket_camera_body"]["crouch_displacement_m"], 0.001)
                for pose_name in ("bind", "draw", "crouch"):
                    pose = report[label]["poses"][pose_name]
                    self.assertEqual(pose["vertices"], vertices)
                    self.assertLessEqual(pose["inverse_bind_max_abs_error"], 0.000002)
                    self.assertLessEqual(pose["max_displacement_m"], 3.0)
                self.assertEqual(report[label]["poses"]["bind"]["vertices_moved_over_1mm"], 0)
                self.assertEqual(report[label]["poses"]["bind"]["max_displacement_m"], 0.0)
                for pose_name in ("draw", "crouch"):
                    self.assertGreater(report[label]["poses"][pose_name]["vertices_moved_over_1mm"], 100)

        for relative_name in report["render_files"]:
            render = rigged_root / relative_name
            with self.subTest(render=relative_name):
                self.assertTrue(render.is_file())
                self.assertGreater(render.stat().st_size, 10_000)
                self.assertEqual(render.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_phase_five_animated_glbs_are_complete(self) -> None:
        """Require actual Phase 5 sampler/channel payload, not a static pose declaration."""

        source_assets = {
            "lod0": ROOT / "character_rigged" / "lyra_vesper_rigged.glb",
            "lod1": ROOT / "character_rigged" / "lyra_vesper_rigged_lod1.glb",
        }
        assets = {
            "lod0": PHASE5 / "lyra_vesper_animated.glb",
            "lod1": PHASE5 / "lyra_vesper_animated_lod1.glb",
        }
        manifest_path = PHASE5 / "animation_manifest.json"
        report_path = PHASE5 / "validation" / "animation_report.json"
        for path in (
            PHASE5 / "README.md",
            PHASE5 / "ANIMATION_SPECIFICATION.md",
            PHASE5 / "PHASE_5_QA.md",
            PHASE5 / "PHASE_6_HANDOFF.md",
            PHASE5 / "source" / "build_lyra_phase5.py",
            PHASE5 / "source" / "render_phase5_validation.py",
            PHASE5 / "source" / "requirements.txt",
            manifest_path,
            report_path,
        ):
            with self.subTest(required_file=path.relative_to(ROOT)):
                self.assertTrue(path.is_file())

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["phase"], 5)
        self.assertEqual(manifest["source_assets"], {
            "lod0": "character_rigged/lyra_vesper_rigged.glb",
            "lod1": "character_rigged/lyra_vesper_rigged_lod1.glb",
        })
        animation_contract = manifest["animation_contract"]
        self.assertEqual(tuple(animation_contract["canonical_clip_names"]), PHASE5_CANONICAL_CLIPS)
        self.assertEqual(animation_contract["clip_count"], 23)
        self.assertEqual(animation_contract["root_motion"], "in_place; no translation animation channel is authored.")
        manifest_clips = {clip["name"]: clip for clip in animation_contract["clips"]}
        self.assertEqual(tuple(manifest_clips), PHASE5_CANONICAL_CLIPS)

        expected_materials = {"M_Lyra_OpaqueAtlas", "M_Lyra_LumenEnergy", "M_Lyra_AuroraMantle"}
        lod_payloads: dict[str, tuple[dict[str, object], bytes]] = {}
        for label, asset in assets.items():
            source = source_assets[label]
            with self.subTest(asset=label):
                self.assertTrue(asset.is_file())
                self.assertGreater(asset.stat().st_size, source.stat().st_size + 150_000)
                self.assertEqual(asset.read_bytes()[:4], b"glTF")
            document = load_glb_json(asset)
            binary = load_glb_binary_chunk(asset)
            source_document = load_glb_json(source)
            source_binary = load_glb_binary_chunk(source)
            lod_payloads[label] = (document, binary)

            with self.subTest(asset=label, check="preserved_phase4_contract"):
                self.assertEqual(document["asset"]["version"], "2.0")
                self.assertFalse(document.get("extensionsRequired"))
                self.assertEqual(len(document["meshes"]), len(source_document["meshes"]))
                self.assertEqual(len(document["nodes"]), len(source_document["nodes"]))
                self.assertEqual(len(document["materials"]), len(source_document["materials"]))
                self.assertEqual(len(document["textures"]), len(source_document["textures"]))
                self.assertEqual(len(document["images"]), len(source_document["images"]))
                self.assertEqual({material["name"] for material in document["materials"]}, expected_materials)
                self.assertEqual(len(document["skins"]), 1)
                self.assertEqual(document["skins"], source_document["skins"])
                for source_mesh, mesh in zip(source_document["meshes"], document["meshes"]):
                    self.assertEqual(len(mesh["primitives"]), len(source_mesh["primitives"]))
                    for source_primitive, primitive in zip(source_mesh["primitives"], mesh["primitives"]):
                        self.assertEqual(primitive["material"], source_primitive["material"])
                        self.assertEqual(primitive["attributes"], source_primitive["attributes"])
                        self.assertEqual(primitive["indices"], source_primitive["indices"])
                        for accessor_index in (*primitive["attributes"].values(), primitive["indices"]):
                            target_accessor = document["accessors"][accessor_index]
                            source_accessor = source_document["accessors"][accessor_index]
                            self.assertEqual(target_accessor, source_accessor)
                source_skin = source_document["skins"][0]
                target_skin = document["skins"][0]
                self.assertEqual(
                    accessor_rows(document, binary, target_skin["inverseBindMatrices"]),
                    accessor_rows(source_document, source_binary, source_skin["inverseBindMatrices"]),
                )

            node_names = {index: node.get("name") for index, node in enumerate(document["nodes"])}
            named_nodes = {name: index for index, name in node_names.items() if name}
            skin = document["skins"][0]
            animatable_node_names = {node_names[index] for index in skin["joints"]} | {"root"}
            self.assertEqual(tuple(animation["name"] for animation in document["animations"]), PHASE5_CANONICAL_CLIPS)
            self.assertEqual(len(document["animations"]), 23)
            self.assertEqual(sum(len(animation["channels"]) for animation in document["animations"]), 523)
            self.assertEqual(sum(len(animation["samplers"]) for animation in document["animations"]), 523)
            self.assertEqual(manifest[f"animated_{label}"]["animations"], 23)
            self.assertEqual(manifest[f"animated_{label}"]["channels"], 523)
            self.assertEqual(manifest[f"animated_{label}"]["samplers"], 523)
            self.assertEqual(manifest[f"animated_{label}"]["rotation_keys"], 2796)
            self.assertEqual(manifest[f"animated_{label}"]["triangles"], 11496 if label == "lod0" else 5843)
            self.assertEqual(manifest[f"animated_{label}"]["vertices"], 8431 if label == "lod0" else 4834)

            rotation_keys = 0
            direct_tracks: dict[str, set[str]] = {}
            for animation in document["animations"]:
                clip_name = animation["name"]
                duration, expected_tracks, normalized_times, expected_loop, expected_events = PHASE5_CLIP_CONTRACT[clip_name]
                with self.subTest(asset=label, clip=clip_name):
                    self.assertEqual(len(animation["channels"]), expected_tracks)
                    self.assertEqual(len(animation["samplers"]), expected_tracks)
                    self.assertEqual(sorted(channel["sampler"] for channel in animation["channels"]), list(range(expected_tracks)))
                    extras = animation.get("extras", {})
                    self.assertEqual(extras.get("phase"), 5)
                    self.assertEqual(extras.get("loop"), expected_loop)
                    self.assertEqual(extras.get("root_motion"), "in_place")
                    self.assertIsInstance(extras.get("purpose"), str)
                    self.assertTrue(extras["purpose"])
                    event_tuples = tuple((event["name"], event["time_s"]) for event in extras.get("semantic_events", []))
                    self.assertEqual(event_tuples, expected_events)
                    for event in extras.get("semantic_events", []):
                        self.assertIsInstance(event.get("meaning"), str)
                        self.assertTrue(event["meaning"])
                        self.assertGreaterEqual(event["time_s"], 0.0)
                        self.assertLessEqual(event["time_s"], duration)
                    self.assertEqual(
                        tuple((event["name"], event["time_s"]) for event in manifest_clips[clip_name]["semantic_events"]),
                        expected_events,
                    )
                    self.assertEqual(manifest_clips[clip_name]["duration_s"], duration)
                    self.assertEqual(manifest_clips[clip_name]["loop"], expected_loop)
                    self.assertEqual(manifest_clips[clip_name]["keyframe_count"], len(normalized_times))

                    targets: set[str] = set()
                    all_non_identity = False
                    for channel in animation["channels"]:
                        target = channel["target"]
                        self.assertEqual(target["path"], "rotation")
                        target_name = node_names[target["node"]]
                        self.assertIn(target_name, animatable_node_names)
                        self.assertNotIn(target_name, {"socket_weapon", "socket_projectile", "socket_camera_body", "socket_camera_chest", "socket_camera_head", "socket_aim"})
                        targets.add(target_name)
                        sampler = animation["samplers"][channel["sampler"]]
                        self.assertEqual(sampler.get("interpolation", "LINEAR"), "LINEAR")
                        input_accessor = document["accessors"][sampler["input"]]
                        output_accessor = document["accessors"][sampler["output"]]
                        self.assertEqual((input_accessor["componentType"], input_accessor["type"], input_accessor["count"]), (5126, "SCALAR", len(normalized_times)))
                        self.assertEqual((output_accessor["componentType"], output_accessor["type"], output_accessor["count"]), (5126, "VEC4", len(normalized_times)))
                        times = [row[0] for row in accessor_rows(document, binary, sampler["input"])]
                        self.assertEqual(len(times), len(normalized_times))
                        for actual, normalized in zip(times, normalized_times):
                            self.assertAlmostEqual(actual, duration * normalized, places=6)
                        self.assertTrue(all(second > first for first, second in zip(times, times[1:])))
                        quaternion_rows = accessor_rows(document, binary, sampler["output"])
                        for quaternion in quaternion_rows:
                            self.assertAlmostEqual(math.sqrt(sum(component * component for component in quaternion)), 1.0, places=5)
                        all_non_identity |= any(
                            any(abs(component - identity_component) > 1e-5 for component, identity_component in zip(quaternion, (0.0, 0.0, 0.0, 1.0)))
                            for quaternion in quaternion_rows
                        )
                        rotation_keys += len(quaternion_rows)
                    self.assertEqual(len(targets), expected_tracks)
                    self.assertTrue(all_non_identity)
                    self.assertEqual(targets, set(manifest_clips[clip_name]["direct_rotation_tracks"]))
                    direct_tracks[clip_name] = targets

            self.assertEqual(rotation_keys, 2796)
            self.assertTrue({"hand_l", "hand_r", "hair_mid", "hair_tip", "mantle_mid", "mantle_tip"}.issubset(direct_tracks["basic_attack"]))
            self.assertTrue(PHASE5_FINGER_TRACKS.issubset(direct_tracks["basic_attack"]))
            for clip_name in PHASE5_ACTION_CLIPS:
                self.assertTrue({"hair_mid", "hair_tip", "mantle_mid", "mantle_tip"}.issubset(direct_tracks[clip_name]))
            for clip_name in ("walk", "run"):
                self.assertTrue({"thigh_l", "thigh_r", "calf_l", "calf_r", "foot_l", "foot_r", "toe_l", "toe_r", "upperarm_l", "upperarm_r"}.issubset(direct_tracks[clip_name]))

            asset_report = report[label]
            self.assertEqual(asset_report["asset"], asset.name)
            self.assertEqual(asset_report["sha256"], hashlib.sha256(asset.read_bytes()).hexdigest())
            self.assertEqual(asset_report["animation_count"], 23)
            self.assertEqual(asset_report["translation_channels"], 0)
            self.assertEqual(asset_report["root_translation_channels"], 0)
            self.assertLessEqual(asset_report["inverse_bind_max_abs_error"], 0.000002)
            self.assertEqual(tuple(asset_report["clips"]), PHASE5_CANONICAL_CLIPS)
            for clip_name, clip_report in asset_report["clips"].items():
                self.assertEqual(clip_report["channels"], PHASE5_CLIP_CONTRACT[clip_name][1])
                self.assertGreater(clip_report["max_vertices_moved_over_1mm"], 100)
                self.assertGreater(clip_report["max_displacement_m"], 0.001)
                self.assertLessEqual(clip_report["max_displacement_m"], 4.5)
            socket_report = asset_report["event_socket_audit"]
            self.assertEqual(socket_report["event_sample_count"], 41)
            self.assertLessEqual(socket_report["max_hand_to_weapon_abs_error"], 0.000002)
            self.assertLessEqual(socket_report["max_weapon_to_projectile_abs_error"], 0.000002)
            self.assertLessEqual(socket_report["max_root_position_error_m"], 0.000002)
            self.assertGreater(asset_report["helper_motion"]["basic_attack:socket_weapon"]["displacement_m"], 0.001)
            self.assertGreater(asset_report["helper_motion"]["basic_attack:socket_projectile"]["displacement_m"], 0.001)

        self.assertEqual(
            animation_curve_signature(*lod_payloads["lod0"]),
            animation_curve_signature(*lod_payloads["lod1"]),
        )
        self.assertEqual(len(report["render_samples"]), 10)
        for render_sample in report["render_samples"]:
            render = PHASE5 / render_sample["file"]
            with self.subTest(render=render_sample["file"]):
                self.assertTrue(render.is_file())
                self.assertGreater(render.stat().st_size, 10_000)
                self.assertEqual(render.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_project_entry_point_exists(self) -> None:
        project = ROOT / "project.godot"
        self.assertTrue(project.is_file())
        config = project.read_text(encoding="utf-8")
        match = re.search(r'run/main_scene="res://([^\"]+)"', config)
        self.assertIsNotNone(match)
        self.assertTrue((ROOT / match.group(1)).is_file())

    def test_hero_scene_contains_required_system_boundaries(self) -> None:
        scene = (HERO / "scenes" / "hero_character.tscn").read_text(encoding="utf-8")
        required_nodes = {
            "HeroCharacter": "CharacterBody3D",
            "Visual": "Node3D",
            "Animation": "Node",
            "Movement": "Node",
            "BasicAttack": "Node",
            "AbilityController": "Node",
            "Targeting": "Node",
            "DamageReceiver": "Node",
            "Stats": "Node",
            "Health": "Node",
            "Energy": "Node",
            "Hurtbox": "Area3D",
            "Hitbox": "Area3D",
            "Detection": "Area3D",
            "CameraTarget": "Node3D",
        }
        for node_name, node_type in required_nodes.items():
            with self.subTest(node=node_name):
                self.assertRegex(
                    scene,
                    rf'\[node name="{node_name}" type="{node_type}"',
                )

    def test_scene_external_paths_resolve(self) -> None:
        for scene_or_resource in ROOT.rglob("*.tscn"):
            content = scene_or_resource.read_text(encoding="utf-8")
            for resource_path in re.findall(r'path="res://([^\"]+)"', content):
                with self.subTest(file=scene_or_resource, resource=resource_path):
                    self.assertTrue((ROOT / resource_path).exists())
        for resource in ROOT.rglob("*.tres"):
            content = resource.read_text(encoding="utf-8")
            for resource_path in re.findall(r'path="res://([^\"]+)"', content):
                with self.subTest(file=resource, resource=resource_path):
                    self.assertTrue((ROOT / resource_path).exists())

    def test_ability_slots_and_lifecycle_are_implemented(self) -> None:
        lifecycle = (HERO / "scripts" / "gameplay" / "hero_ability.gd").read_text(encoding="utf-8")
        for lifecycle_marker in ("CAST", "ACTION", "RECOVERY", "cooldown_remaining"):
            self.assertIn(lifecycle_marker, lifecycle)
        self.assertIn("if requires_target and resolved_target != null and not _target_in_range", lifecycle)
        expected = {
            "slipstream_passive.gd": "SlipstreamPassive",
            "prism_volley.gd": "PrismVolleyAbility",
            "phase_step.gd": "PhaseStepAbility",
            "tether_snare.gd": "TetherSnareAbility",
            "apex_constellation.gd": "ApexConstellationAbility",
        }
        gameplay = HERO / "scripts" / "gameplay"
        for filename, class_name in expected.items():
            with self.subTest(ability=filename):
                content = (gameplay / filename).read_text(encoding="utf-8")
                self.assertIn(f"class_name {class_name}", content)

    def test_damage_pipeline_is_data_driven_and_separated(self) -> None:
        event = (HERO / "scripts" / "core" / "damage_event.gd").read_text(encoding="utf-8")
        for field in (
            "source",
            "target",
            "amount",
            "damage_type",
            "critical",
            "modifiers",
            "ability_id",
            "attack_source",
        ):
            self.assertRegex(event, rf"var {field}")
        projectile = (HERO / "scripts" / "interaction" / "projectile.gd").read_text(encoding="utf-8")
        self.assertIn("hurtbox", projectile)
        self.assertIn("receiver.receive_damage", projectile)
        receiver = (HERO / "scripts" / "gameplay" / "damage_receiver.gd").read_text(encoding="utf-8")
        self.assertIn("health.apply_damage", receiver)

    def test_imported_presentation_and_audio_assets_exist(self) -> None:
        adapter = (HERO / "scripts" / "presentation" / "hero_presentation_adapter.gd").read_text(encoding="utf-8")
        for marker in (
            "HeroPresentationAdapter",
            "lyra_vesper_animated.glb",
            "lyra_vesper_animated_lod1.glb",
            "AnimationTree",
            "BoneAttachment3D",
            "socket_projectile",
            "animation_manifest.json",
            "set_lod_level",
        ):
            self.assertIn(marker, adapter)
        self.assertTrue((HERO / "scenes" / "lyra_presentation_preview.tscn").is_file())
        self.assertTrue((ROOT / "tests" / "godot" / "phase6_import_probe.gd").is_file())
        self.assertTrue((ROOT / "tests" / "godot" / "phase6_integration_smoke.gd").is_file())
        audio_files = sorted((HERO / "audio").glob("*.wav"))
        self.assertGreaterEqual(len(audio_files), 10)
        for audio_file in audio_files:
            with self.subTest(audio=audio_file.name):
                with wave.open(str(audio_file), "rb") as handle:
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertEqual(handle.getsampwidth(), 2)
                    self.assertGreater(handle.getnframes(), 100)

    def test_phase_six_imported_visual_replaces_active_primitive_path(self) -> None:
        scene_text = (HERO / "scenes" / "hero_character.tscn").read_text(encoding="utf-8")
        hero_text = (HERO / "scripts" / "hero_character.gd").read_text(encoding="utf-8")
        adapter_text = (HERO / "scripts" / "presentation" / "hero_presentation_adapter.gd").read_text(encoding="utf-8")
        driver_text = (HERO / "scripts" / "presentation" / "hero_animation_driver.gd").read_text(encoding="utf-8")
        attack_text = (HERO / "scripts" / "gameplay" / "basic_attack.gd").read_text(encoding="utf-8")
        camera_text = (HERO / "scripts" / "presentation" / "camera_target.gd").read_text(encoding="utf-8")

        self.assertIn("hero_presentation_adapter.gd", scene_text)
        self.assertNotIn("hero_visual.gd", scene_text)
        self.assertNotIn('parent="Visual/CharacterModel"', scene_text)
        self.assertNotIn('parent="Animation"', scene_text)
        self.assertIn("var visual: HeroPresentationAdapter", hero_text)
        self.assertIn('get_node_or_null("Hurtbox") as Hurtbox', hero_text)
        self.assertIn('get_node_or_null("Hitbox") as Hitbox', hero_text)
        self.assertIn("visual.semantic_event.connect", hero_text)
        self.assertIn("do not\n\t# create another projectile", hero_text)
        self.assertIn("HeroPresentationAdapter", driver_text)
        self.assertNotIn("_apply_pose", driver_text)
        self.assertNotIn("_install_named_clips", driver_text)
        self.assertIn("get_semantic_event_time", attack_text)
        self.assertIn("one and only authoritative projectile spawn path", attack_text)
        self.assertIn("bind_visual", camera_text)
        self.assertIn("socket_camera_head", camera_text)
        self.assertIn("apply_phase45_axis_conversion", adapter_text)
        self.assertIn("Basis(Vector3.LEFT, Vector3.BACK, Vector3.UP)", adapter_text)
        self.assertIn("(x, y, z) → (-x, z, y)", adapter_text)
        for helper in (
            "socket_weapon",
            "socket_projectile",
            "socket_camera_body",
            "socket_camera_chest",
            "socket_camera_head",
            "socket_aim",
        ):
            with self.subTest(helper=helper):
                self.assertIn(helper, adapter_text)
        adapter_without_comments = re.sub(r"#.*", "", adapter_text)
        self.assertNotIn("spawn_projectile(", adapter_without_comments)
        self.assertNotIn("DamageEvent.new", adapter_without_comments)

    def test_gdscript_class_names_are_unique(self) -> None:
        class_names: dict[str, Path] = {}
        for script in ROOT.rglob("*.gd"):
            content = script.read_text(encoding="utf-8")
            match = re.search(r"^class_name\s+(\w+)", content, re.MULTILINE)
            if not match:
                continue
            class_name = match.group(1)
            self.assertNotIn(class_name, class_names, f"{class_name}: {script} and {class_names.get(class_name)}")
            class_names[class_name] = script

    def test_godot_void_erase_is_not_used_as_a_condition(self) -> None:
        for script in ROOT.rglob("*.gd"):
            with self.subTest(script=script):
                content = script.read_text(encoding="utf-8")
                self.assertNotRegex(content, r"if\s+[^\n]*\.erase\(")

    def test_node3d_helpers_do_not_shadow_transform_properties(self) -> None:
        # Godot warns on local parameter names that shadow inherited Node3D fields.
        for script in (
            HERO / "scripts" / "presentation" / "hero_presentation_adapter.gd",
            ROOT / "demo" / "scripts" / "demo_arena.gd",
        ):
            with self.subTest(script=script):
                content = script.read_text(encoding="utf-8")
                self.assertNotRegex(content, r"\b(position|rotation|scale)\s*:\s*Vector3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
