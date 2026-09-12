# Phase 8 — Basic Attack & Projectile Authority

## Gate status

**Complete at the real Godot 4.3 basic-attack combat gate.** This phase verifies
Lyra's ordinary marksman attack against live `HeroCharacter` and `TrainingDrone`
scenes: hostile target qualification, animation-aligned gameplay windup, imported
socket placement, one projectile, `Hurtbox`/`DamageReceiver` damage delivery,
recovery, and target-loss cancellation.

It is deliberately a basic-attack gate, not a claim that the three abilities,
ultimate radial behavior, full targeting policy, navigation, balance, multiplayer,
or Android QA is complete.

## Authority contract

```text
TargetingComponent / direct request
                │ hostile + in-range validation
                ▼
            BasicAttack
    prepare → gameplay windup timer → spawn one EnergyProjectile
                                            │
                    imported socket_projectile supplies only spawn transform
                                            │
                                      Hurtbox → DamageReceiver → Health

HeroPresentationAdapter semantic projectile_release
                         │
                         └── VFX / audio only; never an extra projectile or DamageEvent
```

`BasicAttack` now validates **every** supplied target itself, even when a caller
passes a preferred target directly. A friendly, invalid, or out-of-range target
cannot consume cooldown or create a pending projectile. This preserves the
component's authority boundary rather than assuming every future input/AI/replay
caller has already performed the same check.

After the gameplay timer reaches the manifest-aligned release time,
`BasicAttack` calls `HeroCharacter.spawn_projectile()` once. The new
`projectile_spawned` signal exposes that authoritative event to observers without
allowing presentation code to produce a second projectile. `attack_fired` is now
emitted only when that projectile was actually constructed. `EnergyProjectile`
then performs hostile-only impact resolution through `Hurtbox` and
`DamageReceiver`; it never edits a health value directly.

## Engine evidence

Starting from an imported Godot project, run:

```bash
GODOT_BIN=/tmp/godot-src-4.3/bin/godot.linuxbsd.editor.x86_64
"$GODOT_BIN" --headless --path . --script res://tests/godot/phase8_basic_attack_smoke.gd
```

The recorded Godot 4.3 run exited `0` and printed
`PHASE8_BASIC_ATTACK_SMOKE result=PASS`. It used a physics floor, one live imported
Lyra, a nearer friendly drone, an in-range hostile drone, a far hostile drone, and
a target removed during windup. It verifies:

1. targeting chooses the nearest hostile while excluding a nearer friendly;
2. direct friendly/far attack requests fail without starting cooldown;
3. a valid attack starts the authoritative windup and produces exactly one basic
   payload/projectile at the current imported `socket_projectile` position;
4. the imported `basic_attack` release marker emits exactly one cosmetic event but
   does not duplicate the gameplay projectile;
5. the projectile follows the live `Hurtbox` → `DamageReceiver` path, damages only
   the hostile, and lets gameplay/visual recovery complete independently;
6. target loss during windup emits cancellation and cannot leave a stale projectile
   or `attack_fired` report behind.

As with Phase 6–7, the headless sandbox reports known rendererless dummy-mesh
diagnostics. The passing result is engine/runtime logic evidence, not GPU-rendered
visual, input-latency, or mobile-performance evidence.

## Deliberate boundary and next work

- Phase 9 should independently validate each ability's cast/action/recovery,
  energy/cooldown, status, interruption, and imported-animation alignment.
- Later targeting/AI/world gates still need multi-target priorities, target-death
  reacquisition, obstacle/navigation, projectile collision edge cases, and AI
  decision behavior under actual encounters.
- Android device profiling, full visual review, final VFX/SFX mix, balance, replay,
  networking, accessibility, and packaged-delivery QA remain open roadmap work.
