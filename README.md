# Lyra Vesper — Hero Foundation (Godot 4.x)

Implementasi **hero playable 3D** untuk contract *Agile Ranged Hunter / Marksman*. Ini bukan satu script karakter monolitik: scene `HeroCharacter` hanya menjadi composition root yang menghubungkan sistem visual, gameplay, control, dan world interaction.

## Hero: Lyra Vesper, *The Lumen Huntress*

Lyra adalah pemburu antarbintang yang membaca lintasan cahaya seperti jejak mangsa. Siluetnya dibuat agar terbaca dari kamera MOBA: **energy bow bercahaya yang besar**, crest/ponytail gelap, mantel aurora asimetris, armor ringan indigo, visor cyan, dan core dada berbentuk berlian. Presentasi 3D native dibangun dari modul mesh Godot yang terikat ke `Skeleton3D`, sehingga proyek ini tetap runnable tanpa ketergantungan model pihak ketiga dan dapat diganti dengan asset skinned production tanpa menyentuh gameplay.

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
│   ├── presentation/       # procedural rig/model, animation, VFX, audio, camera anchors
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
# Optional, apabila GDQuest gdtoolkit tersedia:
gdlint heroes demo
```

`tests/test_project_contract.py` memeriksa scene entry point, node contract, asset path, semua ability, uniqueness class, dan validitas WAV. Test ini sengaja tidak memerlukan binary Godot. Untuk runtime QA di editor, ikuti checklist di [`TESTING.md`](heroes/hero_agile_hunter/docs/TESTING.md).

## Catatan integrasi production

- Gameplay bergantung pada interface/komponen (`DamageEvent`, `StatsComponent`, `Hurtbox`, `DamageReceiver`, `TargetingComponent`), **bukan** pada `MeshInstance3D` tertentu.
- Visual native saat ini adalah rig modular yang valid dan dimainkan langsung oleh `HeroAnimationDriver`. Untuk art final, replace modul tersebut dengan satu `glTF/GLB` rigged, pertahankan bone/socket `hand_r` dan `ProjectileOrigin`, lalu sambungkan clip import ke nama state yang sama.
- Semua VFX dibuat ringan dan data/event-driven; hindari particle overdraw besar di versi mobile final.
- Cue WAV adalah cue sintesis original untuk feedback runnable. Rekaman voice/callout berlokalisasi harus menggantikannya pada tahap audio final tanpa mengubah gameplay call-site.
