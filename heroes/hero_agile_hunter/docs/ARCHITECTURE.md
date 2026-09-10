# Architecture & Dependency Notes

## Hero scene tree

```text
HeroCharacter : CharacterBody3D                # composition root only
├── BodyCollision : CollisionShape3D            # direct child required by Godot physics
├── Visual : HeroVisual
│   └── CharacterModel
│       ├── Skeleton : Skeleton3D
│       ├── Weapon : Node3D
│       │   └── ProjectileOrigin : Marker3D
│       └── Accessories : Node3D
├── Animation : HeroAnimationDriver
│   ├── AnimationPlayer
│   └── AnimationTree
├── Movement : MovementController
├── Combat
│   ├── BasicAttack
│   ├── AbilityController
│   ├── Targeting : TargetingComponent
│   └── DamageReceiver
├── Abilities
│   ├── Passive : SlipstreamPassive
│   ├── Skill01 : PrismVolleyAbility
│   ├── Skill02 : PhaseStepAbility
│   ├── Skill03 : TetherSnareAbility
│   └── Ultimate : ApexConstellationAbility
├── Stats : StatsComponent → HeroStats Resource
├── Health : HealthComponent
├── Energy : EnergyComponent
├── Status : StatusComponent
├── Team : TeamComponent
├── Hurtbox : Area3D → CollisionShape3D
├── Hitbox : Area3D → CollisionShape3D
├── Detection : Area3D → CollisionShape3D
├── VFX
│   ├── BodyEffects
│   ├── AttackEffects
│   ├── SkillEffects
│   └── DeathEffects
├── Audio
│   ├── Voice
│   ├── Attack
│   ├── Skill
│   └── Movement
├── CameraTarget
│   ├── Body
│   ├── Chest
│   ├── Head
│   └── AimPoint
└── Control
    └── CharacterController
        ├── PlayerInput : PlayerInputSource
        └── AIInput : AIInputSource
```

`BodyCollision`, `Hurtbox`, `Hitbox`, dan `Detection` sengaja langsung berada di bawah root. `CollisionShape3D` harus menjadi child efektif dari `CollisionObject3D`/`Area3D` agar engine mendaftarkan shape dengan benar. Ini adalah adaptasi node hierarchy terhadap invariant Godot, bukan pencampuran concern.

## Data/event flow

```text
PlayerInputSource | AIInputSource | external/replay packet
                         ↓ CharacterCommand
                    CharacterController
                  ↙                       ↘
        MovementController         Targeting + BasicAttack/AbilityController
                                           ↓
                               EnergyProjectile / Hitbox
                                           ↓
                                      Hurtbox (Area3D)
                                           ↓
                               DamageReceiver ← DamageEvent
                                  ↓       ↓       ↓
                            Health   Status   Animation/VFX/Audio events
```

## Significant additional subsystems

| Subsystem | Reason it exists |
|---|---|
| `EnergyComponent` | Mana/energy has a lifecycle (spend, regen, insufficient event) distinct from generic stats. |
| `StatusComponent` | Root, slow, phase and future buff/debuff behavior should not fork movement/damage scripts. |
| `TeamComponent` | Targeting needs faction filtering without assuming a player or AI owner. |
| `CharacterCommand` / `InputSource` | Makes player, AI, network, replay, and tests produce the same intent packet. |
| `DamageEvent` | Carries source, amount, damage type, critical state, source IDs, modifiers, metadata, and status payload for extension without changing public calls. |
| `CameraTarget` | Gives camera systems named body/chest/head/aim anchors without making camera a combat dependency. |

## Boundary rules

1. **Visual does not calculate damage.** `HeroVisual` and `HeroAnimationDriver` only consume semantic state/events.
2. **Attack does not select targets.** `BasicAttack` asks `TargetingComponent` for a target; AI and player can both supply selection policy.
3. **Projectiles do not directly edit HP.** They call `Hurtbox`, which calls `DamageReceiver`, which owns mitigation and `HealthComponent` dispatch.
4. **Abilities do not read Input.** `CharacterController` submits a slot/aim request; `HeroAbility` owns cast/action/recovery/cooldown.
5. **Audio/VFX are event sinks.** Their failures or replacement assets cannot change combat resolution.

## Expansion points

- Add equipment/talent buffs through `StatsComponent.set_flat_modifier` / `set_percent_modifier` using a source key.
- Add status resolver categories in `StatusComponent` rather than adding conditionals to every ability.
- Implement network authority by supplying `CharacterCommand` from an external input source and replicating `DamageEvent` / ability activation at the game layer.
- Replace `TrainingDrone` with any combatant that implements `get_team_id`, `get_damage_receiver`, and optionally `get_aim_position`.
