class_name HeroCharacter
extends CharacterBody3D
## Thin composition root for Lyra Vesper.
## It wires modular components and deliberately contains no combat mechanics itself.

signal hero_died(source_event: DamageEvent)
signal hero_revived
signal control_mode_changed(mode: StringName)

const PROJECTILE_SCENE := preload("res://heroes/hero_agile_hunter/scenes/energy_projectile.tscn")

@export_enum("player", "ai", "external") var control_mode: String = "player"
@export var team_id: int = 1
@export var hero_id: StringName = &"lyra_vesper"

var stats: StatsComponent
var health: HealthComponent
var energy: EnergyComponent
var statuses: StatusComponent
var team: TeamComponent
var visual: HeroVisual
var animation_driver: HeroAnimationDriver
var movement: MovementController
var targeting: TargetingComponent
var damage_receiver: DamageReceiver
var basic_attack: BasicAttack
var ability_controller: AbilityController
var passive: SlipstreamPassive
var controller: CharacterController
var hurtbox: Hurtbox
var hitbox: Hitbox
var detection: DetectionSensor
var vfx: HeroVFXController
var audio: HeroAudioEmitter
var camera_target: HeroCameraTarget
var _initialized: bool = false


func _ready() -> void:
	add_to_group("targetable")
	set_meta("target_priority", 0.0)
	_cache_components()
	_initialize_components()


func set_control_mode(next_mode: StringName) -> void:
	if next_mode not in [&"player", &"ai", &"external"]:
		push_warning("Unsupported control mode: %s" % next_mode)
		return
	control_mode = String(next_mode)
	control_mode_changed.emit(next_mode)


func get_control_mode() -> StringName:
	return StringName(control_mode)


func get_team_id() -> int:
	return team.team_id if team != null else team_id


func get_damage_receiver() -> DamageReceiver:
	return damage_receiver


func get_targeting() -> TargetingComponent:
	return targeting


func get_statuses() -> StatusComponent:
	return statuses


func get_hitbox() -> Hitbox:
	return hitbox


func get_vfx() -> HeroVFXController:
	return vfx


func get_audio() -> HeroAudioEmitter:
	return audio


func get_attack_range() -> float:
	return stats.get_stat(&"attack_range") if stats != null else 0.0


func get_health_ratio() -> float:
	return health.health_ratio() if health != null else 0.0


func get_aim_position() -> Vector3:
	return camera_target.get_aim_point() if camera_target != null else global_position + Vector3.UP * 1.4


func get_projectile_origin_position() -> Vector3:
	var origin := visual.get_projectile_origin() if visual != null else null
	return origin.global_position if origin != null else global_position + Vector3.UP * 1.35 - global_transform.basis.z * 0.45


func is_combat_ready() -> bool:
	return _initialized and health != null and not health.is_dead


func is_basic_attack_allowed() -> bool:
	return ability_controller == null or ability_controller.is_basic_attack_allowed()


func spawn_projectile(target: Node3D, event: DamageEvent, options: Dictionary = {}) -> EnergyProjectile:
	if not is_combat_ready():
		return null
	var projectile := PROJECTILE_SCENE.instantiate() as EnergyProjectile
	if projectile == null:
		return null
	var origin := get_projectile_origin_position()
	projectile.launch(origin, self, target, event, options)
	var world: Node = get_tree().current_scene if get_tree().current_scene != null else get_parent()
	world.add_child(projectile)
	# launch() runs before _ready so visual style is known; restore the world-space
	# origin after parenting in case the scene root itself carries a transform.
	projectile.global_position = origin
	if audio != null:
		audio.play_event(&"projectile")
	return projectile


func revive(health_fraction: float = 1.0) -> void:
	if health == null:
		return
	health.revive(health_fraction)


func _cache_components() -> void:
	stats = get_node_or_null("Stats") as StatsComponent
	health = get_node_or_null("Health") as HealthComponent
	energy = get_node_or_null("Energy") as EnergyComponent
	statuses = get_node_or_null("Status") as StatusComponent
	team = get_node_or_null("Team") as TeamComponent
	visual = get_node_or_null("Visual") as HeroVisual
	animation_driver = get_node_or_null("Animation") as HeroAnimationDriver
	movement = get_node_or_null("Movement") as MovementController
	targeting = get_node_or_null("Combat/Targeting") as TargetingComponent
	damage_receiver = get_node_or_null("Combat/DamageReceiver") as DamageReceiver
	basic_attack = get_node_or_null("Combat/BasicAttack") as BasicAttack
	ability_controller = get_node_or_null("Combat/AbilityController") as AbilityController
	passive = get_node_or_null("Abilities/Passive") as SlipstreamPassive
	controller = get_node_or_null("Control/CharacterController") as CharacterController
	hurtbox = get_node_or_null("Collision/Hurtbox") as Hurtbox
	hitbox = get_node_or_null("Collision/Hitbox") as Hitbox
	detection = get_node_or_null("Detection") as DetectionSensor
	vfx = get_node_or_null("VFX") as HeroVFXController
	audio = get_node_or_null("Audio") as HeroAudioEmitter
	camera_target = get_node_or_null("CameraTarget") as HeroCameraTarget


func _initialize_components() -> void:
	if stats == null or health == null or visual == null:
		push_error("HeroCharacter scene is missing required components.")
		return
	stats.initialize()
	if team != null:
		team.team_id = team_id
	visual.initialize()
	animation_driver.initialize(visual, movement)
	movement.initialize(self, stats, statuses, animation_driver)
	health.initialize(stats)
	energy.initialize(stats)
	audio.initialize()
	movement.footstep.connect(_on_footstep)
	vfx.initialize(self)
	damage_receiver.initialize(self, stats, health, statuses, animation_driver, vfx, audio)
	hurtbox.initialize(damage_receiver)
	targeting.initialize(self, detection)
	basic_attack.initialize(self, stats, targeting, movement, animation_driver, vfx, audio)
	var context := {
		"hero": self,
		"stats": stats,
		"energy": energy,
		"targeting": targeting,
		"movement": movement,
		"animation": animation_driver,
		"vfx": vfx,
		"audio": audio,
		"hitbox": hitbox,
		"basic_attack": basic_attack,
	}
	passive.initialize(context)
	ability_controller.initialize(context, get_node_or_null("Abilities"))
	controller.initialize(self, movement, targeting, basic_attack, ability_controller, statuses)
	health.died.connect(_on_health_died)
	health.revived.connect(_on_health_revived)
	_initialized = true
	animation_driver.play_spawn()
	audio.play_event(&"voice")


func _on_footstep() -> void:
	if audio != null:
		audio.play_event(&"movement")


func _on_health_died(event: DamageEvent) -> void:
	if not _initialized:
		return
	statuses.apply_status(&"death", 9999.0, 1.0, self)
	movement.force_stop()
	controller.set_enabled(false)
	basic_attack.cancel_pending()
	ability_controller.cancel_all(&"owner_dead")
	animation_driver.play_death()
	vfx.play_effect(&"death", global_position + Vector3.UP * 1.0, Vector3.UP, 1.4)
	audio.play_event(&"death")
	hero_died.emit(event)


func _on_health_revived(_current_health: float) -> void:
	statuses.remove_status(&"death")
	controller.set_enabled(true)
	animation_driver.play_spawn()
	hero_revived.emit()
