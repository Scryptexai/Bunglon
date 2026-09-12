class_name TrainingDrone
extends StaticBody3D
## Lightweight hostile target used by the playable verification arena.

@export var team_id: int = 2
@export var max_health: float = 1200.0

var health: float
var damage_receiver: DamageReceiver
var statuses: StatusComponent
var _stats: StatsComponent
var _vfx: HeroVFXController
var _audio: HeroAudioEmitter


func _ready() -> void:
	add_to_group("targetable")
	set_meta("target_priority", 0.0)
	health = max_health
	_build_visual()
	_build_combat_components()


func get_team_id() -> int:
	return team_id


func get_damage_receiver() -> DamageReceiver:
	return damage_receiver


func get_aim_position() -> Vector3:
	return global_position + Vector3.UP * 1.25


func _build_combat_components() -> void:
	_stats = StatsComponent.new()
	_stats.name = "Stats"
	_stats.base_stats = HeroStats.new()
	_stats.base_stats.max_health = max_health
	_stats.base_stats.defense = 12.0
	_stats.base_stats.energy_resistance = 8.0
	add_child(_stats)
	_stats.initialize()
	var health_component := HealthComponent.new()
	health_component.name = "Health"
	add_child(health_component)
	health_component.initialize(_stats)
	health_component.died.connect(_on_died)
	statuses = StatusComponent.new()
	statuses.name = "Status"
	add_child(statuses)
	damage_receiver = DamageReceiver.new()
	damage_receiver.name = "DamageReceiver"
	add_child(damage_receiver)
	damage_receiver.initialize(self, _stats, health_component, statuses, null, null, null)
	var hurtbox := Hurtbox.new()
	hurtbox.name = "Hurtbox"
	hurtbox.collision_layer = 2
	hurtbox.collision_mask = 0
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.55
	capsule.height = 2.3
	shape.shape = capsule
	hurtbox.add_child(shape)
	add_child(hurtbox)
	hurtbox.position.y = 1.15
	hurtbox.initialize(damage_receiver)


func _build_visual() -> void:
	var body := MeshInstance3D.new()
	body.name = "DroneHull"
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.46
	capsule.height = 1.85
	body.mesh = capsule
	body.position.y = 0.95
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("6d3157")
	material.metallic = 0.5
	material.roughness = 0.27
	body.material_override = material
	add_child(body)
	var core := MeshInstance3D.new()
	core.name = "DroneCore"
	var sphere := SphereMesh.new()
	sphere.radius = 0.16
	sphere.height = 0.32
	core.mesh = sphere
	core.position = Vector3(0, 1.05, -0.43)
	var core_material := StandardMaterial3D.new()
	core_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	core_material.emission_enabled = true
	core_material.emission = Color("ff5f8f")
	core_material.emission_energy_multiplier = 2.3
	core.material_override = core_material
	add_child(core)


func _on_died(_event: DamageEvent) -> void:
	remove_from_group("targetable")
	queue_free()
