class_name SlipstreamPassive
extends Node
## Passive — Slipstream Ledger
## Sustained movement builds up to three Vantage charges. A charged basic attack marks
## its prey; three marked hits on one target prime a piercing, high-damage Lumen Arrow.

signal vantage_changed(stacks: int)
signal prey_marked(target: Node3D, stacks: int)
signal lumen_arrow_primed

@export var build_seconds_per_stack: float = 0.75
@export var max_vantage_stacks: int = 3
@export var charge_bonus_ratio: float = 0.22
@export var pierce_bonus_ratio: float = 0.60

var hero: HeroCharacter
var stats: StatsComponent
var movement: MovementController
var basic_attack: BasicAttack
var vfx: HeroVFXController
var _charge_progress: float = 0.0
var _vantage_stacks: int = 0
var _marks_by_target: Dictionary = {}
var _lumen_arrow_ready: bool = false


func initialize(context: Dictionary) -> void:
	hero = context.get("hero") as HeroCharacter
	stats = context.get("stats") as StatsComponent
	movement = context.get("movement") as MovementController
	basic_attack = context.get("basic_attack") as BasicAttack
	vfx = context.get("vfx") as HeroVFXController
	if basic_attack != null:
		basic_attack.attack_prepared.connect(_on_attack_prepared)
		basic_attack.attack_landed.connect(_on_attack_landed)


func get_vantage_stacks() -> int:
	return _vantage_stacks


func is_lumen_arrow_ready() -> bool:
	return _lumen_arrow_ready


func _physics_process(delta: float) -> void:
	if hero == null or movement == null or stats == null or not hero.is_combat_ready():
		return
	var moving_fast := movement.horizontal_speed >= stats.get_movement_speed() * 0.62 or movement.is_dashing()
	if moving_fast and _vantage_stacks < max_vantage_stacks:
		_charge_progress += delta
		if _charge_progress >= build_seconds_per_stack:
			_charge_progress -= build_seconds_per_stack
			_vantage_stacks += 1
			vantage_changed.emit(_vantage_stacks)
			if vfx != null:
				vfx.play_effect(&"passive_charge", hero.global_position + Vector3.UP * 1.1)
	elif not moving_fast:
		_charge_progress = maxf(0.0, _charge_progress - delta * 0.45)


func _on_attack_prepared(_target: Node3D, event: DamageEvent) -> void:
	if _vantage_stacks > 0:
		_vantage_stacks -= 1
		vantage_changed.emit(_vantage_stacks)
		event.amount += stats.get_attack_damage() * charge_bonus_ratio
		event.metadata["slipstream_mark"] = true
		event.metadata["vantage_consumed"] = true
	if _lumen_arrow_ready:
		_lumen_arrow_ready = false
		event.amount *= 1.0 + pierce_bonus_ratio
		event.metadata["pierce_count"] = 2
		event.metadata["lumen_arrow"] = true
		if vfx != null:
			vfx.play_effect(&"lumen_ready", hero.get_projectile_origin_position())


func _on_attack_landed(target: Node3D, event: DamageEvent) -> void:
	if not bool(event.metadata.get("slipstream_mark", false)):
		return
	var target_id := target.get_instance_id()
	var marks := int(_marks_by_target.get(target_id, 0)) + 1
	_marks_by_target[target_id] = marks
	prey_marked.emit(target, marks)
	if marks >= 3:
		_marks_by_target.erase(target_id)
		_lumen_arrow_ready = true
		lumen_arrow_primed.emit()
		if vfx != null:
			vfx.play_effect(&"lumen_ready", hero.global_position + Vector3.UP * 1.4)
