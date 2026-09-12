# Lyra Vesper Phase 5 → Phase 6 Godot Integration Handoff

## What Phase 6 receives

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

The Phase 6 adapter should be introduced as a presentation boundary, consistent with [`../ARCHITECTURE.md`](../ARCHITECTURE.md), not folded into ability or combat scripts.

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

## Event ingestion choices to decide in Phase 6

The GLBs store semantic events in `animation.extras.semantic_events`. Godot import behavior for arbitrary glTF animation extras must be tested rather than assumed. Choose one verified mechanism:

1. extract the extras into a generated Godot `.tres` / mapping resource at import time;
2. mirror each event as an AnimationPlayer method/call marker during a controlled editor import step; or
3. load `animation_manifest.json` as the adapter's source of timing data while matching it against the imported AnimationLibrary.

Whichever mechanism is selected must preserve clip name, event name, `time_s`, and documented non-authoritative semantics. It must be unit/integration tested against the imported AnimationPlayer duration and must tolerate interruption/restart/LOD swap without duplicate gameplay damage.

## Definition of done for the next gate

Phase 6 is complete only after a real Godot 4.x import proves: animation playback, `AnimationTree` transitions, helper attachment following, semantic event timing/mapping, proper material import, asset replacement of the primitive prototype in an isolated visual scene, and player/AI presentation requests working through the adapter boundary. It must document any importer conversion needed to preserve the GLB event contract.

## Explicit non-claims from Phase 5

Phase 5 does **not** claim that any of the above editor/runtime checks occurred. It also does not claim live gameplay collision alignment, mobile performance, Android builds, multiplayer/replay synchronization, final VFX/SFX, or player/AI behavior validation. Those are intentionally left for later roadmap phases.
