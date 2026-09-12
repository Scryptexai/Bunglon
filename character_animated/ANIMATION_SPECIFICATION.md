# Lyra Vesper Phase 5 — Animation Specification and Timing Contract

## Scope and source

The Phase 5 exports are baked action data for the existing Phase 4 `LyraVesper_DeformRig`, not replacement geometry. LOD0 and LOD1 use the same 23 animation names, skeletal target names, timing, sampler interpolation, event payloads, loop policy, and root-motion policy. Only their inherited mesh density differs.

All action curves are core glTF 2.0 `animation.samplers` + `animation.channels`:

- target property: `rotation` only;
- output type: float `VEC4` unit quaternion;
- interpolation: `LINEAR`;
- input time range: `0.0` through each clip duration;
- clip metadata: `animation.extras.phase`, `loop`, `purpose`, and `root_motion`;
- semantic windows: `animation.extras.semantic_events` when a clip has events. An absent field means no events, rather than an invalid empty payload.

## In-place root-motion policy

All Phase 5 movement is **in-place**. There are no glTF `translation` animation channels—on `root` or any other node. This includes `walk`, `run`, `start_run`, `stop_run`, `skill_02` / Phase Step, knockback, and death. `root` may rotate in the visual death fall, but its position is unchanged.

`MovementController` and ability gameplay remain authoritative for world displacement, dash distance, knockback resolution, collision, hit detection, and damage. The exported time/event values coordinate presentation; they do not authorize a mesh curve to move a `CharacterBody3D` or decide a gameplay result.

## Authored-motion principles

- **Locomotion:** alternating legs/feet/toes, controlled bow-side arm swing, torso counter-motion, and visible secondary hair/mantle response. Walk/run loops repeat matching first/last poses.
- **Transitions and turns:** preparatory body shift, commitment, and settle instead of a one-key rotation.
- **Bow attacks:** aimed torso/shoulder layering; both hands and compact digit chains participate in preparation, tension, release, and recovery. Aster Arc remains associated with the inherited `hand_r → socket_weapon → socket_projectile` hierarchy.
- **Abilities:** Prism Volley differentiates three release beats, Phase Step provides a crouch/launch silhouette without visual root displacement, Tether Snare creates a longer aim tension, and Apex Constellation has readable gather/release/impact/recovery phases.
- **Secondary silhouette:** `hair_mid`, `hair_tip`, `mantle_mid`, and `mantle_tip` are purposefully keyed across the action set rather than left as static attachments.
- **Reactions:** light/heavy hit, knockback, stun, death, spawn, and victory each have their own readable timing and recovery/hold policy.

## Canonical clips and semantic timings

`time_s` is measured from the start of the named clip. “Loop” means the intended playback policy recorded in clip extras; core glTF itself does not own a universal playback-loop flag.

| # | Clip | Duration | Playback | Presentation intent | Semantic event(s), `time_s` |
|---:|---|---:|---|---|---|
| 1 | `idle` | 2.00 s | loop | Combat-ready breathing and subtle secondary silhouette. | — |
| 2 | `idle_variation` | 3.20 s | loop | Lookout/weight-shift idle variation. | — |
| 3 | `walk` | 1.00 s | loop | In-place walk. | `footstep_left` 0.080; `footstep_right` 0.580 |
| 4 | `run` | 0.72 s | loop | In-place combat run. | `footstep_left` 0.0432; `footstep_right` 0.4032 |
| 5 | `turn_left` | 0.42 s | once | Stationary pelvis-to-head left turn. | — |
| 6 | `turn_right` | 0.42 s | once | Stationary pelvis-to-head right turn. | — |
| 7 | `start_run` | 0.36 s | once | Acceleration anticipation into run. | `locomotion_commit` 0.1872 |
| 8 | `stop_run` | 0.42 s | once | Deceleration and combat-ready settle. | `locomotion_stop` 0.2604 |
| 9 | `basic_attack` | 0.76 s | once | Aster Arc draw, release, recovery. | `weapon_draw` 0.3192; `projectile_release` 0.5320; `recovery_open` 0.6840 |
| 10 | `basic_attack_recovery` | 0.34 s | once | Optional interruption-safe post-shot settle. | `recovery_open` 0.2788 |
| 11 | `attack_variant` | 0.80 s | once | Side-weighted alternate bow shot. | `weapon_draw` 0.3200; `projectile_release` 0.5520; `recovery_open` 0.7280 |
| 12 | `charged_attack` | 1.18 s | once | Deliberate charged draw and strong release. | `charge_start` 0.3422; `charge_ready` 0.8024; `projectile_release` 0.9676; `recovery_open` 1.1210 |
| 13 | `hit_light` | 0.34 s | once | Short flinch. | `hit_react` 0.0850 |
| 14 | `hit_heavy` | 0.52 s | once | Stronger torso recoil/stagger. | `hit_react` 0.1144; `recovery_open` 0.4576 |
| 15 | `knockback` | 0.62 s | once | In-place knockback silhouette. | `knockback_peak` 0.1860; `recovery_open` 0.5580 |
| 16 | `stun` | 1.00 s | loop | Exit-capable low-amplitude stunned sway. | `stun_loop` 0.0000 |
| 17 | `death` | 1.18 s | once / hold end | In-place fall to held death pose. | `death_impact` 0.7316; `death_complete` 1.1800 |
| 18 | `victory` | 1.55 s | once | Bow raise and wave silhouette. | `victory_pose` 0.8680 |
| 19 | `spawn` | 1.02 s | once | Compact arrival stance rising to neutral. | `spawn_ready` 0.8976 |
| 20 | `skill_01` | 0.92 s | once | Prism Volley, three differentiated arrow beats. | `volley_release_1` 0.4600; `volley_release_2` 0.5612; `volley_release_3` 0.6624; `recovery_open` 0.8280 |
| 21 | `skill_02` | 0.48 s | once | Phase Step launch/dash silhouette. | `dash_start` 0.1344; `dash_end` 0.3168; `recovery_open` 0.4224 |
| 22 | `skill_03` | 1.04 s | once | Tether Snare precision aim/release. | `tether_ready` 0.5200; `projectile_release` 0.7280; `recovery_open` 0.9464 |
| 23 | `ultimate` | 1.82 s | once | Apex Constellation gather/release/recovery. | `ultimate_charge` 0.6552; `ultimate_release` 1.2376; `ultimate_impact_window` 1.4924; `recovery_open` 1.7290 |

## Semantic-event use contract

The future Phase 6 presentation adapter should decode the event extras (or mirror this manifest into engine-native animation markers) and emit a semantic signal for gameplay/presentation consumers. The adapter must preserve the following separation:

| Event family | Presentation handoff | Gameplay ownership retained outside the animation |
|---|---|---|
| `projectile_release`, `volley_release_*` | Spawn/muzzle flash point is `socket_projectile` at the matching sampled pose. | Projectile authority, direction, collision, damage, and networking/replay truth. |
| `weapon_draw`, `charge_*`, `tether_ready`, `ultimate_*` | VFX/SFX/camera presentation windows. | Cooldowns, energy costs, target validation, hit result, and ability state. |
| `dash_start`, `dash_end`, `locomotion_*`, `knockback_peak` | Timing cues for visual phase changes. | CharacterBody3D velocity/displacement and status resolution. |
| `footstep_*`, `hit_react`, `victory_pose`, `spawn_ready`, `death_*`, `recovery_open` | Audio/VFX/animation-state transition cues. | Grounding, damage reception, respawn/despawn, control lock, and combat cancellation rules. |

No semantic marker is a collision shape, hitbox, damage calculation, or authoritative movement command.

## Socket continuity contract

The skeleton preserves the Phase 4 relationships:

```text
hand_r → socket_weapon → socket_projectile
pelvis → socket_camera_body
chest → socket_camera_chest, socket_aim
head → socket_camera_head
```

The Phase 5 validator samples every exported semantic-event time and checks that the world transforms produced by the animation still equal the inherited parent transform multiplied by the exported rest-relative helper transform. It also checks a stationary root position at those times. This establishes asset-level continuity only; actual Godot `BoneAttachment3D` / imported-node behavior remains a Phase 6 test.

## LOD parity contract

Animation names/order, clip extras, durations, event payloads, number/targets of direct rotation tracks, times, and quaternion values match across LOD0 and LOD1. The LOD split retains the Phase 4 topology budget only: 11,496 / 8,431 LOD0 triangles/vertices and 5,843 / 4,834 LOD1 triangles/vertices.
