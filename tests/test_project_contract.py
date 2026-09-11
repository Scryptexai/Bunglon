"""Static contract checks for the self-contained Godot hero foundation.

These tests intentionally avoid requiring a Godot executable. Godot runtime validation is
covered by the manual/editor checklist in heroes/hero_agile_hunter/docs/TESTING.md.
"""

from __future__ import annotations

import json
import re
import struct
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "heroes" / "hero_agile_hunter"


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
            "Skeleton": "Skeleton3D",
            "Weapon": "Node3D",
            "AnimationPlayer": "AnimationPlayer",
            "AnimationTree": "AnimationTree",
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

    def test_native_model_rig_and_audio_assets_exist(self) -> None:
        visual = (HERO / "scripts" / "presentation" / "hero_visual.gd").read_text(encoding="utf-8")
        for marker in ("Skeleton3D", "BoneAttachment3D", "ProjectileOrigin", "EnergyString", "AuroraMantle"):
            self.assertIn(marker, visual)
        audio_files = sorted((HERO / "audio").glob("*.wav"))
        self.assertGreaterEqual(len(audio_files), 10)
        for audio_file in audio_files:
            with self.subTest(audio=audio_file.name):
                with wave.open(str(audio_file), "rb") as handle:
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertEqual(handle.getsampwidth(), 2)
                    self.assertGreater(handle.getnframes(), 100)

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
            HERO / "scripts" / "presentation" / "hero_visual.gd",
            ROOT / "demo" / "scripts" / "demo_arena.gd",
        ):
            with self.subTest(script=script):
                content = script.read_text(encoding="utf-8")
                self.assertNotRegex(content, r"\b(position|rotation|scale)\s*:\s*Vector3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
