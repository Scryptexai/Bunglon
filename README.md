# Lyra Vesper — Hero Foundation (Godot 4.x)

Implementasi **hero playable 3D** untuk contract *Agile Ranged Hunter / Marksman*. Ini bukan satu script karakter monolitik: scene `HeroCharacter` hanya menjadi composition root yang menghubungkan sistem visual, gameplay, control, dan world interaction.

## Hero: Lyra Vesper, *The Lumen Huntress*

Lyra adalah pemburu antarbintang yang membaca lintasan cahaya seperti jejak mangsa. Siluetnya dibuat agar terbaca dari kamera MOBA: **energy bow bercahaya yang besar**, crest/ponytail gelap, mantel aurora asimetris, armor ringan indigo, visor cyan, dan core dada berbentuk berlian. Presentasi runtime aktif memakai paket GLB Phase 5 ber-skeleton dan beranimasi melalui `HeroPresentationAdapter`; bukan lagi assembly mesh primitive/prosedural. Gameplay tetap tidak bergantung pada path mesh tertentu.

![Concept art Lyra Vesper](heroes/hero_agile_hunter/docs/lyra_vesper_concept.png)

| Slot | Ability | Peran gameplay |
|---|---|---|
| Passive | **Slipstream Ledger** | Bergerak cepat membangun 3 Vantage. Serangan dengan Vantage menandai mangsa; tiga hit bertanda menyiapkan Lumen Arrow yang menembus target dan memberi burst. |
| Q / Skill 01 | **Prism Volley** | Tiga anak panah energi dalam fan sempit untuk burst dan clear yang presisi. |
| E / Skill 02 | **Phase Step** | Dash arah aim 6,8 m dan fase singkat untuk menghindari damage. |
| R / Skill 03 | **Tether Snare** | Proyektil taktis yang melakukan root pada target pertama. |
| F / Ultimate | **Apex Constellation** | Antisipasi/lock-on yang mengirim tiga astral arrow; hit terakhir meledak secara radial dan memberi slow. |

Rincian angka, target, VFX, SFX, dan alasan desain tersedia di [`HERO_DESIGN.md`](heroes/hero_agile_hunter/docs/HERO_DESIGN.md).

## Menjalankan

1. Buka folder ini sebagai project dengan **Godot 4.3+**.
2. Jalankan `demo/scenes/demo_arena.tscn` (atau `F6`), atau tekan `F5` dari project root.
3. Demo membuat Lyra player, satu Lyra dengan controller AI, dan beberapa hostile training drone.

### Kontrol desktop

| Aksi | Input |
|---|---|
| Movement | `W A S D` |
| Basic attack (hold) | `Space` |
| Cycle target | `Tab` |
| Prism Volley | `Q` |
| Phase Step | `E` |
| Tether Snare | `R` |
| Apex Constellation | `F` |

`PlayerInputSource` menyiapkan input desktop saat runtime. `HeroDemoHUD` juga menghubungkan tombol arah, attack, dan skill yang tampil di perangkat mobile ke API input yang sama; gameplay tidak pernah membaca input UI secara langsung.

## Struktur penting

```text
heroes/hero_agile_hunter/
├── scenes/                 # Hero, energy projectile, training target
├── scripts/
│   ├── core/               # stats, health, energy, status, team, DamageEvent
│   ├── gameplay/           # movement, targeting, attack, abilities, damage receiver
│   ├── control/            # CharacterCommand, player, AI, external controller boundary
│   ├── interaction/        # hurtbox, hitbox, detection, projectile
│   ├── presentation/       # imported GLB adapter, animation, VFX, audio, camera anchors
│   └── world/              # test target
├── data/                   # authored HeroStats resource
├── audio/                  # small, valid, spatial-ready WAV cue set
└── docs/                   # design, architecture, asset pipeline, validation

demo/                       # external camera, HUD/mobile bridge, smoke-test arena
tests/                      # contract/static validation without an engine binary
```

Lihat [`ARCHITECTURE.md`](heroes/hero_agile_hunter/docs/ARCHITECTURE.md) untuk node tree dan dependency flow, serta [`ASSET_PIPELINE.md`](heroes/hero_agile_hunter/docs/ASSET_PIPELINE.md) untuk hand-off art/audio production dan budget mobile.

## Validasi

```bash
python3 -m unittest discover -s tests -v
# Setelah project diimpor oleh Godot 4.3+:
godot --headless --path . --script res://tests/godot/phase6_import_probe.gd
godot --headless --path . --script res://tests/godot/phase6_integration_smoke.gd
# Optional, apabila GDQuest gdtoolkit tersedia:
gdlint heroes demo
```

`tests/test_project_contract.py` memeriksa scene entry point, node contract, asset path, semua ability, uniqueness class, dan validitas WAV. Dua probe Godot menjalankan import/runtime nyata untuk GLB, `AnimationPlayer`/`AnimationTree`, helper, LOD, dan jalur player/AI. Hasil dan batasan engine tercatat di [`PHASE_6_GODOT_INTEGRATION.md`](heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md).

## Status terhadap 3D Hero Production Roadmap V1

Roadmap menetapkan bahwa primitive/blocky mesh tidak boleh menjadi final character. **Phase 2 — 3D Character** menyediakan mesh `.glb` nyata di `character_final/`; **Phase 3 — Topology & Game Readiness** menyediakan LOD0/LOD1 yang dioptimalkan, UV atlas, material PBR, dan normal/tangent MikkTSpace; **Phase 4 — Rigging & Skinning** menyediakan GLB ber-skeleton, skin weights, inverse-bind matrices, socket helpers, serta bukti deformasi; **Phase 5 — Authored Animation Action Set** menyediakan 23 action GLB nyata dengan 523 channel/sampler rotasi dan semantic timing contract di `character_animated/`; dan **Phase 6 — Godot Integration** sekarang memakai asset tersebut sebagai visual aktif melalui adapter terpisah, `AnimationTree`, imported helper sockets, semantic presentation events, serta LOD swap tervalidasi. Tidak ada jalur visual primitive/prosedural yang aktif.

- [`PROJECT_PLAN.md`](PROJECT_PLAN.md) — phase gate, tool decision, dependency order, dan test strategy.
- [`ASSET_PIPELINE.md`](ASSET_PIPELINE.md) — contract concept → authored 3D mesh → UV/PBR → rig → animation → GLB → Godot.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — runtime boundary yang menjaga visual asset tetap terpisah dari gameplay.
- [`character_design.md`](character_design.md) — design lock Lyra Vesper, color/material language, silhouette, dan Phase 2 handoff.
- [`concept/`](concept/) dan [`references/`](references/) — key concept serta sembilan view reference wajib.
- [`character_final/`](character_final/) — GLB mesh source, source generator, provisional PBR textures, render inspection, dan Phase 2 QA.
- [`character_optimized/`](character_optimized/) — Phase 3 LOD0 GLB, packed texture maps, topology/material decisions, visual evidence, and QA.
- [`character_lod/`](character_lod/) — Phase 3 matching LOD1 GLB and selection policy.
- [`character_rigged/`](character_rigged/) — Phase 4 rigged LOD0/LOD1 GLBs, skeleton/socket specification, CPU deformation evidence, and QA.
- [`character_animated/`](character_animated/) — Phase 5 animated LOD0/LOD1 GLBs, 23 named action clips, event/timing specification, CPU LBS/socket evidence, and Phase 6 handoff.
- [`heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md`](heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md) — implemented adapter boundary, Godot importer conversion, and recorded engine validation.

Gameplay bergantung pada interface/komponen (`DamageEvent`, `StatsComponent`, `Hurtbox`, `DamageReceiver`, `TargetingComponent`), **bukan** pada `MeshInstance3D` tertentu. Karena itu visual GLB aktif dapat terus diiterasi tanpa membongkar controller, combat, abilities, targeting, atau AI.
