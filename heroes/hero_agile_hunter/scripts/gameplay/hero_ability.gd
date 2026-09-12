class_name HeroAbility
extends Node
## Shared ability lifecycle: cast → activation → action → recovery → cooldown.

signal cast_started(ability: HeroAbility, target: Node3D)
signal activated(ability: HeroAbility, target: Node3D)
signal action_executed(ability: HeroAbility, target: Node3D)
signal recovery_started(ability: HeroAbility)
signal finished(ability: HeroAbility)
signal failed(ability: HeroAbility, reason: StringName)

enum Phase {
	READY,
	CAST,
	ACTION,
	RECOVERY,
}

@export var slot_id: StringName = &"ability"
@export var display_name: String = "Ability"
@export_multiline var description: String = ""
@export var energy_cost: float = 0.0
@export var cooldown_seconds: float = 1.0
@export var range: float = 12.0
@export var requires_target: bool = true
@export var cast_seconds: float = 0.15
@export var action_seconds: float = 0.0
@export var recovery_seconds: float = 0.2
@export var locks_movement: bool = false
@export var blocks_basic_attack: bool = false
@export var animation_id: StringName = &"skill_cast"
# These query the validated Phase 5 manifest through HeroAnimationDriver once at
# activation. They are timing data for authoritative gameplay timers, not subscriptions
# to presentation signals; an interrupted/replaced visual can never dispatch damage.
@export var action_timing_event: StringName = &""
@export var recovery_timing_event: StringName = &"recovery_open"

var hero: HeroCharacter
var stats: StatsComponent
var energy: EnergyComponent
var targeting: TargetingComponent
var movement: MovementController
var animation_driver: HeroAnimationDriver
var vfx: HeroVFXController
var audio: HeroAudioEmitter
var hitbox: Hitbox
var phase: Phase = Phase.READY
var cooldown_remaining: float = 0.0
var _phase_remaining: float = 0.0
var _cast_target: Node3D
var _cast_aim: Vector3 = Vector3.ZERO
var _resolved_cast_seconds: float = 0.0
var _resolved_action_seconds: float = 0.0
var _resolved_recovery_seconds: float = 0.0


func initialize(context: Dictionary) -> void:
	hero = context.get("hero") as HeroCharacter
	stats = context.get("stats") as StatsComponent
	energy = context.get("energy") as EnergyComponent
	targeting = context.get("targeting") as TargetingComponent
	movement = context.get("movement") as MovementController
	animation_driver = context.get("animation") as HeroAnimationDriver
	vfx = context.get("vfx") as HeroVFXController
	audio = context.get("audio") as HeroAudioEmitter
	hitbox = context.get("hitbox") as Hitbox


func is_ready() -> bool:
	return phase == Phase.READY and cooldown_remaining <= 0.0 and hero != null and hero.is_combat_ready()


func cooldown_ratio() -> float:
	return clampf(cooldown_remaining / maxf(0.01, cooldown_seconds), 0.0, 1.0)


func try_activate(requested_target: Node3D, aim_direction: Vector3) -> bool:
	if not is_ready():
		failed.emit(self, &"cooldown_or_busy")
		return false
	var resolved_target := _resolve_target(requested_target)
	if requires_target and resolved_target == null:
		failed.emit(self, &"no_target")
		return false
	# Directional/self abilities may receive the controller's currently selected combat
	# target for aiming, but that optional target must not make a range-zero ability
	# fail. Only an ability that explicitly requires a target owns target-range gating.
	if requires_target and resolved_target != null and not _target_in_range(resolved_target):
		failed.emit(self, &"out_of_range")
		return false
	if energy != null and not energy.try_spend(energy_cost):
		failed.emit(self, &"insufficient_energy")
		return false
	_cast_target = resolved_target
	_cast_aim = _resolve_aim(aim_direction, resolved_target)
	_resolve_phase_timing()
	cooldown_remaining = cooldown_seconds
	phase = Phase.CAST
	_phase_remaining = _resolved_cast_seconds
	if locks_movement and movement != null:
		movement.set_action_lock(slot_id, true)
	if movement != null and _cast_aim.length_squared() > 0.0001:
		movement.set_combat_facing(_cast_aim)
	if animation_driver != null:
		animation_driver.request_action(animation_id, _resolved_cast_seconds + _resolved_action_seconds + _resolved_recovery_seconds)
	cast_started.emit(self, _cast_target)
	_on_cast_started()
	if _resolved_cast_seconds <= 0.0:
		_enter_action()
	return true


func cancel(reason: StringName = &"cancelled") -> void:
	if phase == Phase.READY:
		return
	phase = Phase.READY
	_phase_remaining = 0.0
	_cast_target = null
	if locks_movement and movement != null:
		movement.set_action_lock(slot_id, false)
	failed.emit(self, reason)


func _physics_process(delta: float) -> void:
	cooldown_remaining = maxf(0.0, cooldown_remaining - delta)
	if phase == Phase.READY:
		return
	_phase_remaining -= delta
	match phase:
		Phase.CAST:
			if requires_target and (_cast_target == null or not is_instance_valid(_cast_target) or not CombatUtil.is_valid_hostile(hero, _cast_target)):
				cancel(&"target_lost")
				return
			if _phase_remaining <= 0.0:
				_enter_action()
		Phase.ACTION:
			_update_action(delta)
			if _phase_remaining <= 0.0:
				_enter_recovery()
		Phase.RECOVERY:
			if _phase_remaining <= 0.0:
				_finish()


func _enter_action() -> void:
	phase = Phase.ACTION
	_phase_remaining = _resolved_action_seconds
	activated.emit(self, _cast_target)
	_execute_action()
	action_executed.emit(self, _cast_target)
	if _resolved_action_seconds <= 0.0:
		_enter_recovery()


func _enter_recovery() -> void:
	phase = Phase.RECOVERY
	_phase_remaining = _resolved_recovery_seconds
	recovery_started.emit(self)
	_on_recovery_started()
	if _resolved_recovery_seconds <= 0.0:
		_finish()


func _finish() -> void:
	phase = Phase.READY
	_phase_remaining = 0.0
	_cast_target = null
	if locks_movement and movement != null:
		movement.set_action_lock(slot_id, false)
	finished.emit(self)


func _resolve_target(requested_target: Node3D) -> Node3D:
	if requested_target != null and CombatUtil.is_valid_hostile(hero, requested_target):
		return requested_target
	if targeting != null:
		return targeting.get_target(range)
	return null


func _target_in_range(target: Node3D) -> bool:
	return hero.global_position.distance_to(target.global_position) <= range


func _resolve_aim(aim_direction: Vector3, target: Node3D) -> Vector3:
	if target != null:
		var toward_target := CombatUtil.get_aim_position(target) - hero.global_position
		toward_target.y = 0.0
		if toward_target.length_squared() > 0.0001:
			return toward_target.normalized()
	aim_direction.y = 0.0
	if aim_direction.length_squared() > 0.0001:
		return aim_direction.normalized()
	return -hero.global_transform.basis.z


func get_authored_event_time(event_id: StringName, fallback: float = -1.0) -> float:
	if event_id.is_empty() or animation_driver == null:
		return fallback
	return animation_driver.get_semantic_event_time(animation_id, event_id, fallback)


func get_action_event_offset(event_id: StringName, fallback: float = 0.0) -> float:
	var event_time := get_authored_event_time(event_id, -1.0)
	if event_time < 0.0:
		return maxf(0.0, fallback)
	return maxf(0.0, event_time - _resolved_cast_seconds)


func _resolve_phase_timing() -> void:
	_resolved_cast_seconds = maxf(0.0, cast_seconds)
	_resolved_action_seconds = maxf(0.0, action_seconds)
	_resolved_recovery_seconds = maxf(0.0, recovery_seconds)
	var action_time := get_authored_event_time(action_timing_event, -1.0)
	if action_time < 0.0:
		return
	_resolved_cast_seconds = action_time
	var recovery_time := get_authored_event_time(recovery_timing_event, -1.0)
	if recovery_time < action_time:
		return
	_resolved_action_seconds = recovery_time - action_time
	var clip_duration := animation_driver.get_clip_duration(animation_id) if animation_driver != null else 0.0
	if clip_duration >= recovery_time:
		_resolved_recovery_seconds = clip_duration - recovery_time


func _on_cast_started() -> void:
	pass


func _execute_action() -> void:
	pass


func _update_action(_delta: float) -> void:
	pass


func _on_recovery_started() -> void:
	pass
