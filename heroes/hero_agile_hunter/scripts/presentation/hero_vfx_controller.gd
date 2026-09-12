class_name HeroVFXController
extends Node3D
## Low-overdraw, gameplay-first native VFX. Effects are event-driven, not combat authority.

signal effect_played(effect_id: StringName, world_position: Vector3)

var character: Node3D
var _live_effects: Array[Dictionary] = []
var _idle_aura: MeshInstance3D
var _idle_material: StandardMaterial3D
var _time: float = 0.0


func initialize(owner_character: Node3D) -> void:
	character = owner_character
	_build_idle_aura()
	play_effect(&"spawn", character.global_position + Vector3.UP * 1.0, Vector3.UP, 1.15)


func play_effect(effect_id: StringName, world_position: Vector3, direction: Vector3 = Vector3.ZERO, intensity: float = 1.0) -> void:
	var parent := _effect_parent(effect_id)
	if parent == null:
		return
	var burst := MeshInstance3D.new()
	burst.name = "%sBurst" % String(effect_id).capitalize()
	var mesh := SphereMesh.new()
	mesh.radius = 0.16
	mesh.height = 0.32
	burst.mesh = mesh
	var material := StandardMaterial3D.new()
	var color := _effect_color(effect_id)
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(color.r, color.g, color.b, 0.92)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 2.2
	burst.material_override = material
	parent.add_child(burst)
	burst.global_position = world_position
	if direction.length_squared() > 0.0001:
		var up := Vector3.UP
		if absf(direction.normalized().dot(up)) > 0.98:
			up = Vector3.FORWARD
		burst.look_at(world_position + direction, up, true)
	var duration := _effect_duration(effect_id)
	var start_scale := Vector3.ONE * (0.45 + intensity * 0.38)
	burst.scale = start_scale
	(
		_live_effects
		. append(
			{
				"node": burst,
				"material": material,
				"age": 0.0,
				"duration": duration,
				"start_scale": start_scale,
				"end_scale": Vector3.ONE * (0.9 + intensity * 1.1),
			}
		)
	)
	effect_played.emit(effect_id, world_position)


func _process(delta: float) -> void:
	_time += delta
	_update_idle_aura()
	for entry: Dictionary in _live_effects.duplicate():
		var burst := entry.get("node") as MeshInstance3D
		if burst == null or not is_instance_valid(burst):
			_live_effects.erase(entry)
			continue
		var age := float(entry.get("age", 0.0)) + delta
		var duration := float(entry.get("duration", 0.3))
		var ratio := clampf(age / duration, 0.0, 1.0)
		var start_scale: Vector3 = entry.get("start_scale", Vector3.ONE)
		var end_scale: Vector3 = entry.get("end_scale", Vector3.ONE)
		burst.scale = start_scale.lerp(end_scale, ratio)
		var material := entry.get("material") as StandardMaterial3D
		if material != null:
			var color := material.albedo_color
			color.a = (1.0 - ratio) * 0.92
			material.albedo_color = color
		if ratio >= 1.0:
			burst.queue_free()
			_live_effects.erase(entry)
		else:
			entry["age"] = age


func _build_idle_aura() -> void:
	if _idle_aura != null:
		return
	var parent := get_node_or_null("BodyEffects") as Node3D
	if parent == null:
		parent = self
	_idle_aura = MeshInstance3D.new()
	_idle_aura.name = "IdleAura"
	var mesh := CylinderMesh.new()
	mesh.top_radius = 0.55
	mesh.bottom_radius = 0.72
	mesh.height = 0.018
	_idle_aura.mesh = mesh
	_idle_material = StandardMaterial3D.new()
	_idle_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_idle_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_idle_material.albedo_color = Color(0.20, 0.88, 1.0, 0.19)
	_idle_material.emission_enabled = true
	_idle_material.emission = Color("45dfff")
	_idle_material.emission_energy_multiplier = 1.25
	_idle_aura.material_override = _idle_material
	parent.add_child(_idle_aura)
	_idle_aura.position = Vector3(0.0, 0.04, 0.0)


func _update_idle_aura() -> void:
	if _idle_aura == null or _idle_material == null:
		return
	var pulse := 1.0 + sin(_time * 2.0) * 0.08
	_idle_aura.scale = Vector3(pulse, 1.0, pulse)
	_idle_aura.rotation.y += get_process_delta_time() * 0.55
	var color := _idle_material.albedo_color
	color.a = 0.14 + (sin(_time * 2.0) + 1.0) * 0.045
	_idle_material.albedo_color = color


func _effect_parent(effect_id: StringName) -> Node3D:
	var effect_name := String(effect_id)
	if effect_name.contains("death"):
		return get_node_or_null("DeathEffects") as Node3D
	if effect_name.begins_with("skill") or effect_name.begins_with("ultimate"):
		return get_node_or_null("SkillEffects") as Node3D
	if effect_name.contains("attack") or effect_name.contains("projectile"):
		return get_node_or_null("AttackEffects") as Node3D
	return get_node_or_null("BodyEffects") as Node3D


func _effect_color(effect_id: StringName) -> Color:
	var effect_name := String(effect_id)
	if effect_name.begins_with("ultimate"):
		return Color("ffe58a")
	if effect_name.contains("snare") or effect_name.contains("skill_03"):
		return Color("5fe5cf")
	if effect_name.contains("phase") or effect_name.contains("skill_02"):
		return Color("a88bff")
	if effect_name.contains("hit") or effect_name.contains("death"):
		return Color("ff8c97")
	return Color("52e8ff")


func _effect_duration(effect_id: StringName) -> float:
	var effect_name := String(effect_id)
	if effect_name.begins_with("ultimate"):
		return 0.52
	if effect_name.contains("death"):
		return 0.85
	return 0.24
