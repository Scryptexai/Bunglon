class_name CharacterController
extends Node
## Applies source-neutral intent to movement and combat. No ability reads raw player input.
##
## The controller owns the command boundary: each physics tick consumes a normalized
## snapshot from exactly one active source. This prevents stale mobile/external input
## from leaking across player, AI, replay, or disabled-control transitions.

signal control_mode_changed(mode: StringName)

var character: HeroCharacter
var movement: MovementController
var targeting: TargetingComponent
var basic_attack: BasicAttack
var abilities: AbilityController
var statuses: StatusComponent
var player_source: PlayerInputSource
var ai_source: AIInputSource
var _external_command: CharacterCommand
var _enabled: bool = true


func initialize(
	owner_character: HeroCharacter,
	owner_movement: MovementController,
	owner_targeting: TargetingComponent,
	owner_basic_attack: BasicAttack,
	owner_abilities: AbilityController,
	owner_statuses: StatusComponent
) -> void:
	if character != null and character.control_mode_changed.is_connected(_on_character_control_mode_changed):
		character.control_mode_changed.disconnect(_on_character_control_mode_changed)
	character = owner_character
	movement = owner_movement
	targeting = owner_targeting
	basic_attack = owner_basic_attack
	abilities = owner_abilities
	statuses = owner_statuses
	player_source = get_node_or_null("PlayerInput") as PlayerInputSource
	ai_source = get_node_or_null("AIInput") as AIInputSource
	if character != null and not character.control_mode_changed.is_connected(_on_character_control_mode_changed):
		character.control_mode_changed.connect(_on_character_control_mode_changed)
	_reset_source_state()


func set_enabled(enabled: bool) -> void:
	_enabled = enabled
	if not _enabled:
		_reset_source_state()


func submit_external_command(command: CharacterCommand) -> void:
	# External packets may be mutated/reused by a network or replay producer after
	# submission. Retain an isolated, normalized snapshot for one physics tick only.
	_external_command = command.snapshot() if command != null else null


func _physics_process(_delta: float) -> void:
	if not _enabled or character == null or not character.is_combat_ready():
		return
	var command := _get_active_command()
	if command == null:
		return
	command = command.snapshot()
	if statuses != null and statuses.is_movement_locked():
		command.move_direction = Vector3.ZERO
	if movement != null:
		movement.set_move_intent(command.move_direction)
		if command.aim_direction.length_squared() > 0.0001:
			movement.set_combat_facing(command.aim_direction)
	if command.request_target_next and targeting != null:
		targeting.select_next_target()
	var target := targeting.get_target(character.get_attack_range()) if targeting != null else null
	if abilities != null:
		for slot: StringName in command.requested_abilities:
			abilities.try_activate(slot, target, command.aim_direction)
	if command.request_attack and basic_attack != null:
		basic_attack.try_attack(target)


func _get_active_command() -> CharacterCommand:
	match character.get_control_mode():
		&"ai":
			return ai_source.get_command(character) if ai_source != null else CharacterCommand.new()
		&"external":
			var command := _external_command
			_external_command = null
			return command if command != null else CharacterCommand.new()
		_:
			return player_source.get_command(character) if player_source != null else CharacterCommand.new()


func _on_character_control_mode_changed(mode: StringName) -> void:
	_reset_source_state()
	control_mode_changed.emit(mode)


func _reset_source_state() -> void:
	_external_command = null
	if player_source != null:
		player_source.clear_mobile_input()
	if ai_source != null:
		ai_source.reset_decision_state()
	if movement != null:
		movement.force_stop()
		movement.clear_combat_facing()
