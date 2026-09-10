class_name HeroVisual
extends Node3D
## Native Godot 3D presentation for Lyra Vesper, the Lumen Huntress.
##
## The assembled mesh is intentionally modular: each silhouette piece is attached to a
## named Skeleton3D bone, and an imported skinned asset can replace these modules without
## changing gameplay, abilities, or camera paths.

var skeleton: Skeleton3D
var character_model: Node3D
var weapon: Node3D
var accessories: Node3D
var projectile_origin: Marker3D
var _attachments: Dictionary = {}
var _materials: Dictionary = {}
var _built: bool = false


func initialize() -> void:
	if _built:
		return
	character_model = get_node_or_null("CharacterModel") as Node3D
	if character_model == null:
		character_model = Node3D.new()
		character_model.name = "CharacterModel"
		add_child(character_model)
	skeleton = character_model.get_node_or_null("Skeleton") as Skeleton3D
	if skeleton == null:
		skeleton = Skeleton3D.new()
		skeleton.name = "Skeleton"
		character_model.add_child(skeleton)
	weapon = character_model.get_node_or_null("Weapon") as Node3D
	if weapon == null:
		weapon = Node3D.new()
		weapon.name = "Weapon"
		character_model.add_child(weapon)
	accessories = character_model.get_node_or_null("Accessories") as Node3D
	if accessories == null:
		accessories = Node3D.new()
		accessories.name = "Accessories"
		character_model.add_child(accessories)
	_build_material_palette()
	_build_skeleton()
	_build_body_modules()
	_build_accessories()
	_build_energy_bow()
	_built = true


func get_skeleton() -> Skeleton3D:
	return skeleton


func get_projectile_origin() -> Marker3D:
	return projectile_origin


func update_weapon_pose() -> void:
	var hand := _attachments.get(&"hand_r") as Node3D
	if hand == null or weapon == null:
		return
	weapon.global_transform = (
		hand.global_transform * Transform3D(Basis.from_euler(Vector3(deg_to_rad(8.0), deg_to_rad(18.0), deg_to_rad(-82.0))), Vector3(0.04, -0.03, -0.02))
	)


func _build_material_palette() -> void:
	_materials[&"skin"] = _material(Color("b98578"), 0.0, 0.78)
	_materials[&"hair"] = _material(Color("10142a"), 0.0, 0.30)
	_materials[&"suit"] = _material(Color("20284f"), 0.05, 0.42)
	_materials[&"armor"] = _material(Color("405084"), 0.58, 0.25)
	_materials[&"leather"] = _material(Color("332a46"), 0.0, 0.82)
	_materials[&"metal"] = _material(Color("9eb5d4"), 0.90, 0.16)
	_materials[&"energy"] = _material(Color("55e8ff"), 0.15, 0.18, Color("3ee8ff"), 2.8)
	_materials[&"violet_energy"] = _material(Color("a184ff"), 0.08, 0.20, Color("926cff"), 2.1)
	_materials[&"gold_energy"] = _material(Color("ffe89a"), 0.2, 0.20, Color("ffd45c"), 2.2)


func _build_skeleton() -> void:
	if skeleton.get_bone_count() > 0:
		return
	var bones := [
		[&"root", -1, Vector3(0.0, 0.0, 0.0)],
		[&"hips", 0, Vector3(0.0, 0.85, 0.0)],
		[&"spine", 1, Vector3(0.0, 0.35, 0.0)],
		[&"chest", 2, Vector3(0.0, 0.34, 0.0)],
		[&"neck", 3, Vector3(0.0, 0.22, 0.0)],
		[&"head", 4, Vector3(0.0, 0.10, 0.0)],
		[&"shoulder_l", 3, Vector3(-0.30, 0.20, 0.0)],
		[&"upper_arm_l", 6, Vector3(-0.24, -0.02, 0.0)],
		[&"forearm_l", 7, Vector3(-0.03, -0.34, 0.0)],
		[&"hand_l", 8, Vector3(0.0, -0.31, 0.0)],
		[&"shoulder_r", 3, Vector3(0.30, 0.20, 0.0)],
		[&"upper_arm_r", 10, Vector3(0.24, -0.02, 0.0)],
		[&"forearm_r", 11, Vector3(0.03, -0.34, 0.0)],
		[&"hand_r", 12, Vector3(0.0, -0.31, 0.0)],
		[&"upper_leg_l", 1, Vector3(-0.20, -0.10, 0.0)],
		[&"lower_leg_l", 14, Vector3(0.0, -0.47, 0.03)],
		[&"foot_l", 15, Vector3(0.0, -0.25, -0.09)],
		[&"upper_leg_r", 1, Vector3(0.20, -0.10, 0.0)],
		[&"lower_leg_r", 17, Vector3(0.0, -0.47, 0.03)],
		[&"foot_r", 18, Vector3(0.0, -0.25, -0.09)],
	]
	for bone_data: Array in bones:
		var index := skeleton.add_bone(bone_data[0])
		var parent_index: int = bone_data[1]
		if parent_index >= 0:
			skeleton.set_bone_parent(index, parent_index)
		skeleton.set_bone_rest(index, Transform3D(Basis.IDENTITY, bone_data[2]))
	skeleton.reset_bone_poses()
	for bone_data: Array in bones:
		var bone_name: StringName = bone_data[0]
		_attachments[bone_name] = _make_attachment(bone_name)


func _build_body_modules() -> void:
	# Athletic, light silhouette: narrow waist, angular shoulder plates and long legs.
	_add_capsule(_attachments[&"spine"], "TorsoSuit", 0.28, 0.84, _materials[&"suit"], Vector3(0, 0.22, 0))
	_add_box(_attachments[&"chest"], "ChestArmor", Vector3(0.62, 0.42, 0.24), _materials[&"armor"], Vector3(0, 0.11, -0.015))
	_add_box(_attachments[&"chest"], "LumenCore", Vector3(0.14, 0.18, 0.035), _materials[&"energy"], Vector3(0, 0.08, -0.15), Vector3(0, 0, deg_to_rad(45)))
	_add_capsule(_attachments[&"hips"], "WaistSuit", 0.25, 0.42, _materials[&"suit"], Vector3(0, 0.0, 0))
	_add_sphere(_attachments[&"head"], "Face", 0.27, _materials[&"skin"], Vector3(0, 0.19, -0.015))
	_add_box(_attachments[&"head"], "Visor", Vector3(0.45, 0.095, 0.06), _materials[&"energy"], Vector3(0, 0.23, -0.25))
	_add_capsule(_attachments[&"head"], "HairCrown", 0.28, 0.24, _materials[&"hair"], Vector3(0, 0.37, 0.02))
	_add_cone(_attachments[&"head"], "Crest", 0.13, 0.03, 0.48, _materials[&"hair"], Vector3(0, 0.63, 0.05), Vector3(deg_to_rad(-10), 0, 0))
	_build_limb(&"upper_arm_l", &"forearm_l", &"hand_l", "L", -1.0)
	_build_limb(&"upper_arm_r", &"forearm_r", &"hand_r", "R", 1.0)
	_build_leg(&"upper_leg_l", &"lower_leg_l", &"foot_l", "L")
	_build_leg(&"upper_leg_r", &"lower_leg_r", &"foot_r", "R")


func _build_limb(upper: StringName, forearm: StringName, hand: StringName, side: String, side_sign: float) -> void:
	_add_capsule(_attachments[upper], "UpperArm%s" % side, 0.115, 0.48, _materials[&"suit"], Vector3(0, -0.20, 0))
	_add_box(_attachments[upper], "ShoulderPlate%s" % side, Vector3(0.25, 0.16, 0.22), _materials[&"armor"], Vector3(side_sign * 0.07, 0.04, 0))
	_add_capsule(_attachments[forearm], "Forearm%s" % side, 0.095, 0.44, _materials[&"armor"], Vector3(0, -0.18, 0))
	_add_sphere(_attachments[hand], "Glove%s" % side, 0.11, _materials[&"leather"], Vector3(0, -0.05, 0))


func _build_leg(upper: StringName, lower: StringName, foot: StringName, side: String) -> void:
	_add_capsule(_attachments[upper], "Thigh%s" % side, 0.145, 0.62, _materials[&"suit"], Vector3(0, -0.25, 0))
	_add_box(_attachments[upper], "ThighGuard%s" % side, Vector3(0.25, 0.32, 0.20), _materials[&"armor"], Vector3(0, -0.13, -0.055))
	_add_capsule(_attachments[lower], "Shin%s" % side, 0.115, 0.56, _materials[&"armor"], Vector3(0, -0.23, 0))
	_add_box(_attachments[foot], "Boot%s" % side, Vector3(0.23, 0.16, 0.42), _materials[&"leather"], Vector3(0, -0.05, -0.12))


func _build_accessories() -> void:
	# Long asymmetric mantle and a swept ponytail make the hero readable at camera distance.
	var hips := _attachments[&"hips"] as Node3D
	var head := _attachments[&"head"] as Node3D
	_add_box(
		hips, "AuroraMantle", Vector3(0.34, 0.98, 0.08), _materials[&"violet_energy"], Vector3(-0.28, -0.48, 0.14), Vector3(deg_to_rad(-13), 0, deg_to_rad(9))
	)
	_add_box(hips, "MantleTrim", Vector3(0.055, 1.03, 0.05), _materials[&"energy"], Vector3(-0.46, -0.49, 0.085), Vector3(deg_to_rad(-13), 0, deg_to_rad(9)))
	_add_capsule(head, "PonytailA", 0.09, 0.55, _materials[&"hair"], Vector3(0.03, -0.15, 0.22), Vector3(deg_to_rad(28), 0, 0))
	_add_capsule(head, "PonytailGlow", 0.025, 0.46, _materials[&"violet_energy"], Vector3(0.03, -0.16, 0.29), Vector3(deg_to_rad(28), 0, 0))
	var quiver := Node3D.new()
	quiver.name = "PrismQuiver"
	accessories.add_child(quiver)
	quiver.position = Vector3(0.33, 1.41, 0.19)
	quiver.rotation = Vector3(deg_to_rad(-18), 0, deg_to_rad(-12))
	_add_box(quiver, "QuiverCase", Vector3(0.18, 0.62, 0.17), _materials[&"leather"], Vector3.ZERO)
	for index: int in 3:
		_add_capsule(quiver, "EnergyArrow%02d" % index, 0.022, 0.70, _materials[&"energy"], Vector3(-0.045 + index * 0.045, 0.17, 0.02))


func _build_energy_bow() -> void:
	weapon.position = Vector3(0.42, 1.25, -0.16)
	_add_capsule(weapon, "BowGrip", 0.055, 0.35, _materials[&"leather"], Vector3.ZERO)
	_add_capsule(weapon, "UpperBowLimb", 0.045, 1.18, _materials[&"metal"], Vector3(0.18, 0.47, 0), Vector3(0, 0, deg_to_rad(-22)))
	_add_capsule(weapon, "LowerBowLimb", 0.045, 1.18, _materials[&"metal"], Vector3(0.18, -0.47, 0), Vector3(0, 0, deg_to_rad(22)))
	_add_capsule(weapon, "EnergyString", 0.014, 1.75, _materials[&"energy"], Vector3(0.36, 0, 0), Vector3(0, 0, deg_to_rad(2)))
	_add_sphere(weapon, "BowCore", 0.10, _materials[&"energy"], Vector3(0.07, 0, -0.015))
	projectile_origin = Marker3D.new()
	projectile_origin.name = "ProjectileOrigin"
	weapon.add_child(projectile_origin)
	projectile_origin.position = Vector3(0.10, 0.02, -0.10)


func _make_attachment(bone_name: StringName) -> BoneAttachment3D:
	var attachment := BoneAttachment3D.new()
	attachment.name = "%sAttachment" % String(bone_name).capitalize()
	attachment.bone_name = bone_name
	skeleton.add_child(attachment)
	return attachment


func _material(
	color: Color, metallic: float, roughness: float, emission_color: Color = Color(0.0, 0.0, 0.0, 0.0), emission_energy: float = 0.0
) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = metallic
	material.roughness = roughness
	if emission_energy > 0.0:
		material.emission_enabled = true
		material.emission = emission_color
		material.emission_energy_multiplier = emission_energy
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return material


func _add_capsule(
	parent: Node, name_id: String, radius: float, height: float, material: Material, position: Vector3, rotation: Vector3 = Vector3.ZERO
) -> MeshInstance3D:
	var mesh := CapsuleMesh.new()
	mesh.radius = radius
	mesh.height = height
	return _add_mesh(parent, name_id, mesh, material, position, rotation)


func _add_sphere(parent: Node, name_id: String, radius: float, material: Material, position: Vector3) -> MeshInstance3D:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2.0
	return _add_mesh(parent, name_id, mesh, material, position)


func _add_box(parent: Node, name_id: String, size: Vector3, material: Material, position: Vector3, rotation: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	return _add_mesh(parent, name_id, mesh, material, position, rotation)


func _add_cone(
	parent: Node,
	name_id: String,
	top_radius: float,
	bottom_radius: float,
	height: float,
	material: Material,
	position: Vector3,
	rotation: Vector3 = Vector3.ZERO
) -> MeshInstance3D:
	var mesh := CylinderMesh.new()
	mesh.top_radius = top_radius
	mesh.bottom_radius = bottom_radius
	mesh.height = height
	return _add_mesh(parent, name_id, mesh, material, position, rotation)


func _add_mesh(parent: Node, name_id: String, mesh: Mesh, material: Material, position: Vector3, rotation: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = name_id
	instance.mesh = mesh
	instance.material_override = material
	instance.position = position
	instance.rotation = rotation
	instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	parent.add_child(instance)
	return instance
