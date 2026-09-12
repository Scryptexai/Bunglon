#!/usr/bin/env python3
"""Build Lyra Vesper's Phase 5 animation handoff from the Phase 4 skinned GLBs.

The builder adds real, standard glTF 2.0 skeletal animation channels to the actual Phase 4
LOD0/LOD1 assets. It preserves skin streams, material bindings, inverse-bind matrices,
and the named socket hierarchy. Root translation is deliberately never animated: gameplay
locomotion remains in-place and authoritative outside the visual asset.

Run from the repository root:
    python3 -m venv /tmp/lyra-phase5-venv
    /tmp/lyra-phase5-venv/bin/pip install -r character_animated/source/requirements.txt
    /tmp/lyra-phase5-venv/bin/python character_animated/source/build_lyra_phase5.py
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from pygltflib import Animation, AnimationChannel, AnimationChannelTarget, AnimationSampler, GLTF2

ROOT = Path(__file__).resolve().parents[2]
PHASE4_SOURCE = ROOT / "character_rigged" / "source"
if str(PHASE4_SOURCE) not in sys.path:
    sys.path.insert(0, str(PHASE4_SOURCE))

from build_lyra_phase4 import (  # noqa: E402
    ACCESSOR_COMPONENTS,
    CLI,
    DEFORM_BONES,
    append_accessor,
    command,
    load_glb_json,
    read_accessor,
    set_buffer_targets,
)

RIGGED_LOD0 = ROOT / "character_rigged" / "lyra_vesper_rigged.glb"
RIGGED_LOD1 = ROOT / "character_rigged" / "lyra_vesper_rigged_lod1.glb"
OUTPUT = ROOT / "character_animated"
LOD0_OUTPUT = OUTPUT / "lyra_vesper_animated.glb"
LOD1_OUTPUT = OUTPUT / "lyra_vesper_animated_lod1.glb"
MANIFEST_PATH = OUTPUT / "animation_manifest.json"

Axis = tuple[float, float, float]
Rotation = tuple[Axis, float]
Pose = dict[str, Rotation]
X_AXIS: Axis = (1.0, 0.0, 0.0)
Y_AXIS: Axis = (0.0, 1.0, 0.0)
Z_AXIS: Axis = (0.0, 0.0, 1.0)
IDENTITY_QUATERNION = np.asarray((0.0, 0.0, 0.0, 1.0), dtype=np.float32)
CANONICAL_CLIPS = (
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
ANIMATABLE_BONES = {"root", *(bone.name for bone in DEFORM_BONES)}


@dataclass(frozen=True)
class SemanticEvent:
    name: str
    normalized_time: float
    meaning: str


@dataclass(frozen=True)
class ClipSpec:
    name: str
    duration_s: float
    loop: bool
    purpose: str
    frames: tuple[tuple[float, Pose], ...]
    events: tuple[SemanticEvent, ...] = ()


def rotations(*items: tuple[str, Axis, float]) -> Pose:
    return {bone_name: (axis, degrees) for bone_name, axis, degrees in items}


def merge(*poses: Pose) -> Pose:
    result: Pose = {}
    for pose in poses:
        result.update(pose)
    return result


def digit_curl(side: str, base_degrees: float, tip_degrees: float) -> Pose:
    """Create a deliberately restrained curl for Lyra's compact two-joint digits."""

    if side not in {"l", "r"}:
        raise ValueError(f"Unsupported hand side: {side}")
    sign = 1.0 if side == "l" else -1.0
    result: Pose = {}
    for digit, base_scale, tip_scale in (
        ("thumb", 0.72, 0.75),
        ("index", 1.00, 1.00),
        ("middle", 0.94, 0.96),
        ("ring", 0.82, 0.86),
        ("pinky", 0.68, 0.73),
    ):
        result[f"{digit}_01_{side}"] = (Y_AXIS, sign * base_degrees * base_scale)
        result[f"{digit}_02_{side}"] = (Y_AXIS, sign * tip_degrees * tip_scale)
    return result


def secondary_motion(hair_degrees: float, mantle_degrees: float) -> Pose:
    return rotations(
        ("hair_mid", Y_AXIS, hair_degrees),
        ("hair_tip", Y_AXIS, hair_degrees * 1.58),
        ("mantle_mid", X_AXIS, mantle_degrees),
        ("mantle_tip", X_AXIS, mantle_degrees * 1.62),
    )


def gait(stride_degrees: float, arm_degrees: float, secondary_degrees: float) -> Pose:
    """In-place alternating gait: feet move, but root translation remains untouched."""

    return merge(
        rotations(
            ("pelvis", X_AXIS, stride_degrees * 0.08),
            ("spine_01", X_AXIS, -stride_degrees * 0.10),
            ("chest", Y_AXIS, stride_degrees * 0.12),
            ("thigh_l", X_AXIS, stride_degrees),
            ("thigh_r", X_AXIS, -stride_degrees),
            ("calf_l", X_AXIS, max(0.0, -stride_degrees) * 1.08),
            ("calf_r", X_AXIS, max(0.0, stride_degrees) * 1.08),
            ("foot_l", X_AXIS, -stride_degrees * 0.34),
            ("foot_r", X_AXIS, stride_degrees * 0.34),
            ("toe_l", X_AXIS, max(0.0, stride_degrees) * 0.22),
            ("toe_r", X_AXIS, max(0.0, -stride_degrees) * 0.22),
            ("clavicle_l", X_AXIS, -arm_degrees * 0.22),
            ("upperarm_l", X_AXIS, -arm_degrees),
            ("lowerarm_l", X_AXIS, arm_degrees * 0.32),
            # The bow-side arm counter-swings but stays noticeably more controlled.
            ("clavicle_r", X_AXIS, arm_degrees * 0.14),
            ("upperarm_r", X_AXIS, arm_degrees * 0.52),
            ("lowerarm_r", X_AXIS, -arm_degrees * 0.18),
        ),
        secondary_motion(secondary_degrees, -secondary_degrees * 0.78),
    )


IDLE_RISE = merge(
    rotations(
        ("spine_01", X_AXIS, -1.6),
        ("chest", X_AXIS, 2.4),
        ("neck", Y_AXIS, 1.2),
        ("head", Y_AXIS, -2.0),
        ("clavicle_l", Z_AXIS, -1.5),
        ("clavicle_r", Z_AXIS, 1.0),
    ),
    secondary_motion(-3.0, 2.0),
)
IDLE_FALL = merge(
    rotations(
        ("spine_01", X_AXIS, 1.2),
        ("chest", X_AXIS, -1.8),
        ("neck", Y_AXIS, -1.2),
        ("head", Y_AXIS, 2.0),
        ("clavicle_l", Z_AXIS, 1.0),
        ("clavicle_r", Z_AXIS, -1.5),
    ),
    secondary_motion(3.0, -2.0),
)
IDLE_LOOK = merge(
    rotations(
        ("pelvis", Y_AXIS, -3.0),
        ("spine_02", Y_AXIS, 5.0),
        ("chest", Y_AXIS, 7.0),
        ("neck", Y_AXIS, 8.0),
        ("head", Y_AXIS, 11.0),
        ("upperarm_l", Z_AXIS, -4.0),
        ("upperarm_r", Z_AXIS, 3.0),
    ),
    secondary_motion(-6.0, 5.0),
)
IDLE_SETTLE = merge(
    rotations(
        ("pelvis", Y_AXIS, 2.0),
        ("spine_02", Y_AXIS, -3.0),
        ("chest", Y_AXIS, -4.0),
        ("neck", Y_AXIS, -5.0),
        ("head", Y_AXIS, -6.0),
    ),
    secondary_motion(4.0, -4.0),
)
WALK_LEFT = gait(17.0, 14.0, 5.0)
WALK_RIGHT = gait(-17.0, -14.0, -5.0)
RUN_LEFT = gait(29.0, 23.0, 9.0)
RUN_RIGHT = gait(-29.0, -23.0, -9.0)
RUN_PREP = merge(
    rotations(
        ("pelvis", X_AXIS, 7.0),
        ("spine_01", X_AXIS, -9.0),
        ("spine_02", X_AXIS, -11.0),
        ("chest", X_AXIS, -6.0),
        ("thigh_l", X_AXIS, 17.0),
        ("thigh_r", X_AXIS, -13.0),
        ("calf_l", X_AXIS, -10.0),
        ("calf_r", X_AXIS, 15.0),
    ),
    secondary_motion(7.0, 9.0),
)
STOP_POSE = merge(
    rotations(
        ("pelvis", X_AXIS, -5.0),
        ("spine_01", X_AXIS, 7.0),
        ("chest", X_AXIS, 4.0),
        ("thigh_l", X_AXIS, -12.0),
        ("thigh_r", X_AXIS, 16.0),
        ("calf_l", X_AXIS, 12.0),
        ("calf_r", X_AXIS, -9.0),
    ),
    secondary_motion(-8.0, -8.0),
)
TURN_LEFT = merge(
    rotations(
        ("pelvis", Y_AXIS, -10.0),
        ("spine_01", Y_AXIS, -13.0),
        ("spine_02", Y_AXIS, -16.0),
        ("chest", Y_AXIS, -19.0),
        ("neck", Y_AXIS, -10.0),
        ("head", Y_AXIS, -12.0),
        ("thigh_l", Z_AXIS, -7.0),
        ("thigh_r", Z_AXIS, 7.0),
    ),
    secondary_motion(-8.0, 7.0),
)
TURN_RIGHT = merge(
    rotations(
        ("pelvis", Y_AXIS, 10.0),
        ("spine_01", Y_AXIS, 13.0),
        ("spine_02", Y_AXIS, 16.0),
        ("chest", Y_AXIS, 19.0),
        ("neck", Y_AXIS, 10.0),
        ("head", Y_AXIS, 12.0),
        ("thigh_l", Z_AXIS, 7.0),
        ("thigh_r", Z_AXIS, -7.0),
    ),
    secondary_motion(8.0, -7.0),
)
BOW_PREP = merge(
    rotations(
        ("spine_02", Y_AXIS, -4.0),
        ("chest", Y_AXIS, -6.0),
        ("clavicle_l", Y_AXIS, 7.0),
        ("upperarm_l", Y_AXIS, 12.0),
        ("lowerarm_l", Y_AXIS, 17.0),
        ("hand_l", X_AXIS, -6.0),
        ("clavicle_r", Y_AXIS, -6.0),
        ("upperarm_r", Y_AXIS, -11.0),
        ("lowerarm_r", Y_AXIS, -17.0),
        ("hand_r", X_AXIS, 5.0),
    ),
    digit_curl("l", 5.0, 7.0),
    digit_curl("r", 4.0, 6.0),
    secondary_motion(-7.0, 6.0),
)
BOW_DRAW = merge(
    rotations(
        ("pelvis", Y_AXIS, 3.0),
        ("spine_01", Y_AXIS, -4.0),
        ("spine_02", Y_AXIS, -8.0),
        ("chest", Y_AXIS, -11.0),
        ("neck", Y_AXIS, -4.0),
        ("head", Y_AXIS, -6.0),
        ("clavicle_l", Y_AXIS, 12.0),
        ("upperarm_l", Y_AXIS, 24.0),
        ("lowerarm_l", Y_AXIS, 31.0),
        ("hand_l", X_AXIS, -12.0),
        ("clavicle_r", Y_AXIS, -10.0),
        ("upperarm_r", Y_AXIS, -21.0),
        ("lowerarm_r", Y_AXIS, -29.0),
        ("hand_r", X_AXIS, 10.0),
    ),
    digit_curl("l", 13.0, 17.0),
    digit_curl("r", 9.0, 12.0),
    secondary_motion(-14.0, 12.0),
)
BOW_RELEASE = merge(
    rotations(
        ("pelvis", Y_AXIS, 2.0),
        ("spine_01", Y_AXIS, -2.0),
        ("spine_02", Y_AXIS, -5.0),
        ("chest", Y_AXIS, -7.0),
        ("neck", Y_AXIS, -2.0),
        ("head", Y_AXIS, -3.0),
        ("clavicle_l", Y_AXIS, 8.0),
        ("upperarm_l", Y_AXIS, 17.0),
        ("lowerarm_l", Y_AXIS, 12.0),
        ("hand_l", X_AXIS, 2.0),
        ("clavicle_r", Y_AXIS, -8.0),
        ("upperarm_r", Y_AXIS, -16.0),
        ("lowerarm_r", Y_AXIS, -15.0),
        ("hand_r", X_AXIS, 7.0),
    ),
    digit_curl("l", 2.0, 3.0),
    digit_curl("r", 7.0, 9.0),
    secondary_motion(-3.0, 10.0),
)
BOW_FOLLOW = merge(
    rotations(
        ("spine_02", Y_AXIS, -3.0),
        ("chest", Y_AXIS, -3.0),
        ("upperarm_l", Y_AXIS, 8.0),
        ("lowerarm_l", Y_AXIS, 4.0),
        ("upperarm_r", Y_AXIS, -9.0),
        ("lowerarm_r", Y_AXIS, -10.0),
    ),
    digit_curl("l", 1.0, 1.0),
    digit_curl("r", 4.0, 5.0),
    secondary_motion(4.0, 7.0),
)
ATTACK_VARIANT = merge(
    BOW_DRAW,
    rotations(
        ("pelvis", Y_AXIS, -7.0),
        ("chest", Y_AXIS, 6.0),
        ("thigh_l", X_AXIS, 10.0),
        ("thigh_r", X_AXIS, -10.0),
    ),
    secondary_motion(-18.0, 15.0),
)
CHARGED_DRAW = merge(
    BOW_DRAW,
    rotations(
        ("spine_02", Y_AXIS, -11.0),
        ("chest", Y_AXIS, -15.0),
        ("upperarm_l", Y_AXIS, 30.0),
        ("lowerarm_l", Y_AXIS, 37.0),
        ("upperarm_r", Y_AXIS, -27.0),
        ("lowerarm_r", Y_AXIS, -36.0),
    ),
    digit_curl("l", 17.0, 21.0),
    digit_curl("r", 12.0, 16.0),
    secondary_motion(-20.0, 16.0),
)
DASH_CHARGE = merge(
    rotations(
        ("pelvis", X_AXIS, 9.0),
        ("spine_01", X_AXIS, -13.0),
        ("spine_02", X_AXIS, -15.0),
        ("chest", X_AXIS, -8.0),
        ("head", X_AXIS, -4.0),
        ("thigh_l", X_AXIS, 20.0),
        ("thigh_r", X_AXIS, 16.0),
        ("calf_l", X_AXIS, -22.0),
        ("calf_r", X_AXIS, -18.0),
        ("upperarm_l", X_AXIS, -19.0),
        ("upperarm_r", X_AXIS, -15.0),
    ),
    secondary_motion(13.0, 14.0),
)
DASH_PEAK = merge(
    rotations(
        ("pelvis", X_AXIS, 12.0),
        ("spine_01", X_AXIS, -20.0),
        ("spine_02", X_AXIS, -23.0),
        ("chest", X_AXIS, -12.0),
        ("head", X_AXIS, -7.0),
        ("thigh_l", X_AXIS, -25.0),
        ("thigh_r", X_AXIS, 27.0),
        ("calf_l", X_AXIS, 35.0),
        ("calf_r", X_AXIS, -29.0),
        ("foot_l", X_AXIS, 12.0),
        ("foot_r", X_AXIS, -12.0),
        ("upperarm_l", X_AXIS, -29.0),
        ("upperarm_r", X_AXIS, -24.0),
    ),
    secondary_motion(23.0, 22.0),
)
HIT_LIGHT = merge(
    rotations(
        ("pelvis", X_AXIS, 3.0),
        ("spine_01", X_AXIS, 6.0),
        ("chest", X_AXIS, 9.0),
        ("head", X_AXIS, 7.0),
        ("upperarm_l", X_AXIS, 7.0),
        ("upperarm_r", X_AXIS, 5.0),
    ),
    secondary_motion(8.0, -7.0),
)
HIT_HEAVY = merge(
    rotations(
        ("pelvis", X_AXIS, 8.0),
        ("spine_01", X_AXIS, 15.0),
        ("spine_02", X_AXIS, 18.0),
        ("chest", X_AXIS, 17.0),
        ("neck", X_AXIS, 8.0),
        ("head", X_AXIS, 12.0),
        ("thigh_l", X_AXIS, -11.0),
        ("thigh_r", X_AXIS, -11.0),
        ("upperarm_l", X_AXIS, 17.0),
        ("upperarm_r", X_AXIS, 14.0),
    ),
    secondary_motion(16.0, -14.0),
)
KNOCKBACK = merge(
    rotations(
        ("pelvis", X_AXIS, 14.0),
        ("spine_01", X_AXIS, 22.0),
        ("spine_02", X_AXIS, 25.0),
        ("chest", X_AXIS, 21.0),
        ("neck", X_AXIS, 12.0),
        ("head", X_AXIS, 15.0),
        ("thigh_l", X_AXIS, -25.0),
        ("thigh_r", X_AXIS, -22.0),
        ("calf_l", X_AXIS, 16.0),
        ("calf_r", X_AXIS, 13.0),
        ("upperarm_l", X_AXIS, 28.0),
        ("upperarm_r", X_AXIS, 25.0),
    ),
    secondary_motion(22.0, -18.0),
)
STUN_LEFT = merge(
    rotations(
        ("spine_01", Y_AXIS, -4.0),
        ("chest", Y_AXIS, -6.0),
        ("head", Y_AXIS, -7.0),
        ("upperarm_l", Z_AXIS, -6.0),
        ("upperarm_r", Z_AXIS, 4.0),
    ),
    secondary_motion(-6.0, 5.0),
)
STUN_RIGHT = merge(
    rotations(
        ("spine_01", Y_AXIS, 4.0),
        ("chest", Y_AXIS, 6.0),
        ("head", Y_AXIS, 7.0),
        ("upperarm_l", Z_AXIS, 6.0),
        ("upperarm_r", Z_AXIS, -4.0),
    ),
    secondary_motion(6.0, -5.0),
)
DEATH_START = merge(HIT_HEAVY, rotations(("root", X_AXIS, 0.0)))
DEATH_FALL = merge(
    rotations(
        ("root", X_AXIS, 52.0),
        ("pelvis", X_AXIS, 12.0),
        ("spine_01", X_AXIS, -18.0),
        ("spine_02", X_AXIS, -26.0),
        ("chest", X_AXIS, -19.0),
        ("neck", X_AXIS, 12.0),
        ("head", X_AXIS, 19.0),
        ("thigh_l", X_AXIS, 29.0),
        ("thigh_r", X_AXIS, -24.0),
        ("calf_l", X_AXIS, -17.0),
        ("calf_r", X_AXIS, 22.0),
        ("upperarm_l", X_AXIS, 39.0),
        ("upperarm_r", X_AXIS, -33.0),
    ),
    secondary_motion(26.0, -20.0),
)
DEATH_END = merge(
    rotations(
        ("root", X_AXIS, 78.0),
        ("pelvis", X_AXIS, 18.0),
        ("spine_01", X_AXIS, -24.0),
        ("spine_02", X_AXIS, -31.0),
        ("chest", X_AXIS, -23.0),
        ("neck", X_AXIS, 16.0),
        ("head", X_AXIS, 25.0),
        ("thigh_l", X_AXIS, 35.0),
        ("thigh_r", X_AXIS, -30.0),
        ("calf_l", X_AXIS, -24.0),
        ("calf_r", X_AXIS, 29.0),
        ("upperarm_l", X_AXIS, 47.0),
        ("upperarm_r", X_AXIS, -42.0),
    ),
    secondary_motion(31.0, -25.0),
)
VICTORY_RAISE = merge(
    rotations(
        ("pelvis", Y_AXIS, -4.0),
        ("spine_02", Y_AXIS, 8.0),
        ("chest", Y_AXIS, 12.0),
        ("head", Y_AXIS, 9.0),
        ("clavicle_r", Z_AXIS, 20.0),
        ("upperarm_r", Z_AXIS, 58.0),
        ("lowerarm_r", X_AXIS, -38.0),
        ("hand_r", X_AXIS, 13.0),
        ("clavicle_l", Z_AXIS, -7.0),
        ("upperarm_l", Z_AXIS, -15.0),
    ),
    digit_curl("r", 4.0, 5.0),
    secondary_motion(-11.0, 14.0),
)
VICTORY_WAVE = merge(
    VICTORY_RAISE,
    rotations(
        ("head", Y_AXIS, -7.0),
        ("lowerarm_r", X_AXIS, -12.0),
        ("hand_r", Y_AXIS, 19.0),
    ),
    secondary_motion(9.0, -11.0),
)
SPAWN_LOW = merge(
    rotations(
        ("pelvis", X_AXIS, 10.0),
        ("spine_01", X_AXIS, -14.0),
        ("spine_02", X_AXIS, -15.0),
        ("chest", X_AXIS, -7.0),
        ("head", X_AXIS, -9.0),
        ("thigh_l", X_AXIS, 25.0),
        ("thigh_r", X_AXIS, 22.0),
        ("calf_l", X_AXIS, -30.0),
        ("calf_r", X_AXIS, -28.0),
        ("upperarm_l", X_AXIS, -13.0),
        ("upperarm_r", X_AXIS, -10.0),
    ),
    secondary_motion(17.0, 16.0),
)
PRISM_POSE = merge(
    BOW_DRAW,
    rotations(
        ("pelvis", Y_AXIS, 5.0),
        ("chest", Y_AXIS, -16.0),
        ("upperarm_l", Y_AXIS, 29.0),
        ("lowerarm_l", Y_AXIS, 35.0),
    ),
    secondary_motion(-18.0, 17.0),
)
TETHER_POSE = merge(
    BOW_DRAW,
    rotations(
        ("pelvis", Y_AXIS, -5.0),
        ("spine_02", Y_AXIS, -12.0),
        ("chest", Y_AXIS, -17.0),
        ("head", Y_AXIS, -10.0),
        ("upperarm_l", Y_AXIS, 32.0),
        ("lowerarm_l", Y_AXIS, 40.0),
        ("upperarm_r", Y_AXIS, -29.0),
        ("lowerarm_r", Y_AXIS, -38.0),
    ),
    digit_curl("l", 18.0, 22.0),
    secondary_motion(-22.0, 16.0),
)
ULTIMATE_GATHER = merge(
    rotations(
        ("pelvis", X_AXIS, 3.0),
        ("spine_01", X_AXIS, -6.0),
        ("spine_02", X_AXIS, -9.0),
        ("chest", X_AXIS, -7.0),
        ("head", X_AXIS, -3.0),
        ("clavicle_l", Z_AXIS, -18.0),
        ("upperarm_l", Z_AXIS, -38.0),
        ("lowerarm_l", X_AXIS, -18.0),
        ("clavicle_r", Z_AXIS, 18.0),
        ("upperarm_r", Z_AXIS, 37.0),
        ("lowerarm_r", X_AXIS, 16.0),
    ),
    digit_curl("l", 9.0, 12.0),
    digit_curl("r", 9.0, 12.0),
    secondary_motion(-15.0, 18.0),
)
ULTIMATE_RELEASE = merge(
    rotations(
        ("pelvis", X_AXIS, -3.0),
        ("spine_01", X_AXIS, 7.0),
        ("spine_02", X_AXIS, 10.0),
        ("chest", X_AXIS, 8.0),
        ("head", X_AXIS, 5.0),
        ("clavicle_l", Z_AXIS, -31.0),
        ("upperarm_l", Z_AXIS, -65.0),
        ("lowerarm_l", X_AXIS, 20.0),
        ("clavicle_r", Z_AXIS, 28.0),
        ("upperarm_r", Z_AXIS, 59.0),
        ("lowerarm_r", X_AXIS, -23.0),
    ),
    digit_curl("l", 2.0, 3.0),
    digit_curl("r", 4.0, 5.0),
    secondary_motion(20.0, -20.0),
)


CLIP_SPECS: tuple[ClipSpec, ...] = (
    ClipSpec(
        "idle", 2.0, True, "Looping combat-ready breathing and secondary-silhouette motion.",
        ((0.0, {}), (0.25, IDLE_RISE), (0.50, {}), (0.75, IDLE_FALL), (1.0, {})),
    ),
    ClipSpec(
        "idle_variation", 3.2, True, "Looping lookout/weight-shift variation for idle variety.",
        ((0.0, {}), (0.25, IDLE_LOOK), (0.55, IDLE_SETTLE), (0.78, IDLE_RISE), (1.0, {})),
    ),
    ClipSpec(
        "walk", 1.0, True, "In-place locomotion gait for gameplay-speed walking.",
        ((0.0, WALK_LEFT), (0.25, {}), (0.50, WALK_RIGHT), (0.75, {}), (1.0, WALK_LEFT)),
        (SemanticEvent("footstep_left", 0.08, "Left-foot contact cue."), SemanticEvent("footstep_right", 0.58, "Right-foot contact cue.")),
    ),
    ClipSpec(
        "run", 0.72, True, "In-place combat run with restrained bow-side arm swing.",
        ((0.0, RUN_LEFT), (0.25, {}), (0.50, RUN_RIGHT), (0.75, {}), (1.0, RUN_LEFT)),
        (SemanticEvent("footstep_left", 0.06, "Left-foot contact cue."), SemanticEvent("footstep_right", 0.56, "Right-foot contact cue.")),
    ),
    ClipSpec(
        "turn_left", 0.42, False, "Stationary left turn using pelvis-to-head counter-rotation.",
        ((0.0, {}), (0.45, TURN_LEFT), (0.78, TURN_LEFT), (1.0, {})),
    ),
    ClipSpec(
        "turn_right", 0.42, False, "Stationary right turn using pelvis-to-head counter-rotation.",
        ((0.0, {}), (0.45, TURN_RIGHT), (0.78, TURN_RIGHT), (1.0, {})),
    ),
    ClipSpec(
        "start_run", 0.36, False, "Acceleration anticipation into the in-place run loop.",
        ((0.0, {}), (0.35, RUN_PREP), (0.72, RUN_LEFT), (1.0, RUN_LEFT)),
        (SemanticEvent("locomotion_commit", 0.52, "Gameplay may transition into the run loop."),),
    ),
    ClipSpec(
        "stop_run", 0.42, False, "Run deceleration and return to combat-ready neutral.",
        ((0.0, RUN_RIGHT), (0.32, STOP_POSE), (0.66, IDLE_FALL), (1.0, {})),
        (SemanticEvent("locomotion_stop", 0.62, "Gameplay may settle to idle."),),
    ),
    ClipSpec(
        "basic_attack", 0.76, False, "Standard Aster Arc draw, release, and recovery.",
        ((0.0, {}), (0.20, BOW_PREP), (0.52, BOW_DRAW), (0.70, BOW_RELEASE), (0.86, BOW_FOLLOW), (1.0, {})),
        (SemanticEvent("weapon_draw", 0.42, "Aster Arc reaches release tension."), SemanticEvent("projectile_release", 0.70, "Spawn the basic-attack projectile at socket_projectile."), SemanticEvent("recovery_open", 0.90, "Basic attack can return to locomotion.")),
    ),
    ClipSpec(
        "basic_attack_recovery", 0.34, False, "Optional post-shot settle used by interruption-safe attack timing.",
        ((0.0, BOW_FOLLOW), (0.46, IDLE_FALL), (1.0, {})),
        (SemanticEvent("recovery_open", 0.82, "Attack recovery completes."),),
    ),
    ClipSpec(
        "attack_variant", 0.80, False, "Side-weighted alternate bow shot for visual variety.",
        ((0.0, {}), (0.22, BOW_PREP), (0.51, ATTACK_VARIANT), (0.69, BOW_RELEASE), (0.87, BOW_FOLLOW), (1.0, {})),
        (SemanticEvent("weapon_draw", 0.40, "Alternate shot reaches tension."), SemanticEvent("projectile_release", 0.69, "Spawn the alternate-shot projectile."), SemanticEvent("recovery_open", 0.91, "Alternate attack can return to locomotion.")),
    ),
    ClipSpec(
        "charged_attack", 1.18, False, "Longer deliberate charge pose with a single strong release.",
        ((0.0, {}), (0.18, BOW_PREP), (0.46, CHARGED_DRAW), (0.70, CHARGED_DRAW), (0.82, BOW_RELEASE), (0.94, BOW_FOLLOW), (1.0, {})),
        (SemanticEvent("charge_start", 0.29, "Charged-shot presentation begins."), SemanticEvent("charge_ready", 0.68, "Charged projectile is fully primed."), SemanticEvent("projectile_release", 0.82, "Spawn the charged projectile at socket_projectile."), SemanticEvent("recovery_open", 0.95, "Charged attack can return to locomotion.")),
    ),
    ClipSpec(
        "hit_light", 0.34, False, "Short readable flinch with secondary follow-through.",
        ((0.0, {}), (0.25, HIT_LIGHT), (0.58, HIT_LIGHT), (1.0, {})),
        (SemanticEvent("hit_react", 0.25, "Presentation hit reaction peak."),),
    ),
    ClipSpec(
        "hit_heavy", 0.52, False, "Heavier torso recoil and stagger response.",
        ((0.0, {}), (0.22, HIT_HEAVY), (0.56, HIT_HEAVY), (1.0, {})),
        (SemanticEvent("hit_react", 0.22, "Presentation heavy-hit peak."), SemanticEvent("recovery_open", 0.88, "Heavy-hit recovery completes.")),
    ),
    ClipSpec(
        "knockback", 0.62, False, "In-place knockback silhouette; displacement remains gameplay-owned.",
        ((0.0, {}), (0.22, KNOCKBACK), (0.58, KNOCKBACK), (1.0, {})),
        (SemanticEvent("knockback_peak", 0.30, "Visual knockback peak; no root translation is authored."), SemanticEvent("recovery_open", 0.90, "Knockback presentation completes.")),
    ),
    ClipSpec(
        "stun", 1.0, True, "Looping low-amplitude stunned sway that can be exited by gameplay.",
        ((0.0, STUN_LEFT), (0.25, {}), (0.50, STUN_RIGHT), (0.75, {}), (1.0, STUN_LEFT)),
        (SemanticEvent("stun_loop", 0.0, "Looping visual state; gameplay owns status duration."),),
    ),
    ClipSpec(
        "death", 1.18, False, "In-place fall and held death pose; death state remains gameplay-owned.",
        ((0.0, DEATH_START), (0.20, DEATH_FALL), (0.62, DEATH_END), (1.0, DEATH_END)),
        (SemanticEvent("death_impact", 0.62, "Death presentation reaches ground pose."), SemanticEvent("death_complete", 1.0, "Animation is held; gameplay owns despawn timing.")),
    ),
    ClipSpec(
        "victory", 1.55, False, "Bow-raise and wave celebration.",
        ((0.0, {}), (0.28, VICTORY_RAISE), (0.56, VICTORY_WAVE), (0.78, VICTORY_RAISE), (1.0, {})),
        (SemanticEvent("victory_pose", 0.56, "Victory silhouette peak."),),
    ),
    ClipSpec(
        "spawn", 1.02, False, "Rise from a compact arrival stance into neutral.",
        ((0.0, SPAWN_LOW), (0.30, SPAWN_LOW), (0.66, IDLE_RISE), (1.0, {})),
        (SemanticEvent("spawn_ready", 0.88, "Hero can enter normal locomotion/idle."),),
    ),
    ClipSpec(
        "skill_01", 0.92, False, "Prism Volley multi-release presentation.",
        ((0.0, {}), (0.20, BOW_PREP), (0.44, PRISM_POSE), (0.54, BOW_RELEASE), (0.64, PRISM_POSE), (0.72, BOW_RELEASE), (0.86, BOW_FOLLOW), (1.0, {})),
        (SemanticEvent("volley_release_1", 0.50, "Spawn Prism Volley arrow one."), SemanticEvent("volley_release_2", 0.61, "Spawn Prism Volley arrow two."), SemanticEvent("volley_release_3", 0.72, "Spawn Prism Volley arrow three."), SemanticEvent("recovery_open", 0.90, "Prism Volley recovery completes.")),
    ),
    ClipSpec(
        "skill_02", 0.48, False, "Phase Step anticipation and in-place dash silhouette.",
        ((0.0, {}), (0.18, DASH_CHARGE), (0.36, DASH_PEAK), (0.60, DASH_PEAK), (0.82, STOP_POSE), (1.0, {})),
        (SemanticEvent("dash_start", 0.28, "Gameplay begins Phase Step displacement; this clip has no root translation."), SemanticEvent("dash_end", 0.66, "Gameplay ends Phase Step displacement."), SemanticEvent("recovery_open", 0.88, "Phase Step can return to locomotion.")),
    ),
    ClipSpec(
        "skill_03", 1.04, False, "Tether Snare precision aim and release.",
        ((0.0, {}), (0.20, BOW_PREP), (0.52, TETHER_POSE), (0.70, BOW_RELEASE), (0.87, BOW_FOLLOW), (1.0, {})),
        (SemanticEvent("tether_ready", 0.50, "Tether Snare aim reaches tension."), SemanticEvent("projectile_release", 0.70, "Spawn tether projectile at socket_projectile."), SemanticEvent("recovery_open", 0.91, "Tether Snare recovery completes.")),
    ),
    ClipSpec(
        "ultimate", 1.82, False, "Apex Constellation gather, constellation release, and recovery.",
        ((0.0, {}), (0.18, ULTIMATE_GATHER), (0.46, ULTIMATE_GATHER), (0.68, ULTIMATE_RELEASE), (0.82, ULTIMATE_RELEASE), (0.94, IDLE_RISE), (1.0, {})),
        (SemanticEvent("ultimate_charge", 0.36, "Apex Constellation gather reaches readable charge."), SemanticEvent("ultimate_release", 0.68, "Trigger the constellation release window."), SemanticEvent("ultimate_impact_window", 0.82, "Open the final impact presentation window."), SemanticEvent("recovery_open", 0.95, "Ultimate recovery completes.")),
    ),
)


@dataclass(frozen=True)
class AnimatedMetrics:
    filename: str
    bytes: int
    meshes: int
    nodes: int
    materials: int
    textures: int
    triangles: int
    vertices: int
    skin_joints: int
    animations: int
    channels: int
    samplers: int
    rotation_keys: int
    directly_animated_nodes: tuple[str, ...]


def axis_angle_quaternion(axis: Axis, degrees: float) -> np.ndarray:
    vector = np.asarray(axis, dtype=np.float64)
    length = float(np.linalg.norm(vector))
    if length <= 1e-8:
        raise RuntimeError("Animation axis must be non-zero.")
    vector /= length
    radians = math.radians(degrees) * 0.5
    quaternion = np.empty(4, dtype=np.float32)
    quaternion[:3] = vector * math.sin(radians)
    quaternion[3] = math.cos(radians)
    return quaternion


def normalize_quaternion_track(values: np.ndarray) -> np.ndarray:
    """Normalize and sign-stabilize a LINEAR glTF quaternion curve."""

    normalized = values.astype(np.float32, copy=True)
    lengths = np.linalg.norm(normalized, axis=1)
    if np.any(lengths < 1e-7):
        raise RuntimeError("Animation contains a zero-length quaternion.")
    normalized /= lengths[:, None]
    for index in range(1, len(normalized)):
        if float(np.dot(normalized[index - 1], normalized[index])) < 0.0:
            normalized[index] *= -1.0
    return normalized


def event_payload(spec: ClipSpec) -> list[dict[str, object]]:
    return [
        {
            "name": event.name,
            "time_s": round(spec.duration_s * event.normalized_time, 6),
            "meaning": event.meaning,
        }
        for event in spec.events
    ]


def validate_clip_specs() -> None:
    names = tuple(spec.name for spec in CLIP_SPECS)
    if names != CANONICAL_CLIPS or len(set(names)) != len(names):
        raise RuntimeError("Phase 5 clip names no longer match the canonical production contract.")
    for spec in CLIP_SPECS:
        if spec.duration_s <= 0.0 or len(spec.frames) < 2:
            raise RuntimeError(f"{spec.name}: requires positive duration and at least two keyframes.")
        times = [time for time, _ in spec.frames]
        if times[0] != 0.0 or times[-1] != 1.0 or any(second <= first for first, second in zip(times, times[1:])):
            raise RuntimeError(f"{spec.name}: normalized key times must strictly span 0 to 1.")
        animated = set().union(*(pose.keys() for _, pose in spec.frames))
        if not animated or not animated.issubset(ANIMATABLE_BONES):
            raise RuntimeError(f"{spec.name}: contains no valid animated deform/root nodes.")
        event_names = [event.name for event in spec.events]
        if len(event_names) != len(set(event_names)):
            raise RuntimeError(f"{spec.name}: duplicate semantic event names.")
        for event in spec.events:
            if not 0.0 <= event.normalized_time <= 1.0:
                raise RuntimeError(f"{spec.name}: semantic event falls outside the clip.")


def append_animation_clip(
    gltf: GLTF2,
    binary: bytearray,
    node_indices: dict[str, int],
    spec: ClipSpec,
) -> tuple[bytearray, int, int]:
    normalized_times = np.asarray([time for time, _ in spec.frames], dtype=np.float32)
    times = (normalized_times * spec.duration_s).reshape((-1, 1))
    input_accessor, binary = append_accessor(
        gltf,
        binary,
        times,
        5126,
        "SCALAR",
        f"Lyra_{spec.name}_times",
        target=None,
    )
    gltf.accessors[input_accessor].min = [float(times.min())]
    gltf.accessors[input_accessor].max = [float(times.max())]

    tracked_bones = sorted(
        set().union(*(pose.keys() for _, pose in spec.frames)),
        key=lambda bone_name: node_indices[bone_name],
    )
    animation = Animation(
        name=spec.name,
        extras={
            "phase": 5,
            "loop": spec.loop,
            "purpose": spec.purpose,
            "semantic_events": event_payload(spec),
            "root_motion": "in_place",
        },
        channels=[],
        samplers=[],
    )
    rotation_keys = 0
    for bone_name in tracked_bones:
        values = np.asarray(
            [
                axis_angle_quaternion(*pose[bone_name]) if bone_name in pose else IDENTITY_QUATERNION
                for _, pose in spec.frames
            ],
            dtype=np.float32,
        )
        values = normalize_quaternion_track(values)
        output_accessor, binary = append_accessor(
            gltf,
            binary,
            values,
            5126,
            "VEC4",
            f"Lyra_{spec.name}_{bone_name}_rotation",
            target=None,
        )
        sampler_index = len(animation.samplers)
        animation.samplers.append(
            AnimationSampler(input=input_accessor, output=output_accessor, interpolation="LINEAR")
        )
        animation.channels.append(
            AnimationChannel(
                sampler=sampler_index,
                target=AnimationChannelTarget(node=node_indices[bone_name], path="rotation"),
            )
        )
        rotation_keys += len(values)
    gltf.animations.append(animation)
    return binary, len(tracked_bones), rotation_keys


def node_name_index(gltf: GLTF2) -> dict[str, int]:
    indices = {node.name: index for index, node in enumerate(gltf.nodes or []) if node.name}
    missing = ANIMATABLE_BONES.difference(indices)
    if missing:
        raise RuntimeError(f"Phase 4 rig is missing expected animatable nodes: {sorted(missing)}")
    return indices


def decode_animation_events(animation: Animation) -> list[dict[str, object]]:
    extras = animation.extras or {}
    events = extras.get("semantic_events", [])
    if not isinstance(events, list):
        raise RuntimeError(f"{animation.name}: semantic_events metadata is not a list.")
    return events


def verify_animation_asset(path: Path) -> AnimatedMetrics:
    """Audit actual exported glTF channels, keys, quaternions, and semantic timing."""

    gltf = GLTF2().load_binary(path)
    binary = bytearray(gltf.binary_blob())
    animations = gltf.animations or []
    names = tuple(animation.name for animation in animations)
    if names != CANONICAL_CLIPS:
        raise RuntimeError(f"{path.name}: animation name/order mismatch: {names}")
    indices = node_name_index(gltf)
    expected_by_name = {spec.name: spec for spec in CLIP_SPECS}
    direct_nodes: set[str] = set()
    channel_count = 0
    sampler_count = 0
    rotation_keys = 0
    for animation in animations:
        spec = expected_by_name[animation.name]
        extras = animation.extras or {}
        if extras.get("phase") != 5 or extras.get("loop") is not spec.loop or extras.get("root_motion") != "in_place":
            raise RuntimeError(f"{path.name}/{animation.name}: malformed phase/loop/root-motion extras.")
        if decode_animation_events(animation) != event_payload(spec):
            raise RuntimeError(f"{path.name}/{animation.name}: semantic event payload mismatch.")
        if not animation.channels or len(animation.channels) != len(animation.samplers):
            raise RuntimeError(f"{path.name}/{animation.name}: channels/samplers are incomplete.")
        targets: set[str] = set()
        for channel in animation.channels:
            if channel.target.path != "rotation" or channel.target.node is None:
                raise RuntimeError(f"{path.name}/{animation.name}: only rotation channels are permitted.")
            target_name = gltf.nodes[channel.target.node].name
            if target_name not in ANIMATABLE_BONES or target_name in targets:
                raise RuntimeError(f"{path.name}/{animation.name}: invalid or duplicate rotation target {target_name}.")
            targets.add(target_name)
            direct_nodes.add(target_name)
            sampler = animation.samplers[channel.sampler]
            if sampler.interpolation != "LINEAR":
                raise RuntimeError(f"{path.name}/{animation.name}: unexpected interpolation {sampler.interpolation}.")
            times = read_accessor(gltf, binary, sampler.input).reshape(-1).astype(np.float64)
            output = read_accessor(gltf, binary, sampler.output).astype(np.float64)
            if len(times) != len(output) or len(times) < 2:
                raise RuntimeError(f"{path.name}/{animation.name}: key/input count mismatch.")
            if abs(times[0]) > 1e-6 or abs(times[-1] - spec.duration_s) > 1e-5 or np.any(np.diff(times) <= 0.0):
                raise RuntimeError(f"{path.name}/{animation.name}: invalid key time range.")
            if output.shape[1] != 4 or not np.allclose(np.linalg.norm(output, axis=1), 1.0, atol=1e-5):
                raise RuntimeError(f"{path.name}/{animation.name}: non-unit quaternion output.")
            input_accessor = gltf.accessors[sampler.input]
            output_accessor = gltf.accessors[sampler.output]
            if input_accessor.type != "SCALAR" or output_accessor.type != "VEC4" or input_accessor.componentType != 5126 or output_accessor.componentType != 5126:
                raise RuntimeError(f"{path.name}/{animation.name}: invalid animation accessor types.")
            rotation_keys += len(output)
        if targets != {bone for _, pose in spec.frames for bone in pose}:
            raise RuntimeError(f"{path.name}/{animation.name}: target set differs from clip specification.")
        if np.allclose(
            np.concatenate(
                [read_accessor(gltf, binary, animation.samplers[channel.sampler].output) for channel in animation.channels]
            ),
            IDENTITY_QUATERNION,
            atol=1e-5,
        ):
            raise RuntimeError(f"{path.name}/{animation.name}: all output keys are identity.")
        channel_count += len(animation.channels)
        sampler_count += len(animation.samplers)
    coverage = {
        "pelvis", "spine_01", "spine_02", "chest", "head",
        "upperarm_l", "lowerarm_l", "hand_l", "upperarm_r", "lowerarm_r", "hand_r",
        "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r",
        "hair_mid", "hair_tip", "mantle_mid", "mantle_tip",
        *(bone.name for bone in DEFORM_BONES if "_0" in bone.name and any(digit in bone.name for digit in ("thumb", "index", "middle", "ring", "pinky"))),
    }
    if not coverage.issubset(direct_nodes):
        raise RuntimeError(f"{path.name}: phase 5 coverage missing {sorted(coverage.difference(direct_nodes))}")

    document = load_glb_json(path)
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
    return AnimatedMetrics(
        filename=path.name,
        bytes=path.stat().st_size,
        meshes=len(document["meshes"]),
        nodes=len(document["nodes"]),
        materials=len(document["materials"]),
        textures=len(document["textures"]),
        triangles=triangles,
        vertices=vertices,
        skin_joints=len(document["skins"][0]["joints"]),
        animations=len(animations),
        channels=channel_count,
        samplers=sampler_count,
        rotation_keys=rotation_keys,
        directly_animated_nodes=tuple(sorted(direct_nodes)),
    )


def animate_asset(source: Path, destination: Path) -> AnimatedMetrics:
    if not source.is_file():
        raise RuntimeError(f"Missing Phase 4 rigged source: {source}")
    gltf = GLTF2().load_binary(source)
    if gltf.animations:
        raise RuntimeError(f"{source.name}: expected a Phase 4 source with no production animations.")
    binary = bytearray(gltf.binary_blob())
    indices = node_name_index(gltf)
    gltf.animations = []
    for spec in CLIP_SPECS:
        binary, _, _ = append_animation_clip(gltf, binary, indices, spec)
    gltf.set_binary_blob(bytes(binary))
    gltf.buffers[0].byteLength = len(binary)
    set_buffer_targets(gltf)
    destination.parent.mkdir(parents=True, exist_ok=True)
    gltf.save_binary(destination)
    command(*CLI, "validate", str(destination))
    return verify_animation_asset(destination)


def manifest_clip_data() -> list[dict[str, object]]:
    return [
        {
            "name": spec.name,
            "duration_s": spec.duration_s,
            "loop": spec.loop,
            "purpose": spec.purpose,
            "keyframe_count": len(spec.frames),
            "direct_rotation_tracks": sorted({bone for _, pose in spec.frames for bone in pose}),
            "semantic_events": event_payload(spec),
        }
        for spec in CLIP_SPECS
    ]


def write_manifest(lod0: AnimatedMetrics, lod1: AnimatedMetrics) -> None:
    payload = {
        "phase": 5,
        "asset": "Lyra Vesper production animation handoff",
        "source_assets": {
            "lod0": str(RIGGED_LOD0.relative_to(ROOT)),
            "lod1": str(RIGGED_LOD1.relative_to(ROOT)),
        },
        "animated_lod0": asdict(lod0),
        "animated_lod1": asdict(lod1),
        "animation_contract": {
            "canonical_clip_names": list(CANONICAL_CLIPS),
            "clip_count": len(CLIP_SPECS),
            "channels": "Standard glTF 2.0 LINEAR rotation channels targeting Phase 4 hierarchy nodes.",
            "root_motion": "in_place; no translation animation channel is authored.",
            "semantic_events": "Per-clip events are stored in glTF animation extras and mirrored below for runtime tooling.",
            "clips": manifest_clip_data(),
        },
        "phase_boundary": {
            "godot_import": "Not yet verified — Phase 6 owns real engine import, AnimationTree, and gameplay-event integration.",
            "gameplay_motion": "Not embedded — movement and dash displacement remain gameplay-authoritative.",
            "validation_evidence": "Generated by source/render_phase5_validation.py into validation/animation_report.json and renders/.",
        },
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    validate_clip_specs()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    lod0 = animate_asset(RIGGED_LOD0, LOD0_OUTPUT)
    lod1 = animate_asset(RIGGED_LOD1, LOD1_OUTPUT)
    if lod0.triangles != 11_496 or lod1.triangles != 5_843:
        raise RuntimeError("Phase 5 export unexpectedly changed the Phase 3/4 triangle contract.")
    if lod0.vertices != 8_431 or lod1.vertices != 4_834:
        raise RuntimeError("Phase 5 export unexpectedly changed the Phase 3/4 vertex contract.")
    write_manifest(lod0, lod1)
    print("Phase 5 animated assets exported")
    print(f"  LOD0: {lod0.animations} clips, {lod0.channels} rotation channels, {lod0.rotation_keys} keys, {lod0.bytes} bytes")
    print(f"  LOD1: {lod1.animations} clips, {lod1.channels} rotation channels, {lod1.rotation_keys} keys, {lod1.bytes} bytes")


if __name__ == "__main__":
    main()
