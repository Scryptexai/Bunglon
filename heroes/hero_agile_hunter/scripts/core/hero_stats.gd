class_name HeroStats
extends Resource
## Authoring data only. Runtime modifiers are owned by StatsComponent, never by the model.

@export_group("Survivability")
@export var max_health: float = 1080.0
@export var health_regen_per_second: float = 2.0
@export var defense: float = 24.0
@export var energy_resistance: float = 10.0

@export_group("Basic Attack")
@export var attack_damage: float = 78.0
@export var attack_speed: float = 0.88
@export var critical_chance: float = 0.15
@export var critical_damage: float = 1.75
@export var attack_range: float = 18.0

@export_group("Ability and Mobility")
@export var skill_damage: float = 92.0
@export var movement_speed: float = 6.6
@export var turn_speed: float = 14.0
@export var max_energy: float = 360.0
@export var energy_regen_per_second: float = 17.0

@export_group("Progression")
@export var level: int = 1
@export var experience: int = 0
