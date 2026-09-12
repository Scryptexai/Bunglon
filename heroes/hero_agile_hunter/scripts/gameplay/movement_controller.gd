class_name MovementController
extends Node
## Responsive locomotion layer. It moves CharacterBody3D but does not inspect input devices.

signal locomotion_state_changed(previous: StringName, current: StringName)
signal dash_started(direction: Vector3)
signal dash_finished
signal footstep

@export var acceleration: float = 30.0
@export var deceleration: float = 38.0
@export var dash_speed: float = 20.0

var character: CharacterBody3D
var stats: StatsComponent
var statuses: StatusComponent
var animation_driver: HeroAnimationDriver
var horizontal_speed: float = 0.0
var locomotion_state: StringName = &"idle"
var _move_intent: Vector3 = Vector3.ZERO
var _combat_facing: Vector3 = Vector3.ZERO
var _dash_direction: Vector3 = Vector3.ZERO
var _dash_remaining: float = 0.0
var _footstep_remaining: float = 0.0
var _action_locks: Dictionary = {}


func initialize(owner_character: CharacterBody3D, owner_stats: StatsComponent, owner_statuses: StatusComponent, owner_animation: HeroAnimationDriver) -> void:
	character = owner_character
	stats = owner_stats
	statuses = owner_statuses
	animation_driver = owner_animation


func set_move_intent(direction: Vector3) -> void:
	direction.y = 0.0
	_move_intent = direction.normalized() if direction.length_squared() > 0.0001 else Vector3.ZERO


func set_combat_facing(direction: Vector3) -> void:
	direction.y = 0.0
	if direction.length_squared() > 0.0001:
		_combat_facing = direction.normalized()


func clear_combat_facing() -> void:
	_combat_facing = Vector3.ZERO


func set_action_lock(source_id: StringName, locked: bool) -> void:
	if locked:
		_action_locks[source_id] = true
	else:
		_action_locks.erase(source_id)


func is_action_locked() -> bool:
	return not _action_locks.is_empty()


func start_dash(direction: Vector3, distance: float, duration: float) -> bool:
	if character == null or duration <= 0.0 or is_action_locked() or (statuses != null and statuses.is_movement_locked()):
		return false
	direction.y = 0.0
	if direction.length_squared() < 0.0001:
		direction = -character.global_transform.basis.z
	_dash_direction = direction.normalized()
	dash_speed = maxf(1.0, distance / duration)
	_dash_remaining = duration
	set_combat_facing(_dash_direction)
	dash_started.emit(_dash_direction)
	return true


func force_stop() -> void:
	_move_intent = Vector3.ZERO
	_dash_remaining = 0.0
	if character != null:
		character.velocity.x = 0.0
		character.velocity.z = 0.0


func is_dashing() -> bool:
	return _dash_remaining > 0.0


func _physics_process(delta: float) -> void:
	if character == null:
		return
	if _dash_remaining > 0.0:
		_update_dash(delta)
	else:
		_update_locomotion(delta)
	_apply_gravity(delta)
	character.move_and_slide()
	horizontal_speed = Vector2(character.velocity.x, character.velocity.z).length()
	_update_state()
	_update_footsteps(delta)


func _update_footsteps(delta: float) -> void:
	if horizontal_speed < 1.0 or is_dashing():
		_footstep_remaining = 0.0
		return
	_footstep_remaining -= delta
	if _footstep_remaining <= 0.0:
		var stride_seconds := lerpf(0.38, 0.22, clampf(horizontal_speed / 7.0, 0.0, 1.0))
		_footstep_remaining = stride_seconds
		footstep.emit()


func _update_dash(delta: float) -> void:
	_dash_remaining -= delta
	character.velocity.x = _dash_direction.x * dash_speed
	character.velocity.z = _dash_direction.z * dash_speed
	_rotate_toward(_dash_direction, delta, 1.7)
	if _dash_remaining <= 0.0:
		_dash_remaining = 0.0
		dash_finished.emit()


func _update_locomotion(delta: float) -> void:
	var requested := _move_intent
	if is_action_locked() or (statuses != null and statuses.is_movement_locked()):
		requested = Vector3.ZERO
	var speed := stats.get_movement_speed() if stats != null else 0.0
	if statuses != null:
		speed *= statuses.movement_multiplier()
	var desired_velocity := requested * speed
	var horizontal := Vector3(character.velocity.x, 0.0, character.velocity.z)
	var rate := acceleration if requested != Vector3.ZERO else deceleration
	horizontal = horizontal.move_toward(desired_velocity, rate * delta)
	character.velocity.x = horizontal.x
	character.velocity.z = horizontal.z
	var facing := requested if requested != Vector3.ZERO else _combat_facing
	if facing != Vector3.ZERO:
		_rotate_toward(facing, delta)


func _apply_gravity(delta: float) -> void:
	if character.is_on_floor():
		if character.velocity.y < 0.0:
			character.velocity.y = -0.5
	else:
		character.velocity.y -= float(ProjectSettings.get_setting("physics/3d/default_gravity")) * delta


func _rotate_toward(direction: Vector3, delta: float, multiplier: float = 1.0) -> void:
	var desired_yaw := atan2(-direction.x, -direction.z)
	var turn_speed := stats.get_stat(&"turn_speed") if stats != null else 12.0
	character.rotation.y = lerp_angle(character.rotation.y, desired_yaw, minf(1.0, turn_speed * multiplier * delta))


func _update_state() -> void:
	var next_state: StringName = &"idle"
	if is_dashing():
		next_state = &"dash"
	elif horizontal_speed > 0.2:
		next_state = &"run" if horizontal_speed > 3.0 else &"walk"
	if next_state == locomotion_state:
		return
	var previous := locomotion_state
	locomotion_state = next_state
	locomotion_state_changed.emit(previous, locomotion_state)
