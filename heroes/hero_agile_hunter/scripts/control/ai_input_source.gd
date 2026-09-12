class_name AIInputSource
extends InputSource
## Optional controller proving the hero core is not coupled to player input.

@export var ideal_range: float = 13.0
@export var retreat_range: float = 6.0
@export var use_abilities: bool = true

var _decision_cooldown: float = 0.0


func reset_decision_state() -> void:
	_decision_cooldown = 0.0


func get_command(character: HeroCharacter) -> CharacterCommand:
	var command := CharacterCommand.new()
	var targeting := character.get_targeting()
	var target := targeting.acquire_nearest(26.0) if targeting != null else null
	if target == null:
		return command
	var to_target := target.global_position - character.global_position
	to_target.y = 0.0
	var distance := to_target.length()
	var direction := to_target.normalized() if distance > 0.01 else Vector3.ZERO
	command.aim_direction = direction
	if distance > ideal_range:
		command.move_direction = direction
	elif distance < retreat_range:
		command.move_direction = -direction
	command.request_attack = distance <= character.get_attack_range()
	_decision_cooldown = maxf(0.0, _decision_cooldown - get_physics_process_delta_time())
	if use_abilities and _decision_cooldown <= 0.0:
		if distance <= 15.0:
			command.request_ability(&"skill_01")
		elif distance > 16.0:
			command.request_ability(&"skill_02")
		if distance <= 12.0:
			command.request_ability(&"skill_03")
		if distance <= 18.0 and character.get_health_ratio() <= 0.55:
			command.request_ability(&"ultimate")
		_decision_cooldown = 1.1
	return command
