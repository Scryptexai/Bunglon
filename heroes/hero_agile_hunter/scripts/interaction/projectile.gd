class_name EnergyProjectile
extends Area3D
## Reusable ranged hit delivery. It carries data; Hurtbox/DamageReceiver resolve damage.

signal impacted(target: Node3D, event: DamageEvent)
signal expired

var source: Node3D
var target: Node3D
var damage_event: DamageEvent
var direction: Vector3 = Vector3.FORWARD
var speed: float = 30.0
var max_range: float = 20.0
var homing_strength: float = 0.0
var impact_radius: float = 0.0
var pierce_remaining: int = 0
var visual_style: StringName = &"basic"
var _travelled: float = 0.0
var _hit_ids: Dictionary = {}
var _finished: bool = false
var _visual: MeshInstance3D


func launch(origin: Vector3, owner_source: Node3D, requested_target: Node3D, event: DamageEvent, options: Dictionary = {}) -> void:
	# HeroCharacter configures launch before parenting, then restores this exact world
	# origin after `add_child`. Avoid querying/setting a global transform while this
	# Area3D is outside the SceneTree.
	source = owner_source
	target = requested_target
	damage_event = event
	speed = float(options.get("speed", speed))
	max_range = float(options.get("range", max_range))
	homing_strength = float(options.get("homing", homing_strength))
	impact_radius = float(options.get("impact_radius", 0.0))
	pierce_remaining = int(options.get("pierce_count", 0))
	visual_style = StringName(options.get("visual_style", &"basic"))
	var supplied_direction: Variant = options.get("direction_override", Vector3.ZERO)
	var has_supplied_direction := false
	if supplied_direction is Vector3:
		var initial_direction: Vector3 = supplied_direction
		if initial_direction.length_squared() > 0.0001:
			direction = initial_direction.normalized()
			has_supplied_direction = true
	if not has_supplied_direction and target != null and is_instance_valid(target):
		direction = (CombatUtil.get_aim_position(target) - origin).normalized()
	if direction.length_squared() < 0.0001:
		direction = Vector3.FORWARD


func _ready() -> void:
	area_entered.connect(_on_area_entered)
	body_entered.connect(_on_body_entered)
	_build_visual()


func _physics_process(delta: float) -> void:
	if _finished:
		return
	if damage_event == null:
		_finished = true
		queue_free()
		return
	_update_homing(delta)
	var step := direction * speed * delta
	global_position += step
	_travelled += step.length()
	if direction.length_squared() > 0.0001:
		look_at(global_position + direction, Vector3.UP, true)
	_check_nearby_hurtboxes()
	if _travelled >= max_range:
		_finished = true
		expired.emit()
		queue_free()


func _update_homing(delta: float) -> void:
	if homing_strength <= 0.0 or target == null or not is_instance_valid(target):
		return
	if not CombatUtil.is_valid_hostile(source, target):
		target = null
		return
	var desired := CombatUtil.get_aim_position(target) - global_position
	if desired.length_squared() > 0.0001:
		direction = direction.slerp(desired.normalized(), minf(1.0, homing_strength * delta)).normalized()


func _check_nearby_hurtboxes() -> void:
	for candidate: Node in get_tree().get_nodes_in_group("hurtbox"):
		var hurtbox := candidate as Hurtbox
		if hurtbox == null:
			continue
		var combatant := hurtbox.get_combatant()
		if combatant == null or _hit_ids.has(combatant.get_instance_id()):
			continue
		if not CombatUtil.is_valid_hostile(source, combatant):
			continue
		if global_position.distance_to(CombatUtil.get_aim_position(combatant)) <= 0.85:
			_impact(combatant)
			if _finished:
				return


func _on_area_entered(area: Area3D) -> void:
	_impact(CombatUtil.get_combatant_root(area))


func _on_body_entered(body: Node3D) -> void:
	_impact(CombatUtil.get_combatant_root(body))


func _impact(combatant: Node3D) -> void:
	if _finished or combatant == null or not is_instance_valid(combatant):
		return
	if _hit_ids.has(combatant.get_instance_id()) or not CombatUtil.is_valid_hostile(source, combatant):
		return
	var receiver := CombatUtil.get_damage_receiver(combatant)
	if receiver == null:
		return
	_hit_ids[combatant.get_instance_id()] = true
	var resolved_event := damage_event.clone_for(combatant)
	resolved_event.impact_position = global_position
	var was_applied := receiver.receive_damage(resolved_event)
	if was_applied:
		impacted.emit(combatant, resolved_event)
		_emit_impact_vfx()
		if impact_radius > 0.0 and source != null and source.has_method("get_hitbox"):
			var radial_event := damage_event.clone_for(null)
			radial_event.impact_position = global_position
			var source_hitbox: Hitbox = source.call("get_hitbox") as Hitbox
			if source_hitbox != null:
				source_hitbox.apply_radial_damage(global_position, impact_radius, radial_event, -1, combatant)
	if pierce_remaining > 0:
		pierce_remaining -= 1
		return
	_finished = true
	queue_free()


func _emit_impact_vfx() -> void:
	if source != null and source.has_method("get_vfx"):
		var source_vfx: HeroVFXController = source.call("get_vfx") as HeroVFXController
		if source_vfx != null:
			source_vfx.play_effect(&"projectile_hit", global_position, direction, 0.7 + impact_radius * 0.15)
	if source != null and source.has_method("get_audio"):
		var source_audio: HeroAudioEmitter = source.call("get_audio") as HeroAudioEmitter
		if source_audio != null:
			source_audio.play_event(&"hit")


func _build_visual() -> void:
	_visual = MeshInstance3D.new()
	_visual.name = "EnergyArrowVisual"
	var mesh := SphereMesh.new()
	mesh.radius = 0.13 if visual_style != &"ultimate" else 0.22
	mesh.height = mesh.radius * 2.0
	_visual.mesh = mesh
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.emission_enabled = true
	material.emission_energy_multiplier = 2.6
	material.albedo_color = _style_color()
	material.emission = _style_color()
	_visual.material_override = material
	add_child(_visual)


func _style_color() -> Color:
	match visual_style:
		&"prism":
			return Color("9d7cff")
		&"snare":
			return Color("63e6d5")
		&"ultimate":
			return Color("f8ec9a")
		_:
			return Color("52e8ff")
