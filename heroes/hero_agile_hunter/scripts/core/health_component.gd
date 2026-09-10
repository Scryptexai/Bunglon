class_name HealthComponent
extends Node

signal health_changed(current_health: float, max_health: float)
signal damaged(amount: float, event: DamageEvent)
signal died(event: DamageEvent)
signal revived(current_health: float)

var max_health: float = 1.0
var current_health: float = 1.0
var regeneration_per_second: float = 0.0
var is_dead: bool = false


func initialize(stats: StatsComponent) -> void:
	max_health = maxf(1.0, stats.get_stat(&"max_health"))
	current_health = max_health
	regeneration_per_second = maxf(0.0, stats.get_stat(&"health_regen_per_second"))
	is_dead = false
	health_changed.emit(current_health, max_health)


func _physics_process(delta: float) -> void:
	if not is_dead and current_health < max_health and regeneration_per_second > 0.0:
		heal(regeneration_per_second * delta)


func apply_damage(amount: float, event: DamageEvent) -> bool:
	if is_dead or amount <= 0.0:
		return false
	current_health = maxf(0.0, current_health - amount)
	damaged.emit(amount, event)
	health_changed.emit(current_health, max_health)
	if is_zero_approx(current_health):
		is_dead = true
		died.emit(event)
	return true


func heal(amount: float) -> float:
	if is_dead or amount <= 0.0:
		return 0.0
	var before := current_health
	current_health = minf(max_health, current_health + amount)
	health_changed.emit(current_health, max_health)
	return current_health - before


func revive(health_fraction: float = 1.0) -> void:
	is_dead = false
	current_health = clampf(max_health * health_fraction, 1.0, max_health)
	health_changed.emit(current_health, max_health)
	revived.emit(current_health)


func health_ratio() -> float:
	return current_health / maxf(1.0, max_health)
