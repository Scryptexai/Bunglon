# Lyra Vesper Phase 5 → Phase 6 Godot Integration Handoff

> Historical Phase 5 handoff. Phase 6 is now implemented and engine-validated;
> see [`../heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md`](../heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md)
> for the active adapter, documented importer conversion, and recorded result.

## What Phase 6 received

| Contract item | Delivered location | Phase 6 use |
|---|---|---|
| Primary animated asset | `lyra_vesper_animated.glb` | Import as the LOD0 Lyra visual. |
| Matching lower-density visual | `lyra_vesper_animated_lod1.glb` | Attach to the established LOD selection policy. |
| Clip names/timings/events | `animation_manifest.json`, `ANIMATION_SPECIFICATION.md` | Map imported takes to state machine and semantic signals. |
| Skeleton / attachment contract | Phase 4 hierarchy preserved in both GLBs | Resolve right-hand weapon/projectile and camera/aim anchors. |
| Asset-level evidence | `validation/animation_report.json`, `renders/` | Baseline for import and visual regression review. |

## Required import checks in a real Godot 4.x editor

1. Import each GLB and confirm that `AnimationPlayer` exposes all 23 canonical clip names in their documented order or that the importer mapping preserves those names explicitly.
2. Confirm that every clip drives the imported skeleton rather than creating a detached duplicate transform hierarchy. Verify `rotation` curves use the Phase 4 bone names.
3. Confirm the three retained PBR material groups (`M_Lyra_OpaqueAtlas`, `M_Lyra_LumenEnergy`, `M_Lyra_AuroraMantle`), eight embedded textures, normal/tangent response, transparency/double-sided mantle setup, and no missing texture warnings.
4. Confirm LOD0/LOD1 have matching skeletons, helpers, clips, durations, semantic metadata mapping, and transition behavior before allowing an LOD swap while animated.
5. Inspect idle, run, both turns, start/stop, basic/charged attacks, all skills, ultimate, hit reactions, death, spawn, and victory from gameplay camera distance as well as close review distance.
6. Inspect shoulders/elbows/wrists/fingers, Aster Arc grip, comet-tail hair, mantle, armor islands, and death pose for import-time deformation or interpolation differences.
7. Resolve and exercise the imported equivalents of `socket_weapon`, `socket_projectile`, `socket_camera_body`, `socket_camera_chest`, `socket_camera_head`, and `socket_aim`. In particular, verify projectile origin at every bow-release semantic window.

## Presentation adapter responsibilities

Phase 6 introduced `HeroPresentationAdapter` as the presentation boundary, consistent with [`../ARCHITECTURE.md`](../ARCHITECTURE.md), without folding it into ability or combat scripts.

```text
HeroPresentationAdapter
├── owns imported Lyra visual, AnimationPlayer, AnimationTree mapping
├── resolves skeleton/helper attachment nodes
├── requests named visual clips from gameplay intent
├── translates imported clip metadata/markers into semantic presentation signals
├── exposes socket_projectile/camera/aim transforms to callers
└── drives presentation-only VFX, audio, and cosmetic material variants
```

Gameplay systems remain responsible for movement, targeting, projectile simulation, hit tests, damage, status, energy, cooldowns, and state validity. The adapter may request a visual `skill_02` at Phase Step start, but it must not move a `CharacterBody3D` from clip translation—there is none—and it must not create an authoritative hit because a `projectile_release` marker occurs.

## Initial named-clip mapping target

| Gameplay/presentation intent | Phase 5 clip | Timing handoff |
|---|---|---|
| Ready / idle variation | `idle`, `idle_variation` | Loop by adapter policy. |
| Locomotion | `walk`, `run`, `start_run`, `stop_run`, `turn_left`, `turn_right` | Gameplay controls speed/direction; footsteps are optional presentation cues. |
| Basic fire | `basic_attack`, optionally `basic_attack_recovery` or `attack_variant` | On `projectile_release`, use the current `socket_projectile` transform for presentation/projectile spawn request. |
| Charged fire | `charged_attack` | Present charge start/ready and release; gameplay validates charge state independently. |
| Skill 01 / Prism Volley | `skill_01` | Consume each of the three `volley_release_*` events separately. |
| Skill 02 / Phase Step | `skill_02` | Observe `dash_start`/`dash_end`; movement controller retains dash distance and collision. |
| Skill 03 / Tether Snare | `skill_03` | Use `tether_ready` and `projectile_release` as presentation cues only. |
| Ultimate / Apex Constellation | `ultimate` | Use charge/release/impact/recovery windows for VFX/audio/camera, not damage authority. |
| Lifecycle / hit state | `hit_light`, `hit_heavy`, `knockback`, `stun`, `death`, `spawn`, `victory` | Game state owns interruption, control lock, respawn/despawn, and looping. |

## Phase 6 event ingestion decision

The GLBs store semantic events in `animation.extras.semantic_events`. The real Godot importer check established that arbitrary extras should not be assumed to become engine markers, so the adapter uses the verified third mechanism: it loads `animation_manifest.json` as timing data while matching each entry against the imported `AnimationPlayer` clip duration and rotation-target contract.

The selected mechanism preserves clip name, event name, `time_s`, and non-authoritative semantics. Its engine smoke test covers interruption/restart/LOD swap protection and confirms an already-passed release marker does not replay across an LOD swap. Phase 9 additionally reads the matching manifest timestamps at accepted ability casts to initialize separate authoritative gameplay timers; it does not subscribe to those emitted visual signals.

## Phase 6 gate result

The real Godot 4.3 gate passed: animation playback for all 23 clips, `AnimationTree` transitions, helper attachment following, semantic event timing/mapping, material/texture import, replacement of the primitive path in an isolated visual scene, and player/AI presentation requests through the adapter boundary. The importer conversion and exact commands/results are documented in [`../heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md`](../heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md).

## Explicit non-claims from Phase 5

Phase 5 did **not** claim that editor/runtime checks occurred; Phase 6 subsequently supplied the documented Godot import/runtime evidence. Neither phase claims mobile performance, Android builds, multiplayer/replay synchronization, final VFX/SFX, or final gameplay balance. Those remain later roadmap work.
