class_name ApexConstellationAbility
extends HeroAbility
## Ultimate — Apex Constellation: an anticipatory three-star hunt ending in a radial burst.

var _shot_timer: float = 0.0
var _shot_index: int = 0


func _init() -> void:
	slot_id = &"ultimate"
	display_name = "Apex Constellation"
	description = "Lock a target, call down three astral arrows, then detonate the final impact."
	energy_cost = 130.0
	cooldown_seconds = 46.0
	range = 19.0
	requires_target = true
	cast_seconds = 0.48
	action_seconds = 0.86
	recovery_seconds = 0.45
	locks_movement = true
	blocks_basic_attack = true
	animation_id = &"ultimate"


func _on_cast_started() -> void:
	if vfx != null:
		vfx.play_effect(&"ultimate_cast", hero.global_position + Vector3.UP * 1.2, _cast_aim, 1.35)
	if audio != null:
		audio.play_event(&"ultimate")


func _execute_action() -> void:
	_shot_index = 0
	_shot_timer = 0.0


func _update_action(delta: float) -> void:
	_shot_timer -= delta
	while _shot_index < 3 and _shot_timer <= 0.0:
		_fire_constellation_arrow(_shot_index)
		_shot_index += 1
		_shot_timer += 0.23


func _fire_constellation_arrow(index: int) -> void:
	if _cast_target == null or not is_instance_valid(_cast_target):
		return
	var finishing_shot := index == 2
	var event := DamageEvent.new()
	event.source = hero
	event.target = _cast_target
	event.amount = (stats.get_stat(&"skill_damage") * (1.20 if finishing_shot else 0.72) + stats.get_attack_damage() * (0.95 if finishing_shot else 0.42))
	event.damage_type = DamageEvent.DamageType.ENERGY
	event.ability_id = slot_id
	event.attack_source = &"apex_constellation"
	if finishing_shot:
		event.status_payload = {"id": &"slow", "duration": 1.4, "magnitude": 0.35}
		event.metadata["impact_radius"] = 3.4
		event.metadata["finisher"] = true
	(
		hero
		. spawn_projectile(
			_cast_target,
			event,
			{
				"speed": 42.0,
				"range": range + 4.0,
				"homing": 12.0,
				"visual_style": &"ultimate",
				"impact_radius": 3.4 if finishing_shot else 0.0,
			}
		)
	)
	if vfx != null:
		vfx.play_effect(&"ultimate_shot", hero.get_projectile_origin_position(), _cast_aim, 1.0 + index * 0.14)
