class_name PrismVolleyAbility
extends HeroAbility
## Skill 01 — Prism Volley: a tight, readable three-arrow offensive fan.

var _release_events: Array[StringName] = [&"volley_release_1", &"volley_release_2", &"volley_release_3"]
var _release_degrees: Array[float] = [-7.5, 0.0, 7.5]
var _release_index: int = 0
var _action_elapsed: float = 0.0


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
	action_timing_event = &"volley_release_1"


func _on_cast_started() -> void:
	if vfx != null:
		vfx.play_effect(&"skill_01_cast", hero.get_projectile_origin_position())
	if audio != null:
		audio.play_event(&"skill_cast")


func _execute_action() -> void:
	_release_index = 0
	_action_elapsed = 0.0
	_emit_due_arrows()


func _update_action(delta: float) -> void:
	_action_elapsed += delta
	_emit_due_arrows()


func _emit_due_arrows() -> void:
	while _release_index < _release_events.size():
		var release_offset := get_action_event_offset(_release_events[_release_index], _release_index * 0.10)
		if _action_elapsed + 0.0005 < release_offset:
			return
		_fire_prism_arrow(_release_degrees[_release_index])
		_release_index += 1


func _fire_prism_arrow(degrees: float) -> void:
	if _cast_target == null or not is_instance_valid(_cast_target) or not CombatUtil.is_valid_hostile(hero, _cast_target):
		return
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
				"direction_override": _cast_aim.rotated(Vector3.UP, deg_to_rad(degrees)),
				"visual_style": &"prism",
			}
			)
	)
	if vfx != null:
		vfx.play_effect(&"skill_01_action", hero.get_projectile_origin_position())
	if audio != null:
		audio.play_event(&"weapon_release")
