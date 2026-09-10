class_name PrismVolleyAbility
extends HeroAbility
## Skill 01 — Prism Volley: a tight, readable three-arrow offensive fan.


func _init() -> void:
	slot_id = &"skill_01"
	display_name = "Prism Volley"
	description = "Launch three energy arrows in a precise fan. Each arrow deals Energy damage."
	energy_cost = 48.0
	cooldown_seconds = 5.5
	range = 16.0
	requires_target = true
	cast_seconds = 0.16
	action_seconds = 0.0
	recovery_seconds = 0.28
	animation_id = &"skill_01"


func _on_cast_started() -> void:
	if vfx != null:
		vfx.play_effect(&"skill_01_cast", hero.get_projectile_origin_position())
	if audio != null:
		audio.play_event(&"skill_cast")


func _execute_action() -> void:
	var base_direction := _cast_aim
	for degrees: float in [-7.5, 0.0, 7.5]:
		var event := DamageEvent.new()
		event.source = hero
		event.target = _cast_target
		event.amount = stats.get_stat(&"skill_damage") + stats.get_attack_damage() * 0.48
		event.damage_type = DamageEvent.DamageType.ENERGY
		event.ability_id = slot_id
		event.attack_source = &"prism_volley"
		event.metadata["prism_arrow"] = true
		(
			hero
			. spawn_projectile(
				_cast_target,
				event,
				{
					"speed": 36.0,
					"range": range + 2.0,
					"homing": 1.2,
					"direction_override": base_direction.rotated(Vector3.UP, deg_to_rad(degrees)),
					"visual_style": &"prism",
				}
			)
		)
	if vfx != null:
		vfx.play_effect(&"skill_01_action", hero.get_projectile_origin_position())
	if audio != null:
		audio.play_event(&"weapon_release")
