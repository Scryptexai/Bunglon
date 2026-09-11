# ARCHITECTURE — Lyra Vesper Hero

This architecture supports the production roadmap without coupling game systems to the final visual asset.

## Stage boundary

The project has completed **Phase 2 mesh/material handoff and Phase 3 topology/game-readiness** for the revised roadmap. The real non-primitive runtime GLBs now have optimization, packed UVs, normal/tangent streams, and LOD policy; they still need Phase 4 rigging, Phase 5 animation, and Phase 6 Godot import verification. Existing gameplay code remains a prototype/reference implementation until that real-asset integration is validated. The target architecture below is the contract for it.

## Runtime composition

```text
HeroCharacter : CharacterBody3D                 # composition root
├── Physics
│   ├── BodyCollision : CollisionShape3D
│   ├── Hurtbox : Area3D
│   ├── HitboxService : Area3D / query service
│   └── Detection : Area3D
├── Presentation
│   ├── CharacterModel : imported Lyra GLB instance
│   │   ├── Skeleton3D
│   │   ├── Meshes + PBR materials
│   │   └── socket_weapon / socket_projectile
│   ├── WeaponModel : imported bow instance if separate
│   ├── AnimationPlayer
│   ├── AnimationTree
│   ├── VFX
│   └── Audio
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
              semantic events → Animation / VFX / Audio
```

### Rules

1. **Presentation is replaceable.** Gameplay sees sockets and semantic animation events, never mesh parts or material slots.
2. **Combat detection is physical/data-driven.** A visual mesh cannot be the source of a hit or damage calculation.
3. **Input is replaceable.** Player, AI, and future replay/network code create the same command shape.
4. **Stats are data.** Hero level, equipment, buffs, skill scaling, and damage modifiers live in data/component layers, not in animation or model scripts.
5. **Animation timing has an adapter.** Imported clips publish draw/release/hit/recovery events; animation changes cannot silently desynchronize damage.

## Real-asset integration adapter

The imported GLB should not contain gameplay scripts. Instead, `HeroPresentationAdapter` owns these responsibilities:

| Adapter responsibility | Source | Consumer |
|---|---|---|
| Locate Skeleton3D / AnimationPlayer | Imported GLB | Animation system |
| Resolve `socket_projectile` | GLB helper bone/node | BasicAttack projectile origin |
| Resolve camera anchors | GLB helpers or mapped bones | External camera / aim system |
| Publish animation events | Imported clip markers / timeline | Combat and abilities |
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
