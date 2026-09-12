extends SceneTree
## Real-engine Phase 7 controller and command-boundary smoke coverage.
##
## Invoke after a Godot 4.3 project import:
##   godot --headless --path . --script res://tests/godot/phase7_controller_smoke.gd
##
## This intentionally exercises the live HeroCharacter composition rather than a
## stand-in controller. It verifies desktop/touch input translation, one-shot command
## semantics, source switching, immutable external snapshots, and a fresh external
## ability intent reaching the imported authored presentation.

const HERO_SCENE := preload("res://heroes/hero_agile_hunter/scenes/hero_character.tscn")

var _failed := false


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	_test_command_snapshot_contract()
	var hero := await _spawn_hero("Phase7ControllerHero")
	if hero != null:
		await _test_player_input_translation(hero)
		await _test_source_switching_and_external_command(hero)
		hero.queue_free()
		await process_frame
	print("PHASE7_CONTROLLER_SMOKE result=%s" % ("FAIL" if _failed else "PASS"))
	quit(1 if _failed else 0)


func _test_command_snapshot_contract() -> void:
	var source := CharacterCommand.new()
	source.move_direction = Vector3(8.0, 5.0, -6.0)
	source.aim_direction = Vector3(-3.0, 2.0, 4.0)
	source.request_attack = true
	source.request_target_next = true
	source.request_ability(&"skill_02")
	source.request_ability(&"skill_02")
	source.request_ability(&"")
	var frozen := source.snapshot()
	source.move_direction = Vector3.ZERO
	source.aim_direction = Vector3.ZERO
	source.request_attack = false
	source.request_target_next = false
	source.request_ability(&"ultimate")

	_expect(is_equal_approx(frozen.move_direction.length(), 1.0), "command snapshot normalizes planar movement")
	_expect(is_zero_approx(frozen.move_direction.y), "command snapshot strips vertical movement")
	_expect(is_equal_approx(frozen.aim_direction.length(), 1.0), "command snapshot normalizes planar aim")
	_expect(is_zero_approx(frozen.aim_direction.y), "command snapshot strips vertical aim")
	_expect(frozen.request_attack and frozen.request_target_next, "command snapshot retains boolean intent")
	_expect(frozen.requested_abilities == [&"skill_02"], "command snapshot de-duplicates and isolates ability requests")


func _spawn_hero(hero_name: String) -> HeroCharacter:
	var hero := HERO_SCENE.instantiate() as HeroCharacter
	_expect(hero != null, "HeroCharacter scene instantiates for controller test")
	if hero == null:
		return null
	hero.name = hero_name
	hero.position = Vector3(0.0, 0.1, 0.0)
	hero.team_id = 1
	hero.set_control_mode(&"player")
	get_root().add_child(hero)
	await process_frame
	await process_frame
	await physics_frame
	_expect(hero.is_combat_ready(), "live HeroCharacter initializes before controller assertions")
	_expect(hero.visual != null and hero.visual.is_import_ready(), "controller test retains imported authored presentation")
	return hero


func _test_player_input_translation(hero: HeroCharacter) -> void:
	var player_input := hero.get_node_or_null("Control/CharacterController/PlayerInput") as PlayerInputSource
	_expect(player_input != null, "PlayerInputSource is available below CharacterController")
	if player_input == null:
		return
	_expect(InputMap.has_action(&"hero_move_forward") and InputMap.has_action(&"hero_attack"), "desktop input actions register through PlayerInputSource")

	Input.action_press(&"hero_move_forward")
	await process_frame
	var desktop_command := player_input.get_command(hero)
	Input.action_release(&"hero_move_forward")
	_expect(desktop_command.move_direction.dot(Vector3.FORWARD) > 0.99, "W-style desktop intent maps to Godot forward")
	_expect(desktop_command.aim_direction.length_squared() > 0.9, "player command supplies a planar combat aim")

	player_input.set_mobile_move(Vector2(0.0, -1.0))
	player_input.set_mobile_attack_held(true)
	player_input.request_mobile_ability(&"skill_02")
	player_input.request_mobile_ability(&"skill_02")
	player_input.request_mobile_target_next()
	var touch_command := player_input.get_command(hero)
	var consumed_command := player_input.get_command(hero)
	_expect(touch_command.move_direction.dot(Vector3.FORWARD) > 0.99, "touch movement uses the same camera-relative planar command")
	_expect(touch_command.request_attack and touch_command.request_target_next, "touch holds and target tap reach the shared command")
	_expect(touch_command.requested_abilities == [&"skill_02"], "touch ability press is a de-duplicated one-shot request")
	_expect(consumed_command.requested_abilities.is_empty() and not consumed_command.request_target_next, "one-shot touch requests are consumed once")
	_expect(consumed_command.request_attack, "touch attack remains held until an explicit release")
	player_input.clear_mobile_input()
	var cleared_command := player_input.get_command(hero)
	_expect(cleared_command.move_direction == Vector3.ZERO and not cleared_command.request_attack, "clearing touch input removes held movement and attack")


func _test_source_switching_and_external_command(hero: HeroCharacter) -> void:
	var controller := hero.controller
	var player_input := hero.get_node_or_null("Control/CharacterController/PlayerInput") as PlayerInputSource
	var phase_step := hero.ability_controller.get_ability(&"skill_02")
	_expect(controller != null and player_input != null and phase_step != null, "controller exposes source and Phase Step dependencies")
	if controller == null or player_input == null or phase_step == null:
		return

	var observed_modes: Array[StringName] = []
	controller.control_mode_changed.connect(func(mode: StringName) -> void: observed_modes.append(mode))
	hero.set_control_mode(&"ai")
	player_input.request_mobile_ability(&"skill_02")
	for _frame: int in 3:
		await physics_frame
	var queued_while_ai := player_input.get_command(hero)
	_expect(queued_while_ai.requested_abilities == [&"skill_02"], "AI mode never consumes PlayerInputSource requests")
	_expect(phase_step.phase == HeroAbility.Phase.READY, "inactive player input cannot activate an ability while AI mode is selected")

	player_input.request_mobile_ability(&"skill_02")
	hero.set_control_mode(&"player")
	var after_player_transition := player_input.get_command(hero)
	_expect(after_player_transition.requested_abilities.is_empty(), "control transition clears stale mobile ability taps")
	_expect(observed_modes == [&"ai", &"player"], "controller publishes each live control-mode transition")

	hero.set_control_mode(&"external")
	var stale_packet := CharacterCommand.new()
	stale_packet.request_ability(&"skill_02")
	controller.submit_external_command(stale_packet)
	hero.set_control_mode(&"player")
	hero.set_control_mode(&"external")
	await physics_frame
	_expect(phase_step.phase == HeroAbility.Phase.READY, "external command queued before a mode transition is discarded")

	var external_packet := CharacterCommand.new()
	external_packet.move_direction = Vector3(9.0, 4.0, 0.0)
	external_packet.aim_direction = Vector3(5.0, 3.0, 0.0)
	external_packet.request_ability(&"skill_02")
	controller.submit_external_command(external_packet)
	# Mutating the producer-owned packet after submission must not alter the queued tick.
	external_packet.move_direction = Vector3.ZERO
	external_packet.aim_direction = Vector3.BACK
	external_packet.requested_abilities.clear()
	await create_timer(0.22).timeout
	_expect(phase_step.phase != HeroAbility.Phase.READY, "fresh external command activates the shared Phase Step lifecycle")
	_expect(hero.visual.get_active_clip() == &"skill_02", "external ability intent maps to the imported skill_02 clip")
	_expect(hero.global_position.x > 0.01, "external snapshot retains submitted planar aim for the authored dash window")


func _expect(condition: bool, message: String) -> void:
	if condition:
		print("PHASE7_CONTROLLER_SMOKE PASS %s" % message)
		return
	_failed = true
	push_error("PHASE7_CONTROLLER_SMOKE FAIL %s" % message)
