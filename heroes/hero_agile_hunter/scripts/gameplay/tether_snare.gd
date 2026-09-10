class_name TetherSnareAbility
extends HeroAbility
## Skill 03 — Tether Snare: tactical projectile that roots the first marked enemy.


func _init() -> void:
	slot_id = &"skill_03"
	display_name = "Tether Snare"
	description = "Fire a tether bolt that roots its first target and exposes it to follow-up fire."
	energy_cost = 66.0
	cooldown_seconds = 10.0
	range = 17.0
	requires_target = true
	cast_seconds = 0.22
	action_seconds = 0.0
	recovery_seconds = 0.30
	animation_id = &"skill_03"


func _on_cast_started() -> void:
	if vfx != null:
		vfx.play_effect(&"skill_03_cast", hero.get_projectile_origin_position())
	if audio != null:
		audio.play_event(&"skill_cast")


func _execute_action() -> void:
	var event := DamageEvent.new()
	event.source = hero
	event.target = _cast_target
	event.amount = stats.get_stat(&"skill_damage") * 0.9 + stats.get_attack_damage() * 0.35
	event.damage_type = DamageEvent.DamageType.ENERGY
	event.ability_id = slot_id
	event.attack_source = &"tether_snare"
	event.status_payload = {"id": &"root", "duration": 1.05, "magnitude": 1.0}
	(
		hero
		. spawn_projectile(
			_cast_target,
			event,
			{
				"speed": 27.0,
				"range": range,
				"homing": 7.5,
				"visual_style": &"snare",
			}
		)
	)
	if vfx != null:
		vfx.play_effect(&"skill_03", hero.get_projectile_origin_position())
	if audio != null:
		audio.play_event(&"weapon_release")
