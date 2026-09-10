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


func _execute_action() -> void:
	var direction := _cast_aim
	if movement != null:
		movement.start_dash(direction, 6.8, 0.28)
	if hero.get_statuses() != null:
		hero.get_statuses().apply_status(&"phase_shift", 0.34, 1.0, hero)
	if vfx != null:
		vfx.play_effect(&"skill_02", hero.global_position + Vector3.UP)
	if audio != null:
		audio.play_event(&"movement")
