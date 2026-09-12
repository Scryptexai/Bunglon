class_name PhaseStepAbility
extends HeroAbility
## Skill 02 — Phase Step: directionally dash through danger, briefly ignoring damage.


func _init() -> void:
	slot_id = &"skill_02"
	display_name = "Phase Step"
	description = "Dash 6.8m in the aim direction and phase through damage for a brief moment."
	energy_cost = 58.0
	cooldown_seconds = 8.0
	range = 0.0
	requires_target = false
	cast_seconds = 0.0
	action_seconds = 0.32
	recovery_seconds = 0.16
	animation_id = &"skill_02"
	action_timing_event = &"dash_start"


func _execute_action() -> void:
	var dash_end_time := get_authored_event_time(&"dash_end", _resolved_cast_seconds + 0.28)
	var dash_duration := maxf(0.01, dash_end_time - _resolved_cast_seconds)
	var direction := _cast_aim
	var dash_started := movement.start_dash(direction, 6.8, dash_duration) if movement != null else false
	if dash_started and hero.get_statuses() != null:
		hero.get_statuses().apply_status(&"phase_shift", dash_duration, 1.0, hero)
	if vfx != null:
		vfx.play_effect(&"skill_02", hero.global_position + Vector3.UP)
	if audio != null:
		audio.play_event(&"movement")
