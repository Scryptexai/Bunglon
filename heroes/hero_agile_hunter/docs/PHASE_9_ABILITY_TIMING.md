# Phase 9 — Ability Lifecycle & Authored Timing

## Gate status

**Complete at the real Godot 4.3 ability-lifecycle gate.** This phase integrates
Lyra's four active abilities with the validated Phase 5 timing contract while
preserving gameplay authority outside the imported GLB:

- **Q — Prism Volley:** three independently scheduled energy arrows;
- **E — Phase Step:** directional dash and short phase immunity;
- **R — Tether Snare:** one tether projectile with root status payload;
- **F — Apex Constellation:** movement/basic-attack lock, three shots, and a
  final radial slow/damage payload.

This is not a claim that all targeting policy, navigation, balance, networking,
Android input/device performance, or GPU visual QA is final.

## Timing architecture

`HeroAbility` has an explicit separation between the **source of a timing value**
and the **authority that acts on it**:

```text
animation_manifest.json → HeroPresentationAdapter / HeroAnimationDriver lookup
                                      │ queried once at accepted cast
                                      ▼
                          HeroAbility private gameplay timers
                                      │
                       projectile / dash / status / cooldown lifecycle

HeroPresentationAdapter semantic signal → VFX / audio only
```

An ability's `action_timing_event` and `recovery_timing_event` resolve against the
matching imported clip through `HeroAnimationDriver.get_semantic_event_time()`.
The resulting cast/action/recovery durations are owned by `HeroAbility` and continue
to use its own physics timers. It does **not** subscribe to a visual signal to spawn
an arrow, dash, apply status, or resolve damage; visual restart, interruption, and
LOD operations therefore cannot duplicate authority.

| Ability | Authoritative action schedule from authored clip |
|---|---|
| Prism Volley | Cast reaches `volley_release_1` at 0.4600 s; arrows 2/3 use 0.5612 / 0.6624 s; recovery opens at 0.8280 s. |
| Phase Step | Dash begins at `dash_start` 0.1344 s and ends at `dash_end` 0.3168 s; phase immunity uses that same authoritative dash window. |
| Tether Snare | Tension continues through `projectile_release` 0.7280 s; recovery opens at 0.9464 s. |
| Apex Constellation | The first arrow starts at `ultimate_release` 1.2376 s; the second is centered between release and `ultimate_impact_window`; the finisher starts at the 1.4924 s impact cue; recovery opens at 1.7290 s. |

The fallback exported phase values remain available if an ability has no configured
or validated authored event. This makes the timing policy graceful for future skills
while rejecting no existing GLB contract.

## Implementation changes

| Location | Responsibility |
|---|---|
| `scripts/gameplay/hero_ability.gd` | Resolves private cast/action/recovery timing from manifest values; exposes read-only authored event offsets to subclasses. |
| `scripts/gameplay/prism_volley.gd` | Emits its three authoritative arrows on the three separate inferred gameplay timer offsets. |
| `scripts/gameplay/phase_step.gd` | Starts movement/status only at `dash_start`; derives the actual dash/phase duration from `dash_end`. |
| `scripts/gameplay/tether_snare.gd` | Holds precision aim until `projectile_release` and guards a lost target at execution. |
| `scripts/gameplay/apex_constellation.gd` | Schedules three shots across authored release/impact timing and protects its finisher against a lost target. |
| `scripts/hero_character.gd` | Publishes a post-parenting `projectile_spawned` observation signal for all gameplay projectile producers. |

Resources and cooldown are committed when a cast is accepted. A target that becomes
invalid during the pre-action cast phase cancels safely without a stale projectile;
this gate records the existing committed-cast policy rather than silently changing
balance/refund rules.

## Engine evidence

Starting from an imported Godot project, run:

```bash
GODOT_BIN=/tmp/godot-src-4.3/bin/godot.linuxbsd.editor.x86_64
"$GODOT_BIN" --headless --path . --script res://tests/godot/phase9_ability_timing_smoke.gd
```

The recorded Godot 4.3 run exited `0` and printed
`PHASE9_ABILITY_TIMING_SMOKE result=PASS`. It covers live hero/drone scenes and
asserts:

1. a target-required cast fails without energy/cooldown commitment when no target
   exists;
2. Phase Step accepts an optional distant target, spends energy only on acceptance,
   begins dash/immunity at `dash_start`, and closes both at the authored window;
3. Prism Volley spends once, follows all three release times, emits three gameplay
   arrows and three cosmetic markers, and completes cast/action/recovery;
4. Tether follows its authored release time, sends one `DamageReceiver` payload,
   applies then expires root through `StatusComponent`, and recovers at clip end;
5. Apex Constellation enforces movement/basic locks, fires three payloads at its
   authored release/impact schedule, has exactly one finisher, applies one radial
   slow/damage event, and clears locks after recovery;
6. a target removed during a timed Prism cast emits `target_lost` and produces no
   stale projectile.

The rendererless sandbox emits known dummy-mesh diagnostics. This is real-engine
logic/timing evidence, not a GPU render, final VFX synchronization review, or mobile
performance claim.

## Remaining work

- dedicated broader targeting, projectile/hitbox edge-case, AI decision, navigation,
  balance, replay/network, and mobile-device gates;
- GPU-capable visual inspection of authored anticipation/release readability;
- final VFX/SFX, accessibility, Android profiling, QA, and packaged delivery.
