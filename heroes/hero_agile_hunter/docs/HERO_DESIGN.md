# Lyra Vesper — The Lumen Huntress

## Identitas

**Role:** Marksman / ranged damage dealer

**Archetype:** Agile Ranged Hunter

**Combat promise:** pemain yang menjaga jarak, membaca target prioritas, membangun momentum dengan positioning, lalu mengonversinya menjadi burst presisi.

Lyra tidak memakai bobot visual tank. Tubuhnya ramping-atletis dengan armor segmented ringan. Pembeda utamanya adalah energy bow tinggi ber-emisi cyan, mantel aurora di sisi kiri, rambut/crest gelap yang memanjang ke belakang, visor cyan, dan chest-core diamond. Kontrasnya sengaja dibagi sebagai berikut:

- **Skin:** hangat dan matte agar wajah tetap terbaca.
- **Suit / leather:** indigo gelap dan ungu untuk massa tubuh utama.
- **Armor / metal:** biru baja terang untuk edge readability.
- **Energy:** cyan untuk basic/passive, violet untuk mobilitas, emas untuk ultimate.

Siluet ini masih terbaca tanpa texture saat kamera jauh: busur tinggi + mantel satu sisi + ponytail membentuk tiga landmark yang tidak simetris.

## Ability kit

| Slot | Trigger | Cost / CD | Range / target | Damage & interaction | Animation / feedback |
|---|---|---:|---|---|---|
| **Passive — Slipstream Ledger** | Otomatis saat bergerak cepat | – | Self → basic target | Setiap 0,75 dtk bergerak memberi 1 Vantage (maks. 3). Basic attack mengonsumsi 1 untuk bonus 22% AD dan Prey Mark. Tiga marked hit pada target yang sama menyiapkan Lumen Arrow berikutnya: +60% damage dan tembus dua target. | Aura cyan kecil saat charge; pulse saat Lumen siap. |
| **Skill 01 — Prism Volley** | `Q` / button | 48 energy / 5,5 dtk | 16 m, target musuh | Tiga energy arrow dalam spread ±7,5°. Masing-masing `Skill Damage + 48% AD` sebagai Energy damage. | Cast 0,16 dtk → release → recovery 0,28 dtk; violet/cyan fan yang sempit. |
| **Skill 02 — Phase Step** | `E` / button | 58 energy / 8 dtk | 6,8 m arah aim | Dash 0,28 dtk dan `phase_shift` 0,34 dtk. Status tersebut membuat `DamageReceiver` menolak damage secara eksplisit—bukan sekadar VFX. | Lean/dash ringan dengan violet after-pulse. |
| **Skill 03 — Tether Snare** | `R` / button | 66 energy / 10 dtk | 17 m, target musuh | Tether bolt melakukan `0,9 Skill Damage + 35% AD` Energy damage dan memberi `root` 1,05 dtk melalui `DamageEvent.status_payload`. | Antisipasi busur, cyan-teal tether burst. |
| **Ultimate — Apex Constellation** | `F` / button | 130 energy / 46 dtk | 19 m, target musuh | Lock 0,48 dtk, lalu 3 astral arrow. Dua pertama: `0,72 Skill Damage + 42% AD`; terakhir: `1,2 Skill Damage + 95% AD`, slow 35% selama 1,4 dtk, serta radial impact 3,4 m. | Cast terkunci, energi emas, tiga timing hit yang jelas, recovery 0,45 dtk. |

## Basic attack timeline

```text
Acquire target → combat facing → draw/windup (0.20s)
→ instantiate EnergyProjectile at ProjectileOrigin
→ homing/travel → Hurtbox hit → DamageReceiver resolves DamageEvent
→ hit VFX/SFX → recovery (0.22s) / attack interval from Stats
```

- `BasicAttack` hanya mengurus cadence dan proyektil.
- `TargetingComponent` mengurus nearest/selected/priority/lost target.
- `EnergyProjectile` membawa payload dan mendeteksi `Hurtbox`.
- `DamageReceiver` menghitung defense/resistance/critical lalu mengubah `HealthComponent`.

Dengan pemisahan itu basic attack tidak memerlukan mesh target dan dapat dipakai AI tanpa cabang player-only.

## Animation identity

| State group | Implementasi saat ini | Intent final |
|---|---|---|
| Locomotion | Idle breathing/scan, walk/run stride, smooth facing, dash pose | Ringan, pusat gravitasi ke depan, tanpa langkah tank. |
| Combat | Draw, charge, release, recovery pada rig bones | Tangan bow stabil; tangan tarik cepat dan terkendali. |
| Reaction | light hit, heavy hit, death pose | Reaksi singkat agar marksman tetap responsif. |
| Ability | Separate `skill_01`, `skill_02`, `skill_03`, `ultimate` action states | Setiap action punya cast/action/recovery dan timing gameplay yang eksplisit. |
| State | spawn, victory, death | Spawn/ultimate memakai silhouette bow sebagai focal point. |

`HeroAnimationDriver` sekarang meneruskan intent gameplay ke `HeroPresentationAdapter`, yang memainkan 23 clip authored pada imported skeleton melalui `AnimationPlayer` dan `AnimationTree`. Marker release tetap hanya memberi VFX/SFX presentasi; timer gameplay dan event damage/projectile tidak berubah menjadi otoritas visual.

## Balance hooks

Semua angka berada pada default `HeroStats` atau property ability yang diekspos, bukan tersembunyi dalam visual. Sistem modifier source-scoped di `StatsComponent` disediakan agar item, buff, talent, level scaling, dan equipment bisa ditambahkan tanpa mengubah logic damage/movement.
