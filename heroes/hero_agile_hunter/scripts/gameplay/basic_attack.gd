class_name BasicAttack
extends Node
## Ranged attack flow: acquire → aim → draw → release → projectile → hit → recovery.

signal attack_prepared(target: Node3D, event: DamageEvent)
signal attack_fired(target: Node3D, event: DamageEvent)
signal attack_landed(target: Node3D, event: DamageEvent)
signal attack_cancelled

@export var windup_seconds: float = 0.20
@export var recovery_seconds: float = 0.22
@export var projectile_speed: float = 31.0

var character: HeroCharacter
var stats: StatsComponent
var targeting: TargetingComponent
var movement: MovementController
var animation_driver: HeroAnimationDriver
var vfx: HeroVFXController
var audio: HeroAudioEmitter
var _cooldown_remaining: float = 0.0
var _windup_remaining: float = 0.0
var _attack_sequence: int = 0
var _pending_target: Node3D
var _pending_event: DamageEvent


func initialize(
	owner_character: HeroCharacter,
	owner_stats: StatsComponent,
	owner_targeting: TargetingComponent,
	owner_movement: MovementController,
	owner_animation: HeroAnimationDriver,
	owner_vfx: HeroVFXController,
	owner_audio: HeroAudioEmitter
) -> void:
	character = owner_character
	stats = owner_stats
	targeting = owner_targeting
	movement = owner_movement
	animation_driver = owner_animation
	vfx = owner_vfx
	audio = owner_audio


func can_attack() -> bool:
	return _cooldown_remaining <= 0.0 and _windup_remaining <= 0.0 and character != null and character.is_combat_ready() and character.is_basic_attack_allowed()


func try_attack(preferred_target: Node3D = null) -> bool:
	if not can_attack():
		return false
	var target := preferred_target
	if target == null and targeting != null:
		target = targeting.get_target(stats.get_stat(&"attack_range"))
	if target == null:
		return false
	_pending_target = target
	_pending_event = _create_attack_event(target)
	attack_prepared.emit(target, _pending_event)
	_attack_sequence += 1
	var action_id: StringName = &"basic_attack"
	if bool(_pending_event.metadata.get("lumen_arrow", false)):
		action_id = &"charged_attack"
	elif _attack_sequence % 3 == 0:
		action_id = &"attack_variant"
	# Gameplay owns the timer and the eventual spawn. It reads the imported-manifest
	# release timing only to align its already-authoritative windup with the visual;
	# HeroPresentationAdapter's semantic signal never creates a DamageEvent itself.
	_windup_remaining = windup_seconds
	if animation_driver != null:
		_windup_remaining = maxf(0.01, animation_driver.get_semantic_event_time(action_id, &"projectile_release", windup_seconds))
		animation_driver.request_action(action_id, _windup_remaining + recovery_seconds)
	_cooldown_remaining = stats.get_attack_interval()
	movement.set_combat_facing(CombatUtil.get_aim_position(target) - character.global_position)
	if vfx != null:
		vfx.play_effect(&"attack_prepare", character.get_projectile_origin_position())
	return true


func get_cooldown_ratio() -> float:
	return clampf(_cooldown_remaining / maxf(0.01, stats.get_attack_interval()), 0.0, 1.0)


func cancel_pending() -> void:
	if _windup_remaining > 0.0:
		_cancel_pending_attack()


func _physics_process(delta: float) -> void:
	_cooldown_remaining = maxf(0.0, _cooldown_remaining - delta)
	if _windup_remaining <= 0.0:
		return
	if _pending_target == null or not is_instance_valid(_pending_target) or not CombatUtil.is_valid_hostile(character, _pending_target):
		_cancel_pending_attack()
		return
	_windup_remaining -= delta
	if _windup_remaining <= 0.0:
		_fire_pending_projectile()


func _create_attack_event(target: Node3D) -> DamageEvent:
	var event := DamageEvent.new()
	event.source = character
	event.target = target
	event.amount = stats.get_attack_damage()
	event.damage_type = DamageEvent.DamageType.PHYSICAL
	event.critical = randf() <= stats.get_stat(&"critical_chance")
	event.critical_multiplier = stats.get_stat(&"critical_damage")
	event.attack_source = &"basic_attack"
	return event


func _fire_pending_projectile() -> void:
	if _pending_event == null or _pending_target == null:
		return
	var options := {
		"speed": projectile_speed,
		"range": stats.get_stat(&"attack_range") + 3.0,
		"homing": 5.5,
		"visual_style": &"basic",
		"pierce_count": int(_pending_event.metadata.get("pierce_count", 0)),
	}
	var projectile := character.spawn_projectile(_pending_target, _pending_event, options)
	if projectile != null:
		projectile.impacted.connect(_on_projectile_impacted)
		attack_fired.emit(_pending_target, _pending_event)
	# Visual release VFX/SFX are consumed from the adapter's matching manifest marker.
	# This timer remains the one and only authoritative projectile spawn path.
	_pending_target = null
	_pending_event = null


func _cancel_pending_attack() -> void:
	_pending_target = null
	_pending_event = null
	_windup_remaining = 0.0
	attack_cancelled.emit()


func _on_projectile_impacted(target: Node3D, event: DamageEvent) -> void:
	if event.attack_source == &"basic_attack":
		attack_landed.emit(target, event)
