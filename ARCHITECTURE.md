# ARCHITECTURE — Lyra Vesper Hero

This architecture supports the production roadmap without coupling game systems to the final visual asset.

## Stage boundary

The project has completed **Phase 2 mesh/material, Phase 3 topology/game-readiness, Phase 4 rigging/skinning, Phase 5 authored animation export, Phase 6 Godot integration, Phase 7 controller/command integration, Phase 8 basic-attack/projectile authority, and Phase 9 ability lifecycle/timing integration** for the revised roadmap. The active non-primitive LOD GLBs retain optimization, packed UVs, normal/tangent streams, a 48-deform-joint / 54-palette-joint skin, inverse-bind matrices, named weapon/projectile/camera/aim helpers, and 23 baked action clips with an in-place semantic timing contract. `HeroPresentationAdapter` imports them below `HeroCharacter/Visual`, validates the LOD contract, supplies an imported `AnimationPlayer`/runtime `AnimationTree`, and exposes the helpers without making the visual asset gameplay authority.

The asset-level action/event details are in [`character_animated/ANIMATION_SPECIFICATION.md`](character_animated/ANIMATION_SPECIFICATION.md). The implemented importer conversion and real-engine evidence are recorded in [`heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md`](heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md).

## Runtime composition

```text
HeroCharacter : CharacterBody3D                 # composition root
├── Physics
│   ├── BodyCollision : CollisionShape3D
│   ├── Hurtbox : Area3D
│   ├── HitboxService : Area3D / query service
│   └── Detection : Area3D
├── Visual : HeroPresentationAdapter
│   └── ActiveImportedVisual : validated Lyra LOD0 or LOD1 GLB instance
│       ├── Skeleton3D + authored skinned meshes/PBR materials
│       ├── AnimationPlayer (23 imported clips)
│       ├── AnimationTree (adapter-owned runtime state machine)
│       └── socket_weapon / socket_projectile / camera / aim BoneAttachment3D helpers
├── VFX
└── Audio
├── Gameplay
│   ├── Stats
│   ├── Health
│   ├── Energy
│   ├── Status
│   ├── MovementController
│   ├── BasicAttack
│   ├── AbilityController
│   └── DamageReceiver
├── Abilities
│   ├── Passive
│   ├── Skill01
│   ├── Skill02
│   ├── Skill03
│   └── Ultimate
├── Targeting
├── Control
│   ├── CharacterController
│   ├── PlayerInputSource
│   ├── AIInputSource
│   └── ExternalInputSource (network/replay boundary)
└── CameraTarget
    ├── Body
    ├── Chest
    ├── Head
    └── AimPoint
```

## Dependency direction

```text
Input source (player / AI / network / replay)
                  ↓ CharacterCommand
             CharacterController
                ↙           ↘
       MovementController    Targeting + combat request
                                  ↓
                         BasicAttack / AbilityController
                                  ↓
                     Projectile or gameplay Hitbox query
                                  ↓
                  Hurtbox → DamageReceiver → Health / Status
                                  ↓
          HeroAnimationDriver → HeroPresentationAdapter → imported AnimationTree
                                                    ↓
                              presentation-only semantic events → VFX / Audio
```

### Rules

1. **Presentation is replaceable.** Gameplay sees read-only imported sockets and semantic presentation signals, never mesh parts or material slots.
2. **Combat detection is physical/data-driven.** A visual mesh cannot be the source of a hit or damage calculation.
3. **Input is replaceable.** Player, AI, and future replay/network code create the same command shape.
4. **Stats are data.** Hero level, equipment, buffs, skill scaling, and damage modifiers live in data/component layers, not in animation or model scripts.
5. **Animation timing has an adapter.** Imported clips publish de-duplicated draw/release/hit/recovery presentation signals; `BasicAttack` and abilities retain the independent authoritative gameplay timelines.
6. **Commands are snapshots.** `CharacterController` accepts one active source per physics tick, normalizes planar move/aim, and clears stale touch/external intent when control ownership changes. It never becomes an alternate combat implementation.
7. **Basic attacks own their gate.** `BasicAttack` independently rejects friendly/invalid/out-of-range direct targets, spawns one gameplay projectile at the imported socket after its gameplay timer, and routes impact only through `Hurtbox` / `DamageReceiver`.
8. **Abilities own their timers.** `HeroAbility` queries manifest timing once at accepted cast, then runs cast/action/recovery timers and effect execution itself. Adapter semantic signals remain VFX/audio facts, never ability triggers.

See [`heroes/hero_agile_hunter/docs/PHASE_7_CONTROLLER_INTEGRATION.md`](heroes/hero_agile_hunter/docs/PHASE_7_CONTROLLER_INTEGRATION.md) for the engine-validated source-switch/external-packet contract, [`heroes/hero_agile_hunter/docs/PHASE_8_BASIC_ATTACK_INTEGRATION.md`](heroes/hero_agile_hunter/docs/PHASE_8_BASIC_ATTACK_INTEGRATION.md) for attack authority evidence, and [`heroes/hero_agile_hunter/docs/PHASE_9_ABILITY_TIMING.md`](heroes/hero_agile_hunter/docs/PHASE_9_ABILITY_TIMING.md) for ability timing evidence.

## Real-asset integration adapter

The imported GLBs contain no gameplay scripts. `HeroPresentationAdapter` owns these responsibilities:

| Adapter responsibility | Source | Consumer |
|---|---|---|
| Locate Skeleton3D / AnimationPlayer | Imported GLB | Animation system |
| Resolve `socket_projectile` | GLB helper bone/node | BasicAttack projectile origin |
| Resolve camera anchors | GLB helpers or mapped bones | External camera / aim system |
| Publish animation events | Manifest-aligned imported clip timeline | Presentation VFX / audio only |
| Apply presentation-only VFX | VFX scenes | Visual feedback only |
| Bind material variants | PBR material resources | Cosmetics / skin system later |

If a source DCC asset changes its bone names, only this adapter/mapping is updated. `MovementController`, `DamageEvent`, abilities, targeting, and AI must remain untouched.

## AI compatibility

`AIInputSource` is intentionally an input producer, not an alternate character type. It handles target acquisition policy, chase/retreat intent, and skill-request heuristics. The same `CharacterController`, `MovementController`, `BasicAttack`, and `AbilityController` execute those requests for player and AI characters.

## Mobile architecture decisions

- One imported hero model with LOD selection; no per-frame dynamic model rebuilding.
- Shared PBR materials and texture atlases where practical.
- Pooled projectiles/VFX in production instead of repeated scene allocation.
- No dynamic lights per hero; use emissive materials and inexpensive effects.
- Collision shape complexity remains simple even when the visual mesh becomes detailed.
- Audio is semantic-event routed and uses a bounded number of spatial players.

## Validation ownership

| Layer | Validation owner |
|---|---|
| Mesh, UV, rig, skin, source animation | Blender/DCC validation scene |
| GLB import and material/animation discovery | Godot import smoke test |
| Movement/combat/abilities/AI | Godot demo and automated gameplay tests |
| Mobile cost | Android profiling pass |
| Visual consistency/readability | Phase 15 art/gameplay review |
