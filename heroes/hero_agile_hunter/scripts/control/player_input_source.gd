class_name PlayerInputSource
extends InputSource
## Keyboard is supplied for desktop testing; the same API accepts a mobile overlay.

var _mobile_move: Vector2 = Vector2.ZERO
var _mobile_attack_held: bool = false
var _mobile_target_next: bool = false
var _mobile_abilities: Array[StringName] = []


func _ready() -> void:
	_ensure_default_input_map()


func get_command(character: HeroCharacter) -> CharacterCommand:
	var command := CharacterCommand.new()
	var keyboard_move := Input.get_vector(&"hero_move_left", &"hero_move_right", &"hero_move_forward", &"hero_move_back")
	var move_input := keyboard_move if keyboard_move.length() > _mobile_move.length() else _mobile_move
	command.move_direction = _camera_relative_move(character, move_input)
	command.aim_direction = _camera_aim_direction(character)
	command.request_attack = Input.is_action_pressed(&"hero_attack") or _mobile_attack_held
	command.request_target_next = Input.is_action_just_pressed(&"hero_target_next") or _mobile_target_next
	if Input.is_action_just_pressed(&"hero_skill_1"):
		command.request_ability(&"skill_01")
	if Input.is_action_just_pressed(&"hero_skill_2"):
		command.request_ability(&"skill_02")
	if Input.is_action_just_pressed(&"hero_skill_3"):
		command.request_ability(&"skill_03")
	if Input.is_action_just_pressed(&"hero_ultimate"):
		command.request_ability(&"ultimate")
	for slot: StringName in _mobile_abilities:
		command.request_ability(slot)
	_mobile_abilities.clear()
	_mobile_target_next = false
	return command


func set_mobile_move(move: Vector2) -> void:
	_mobile_move = move.limit_length(1.0)


func set_mobile_attack_held(held: bool) -> void:
	_mobile_attack_held = held


func request_mobile_ability(slot: StringName) -> void:
	if not _mobile_abilities.has(slot):
		_mobile_abilities.append(slot)


func request_mobile_target_next() -> void:
	_mobile_target_next = true


func clear_mobile_input() -> void:
	# A control-mode change or disabled hero must not replay a stale touch hold/button
	# when player control becomes active again.
	_mobile_move = Vector2.ZERO
	_mobile_attack_held = false
	_mobile_target_next = false
	_mobile_abilities.clear()


func _camera_relative_move(character: HeroCharacter, input: Vector2) -> Vector3:
	if input.length_squared() < 0.0001:
		return Vector3.ZERO
	var camera := character.get_viewport().get_camera_3d()
	if camera == null:
		return Vector3(input.x, 0.0, input.y).normalized()
	var forward := -camera.global_transform.basis.z
	var right := camera.global_transform.basis.x
	forward.y = 0.0
	right.y = 0.0
	return (right.normalized() * input.x + forward.normalized() * input.y).normalized()


func _camera_aim_direction(character: HeroCharacter) -> Vector3:
	var camera := character.get_viewport().get_camera_3d()
	if camera != null:
		var forward := -camera.global_transform.basis.z
		forward.y = 0.0
		if forward.length_squared() > 0.0001:
			return forward.normalized()
	return -character.global_transform.basis.z


func _ensure_default_input_map() -> void:
	_register_key(&"hero_move_left", KEY_A)
	_register_key(&"hero_move_right", KEY_D)
	_register_key(&"hero_move_forward", KEY_W)
	_register_key(&"hero_move_back", KEY_S)
	_register_key(&"hero_attack", KEY_SPACE)
	_register_key(&"hero_skill_1", KEY_Q)
	_register_key(&"hero_skill_2", KEY_E)
	_register_key(&"hero_skill_3", KEY_R)
	_register_key(&"hero_ultimate", KEY_F)
	_register_key(&"hero_target_next", KEY_TAB)


func _register_key(action_name: StringName, keycode: Key) -> void:
	if InputMap.has_action(action_name):
		return
	InputMap.add_action(action_name)
	var event := InputEventKey.new()
	event.physical_keycode = keycode
	InputMap.action_add_event(action_name, event)
