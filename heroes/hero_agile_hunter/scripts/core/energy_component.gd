class_name EnergyComponent
extends Node

signal energy_changed(current_energy: float, max_energy: float)
signal energy_spent(amount: float)
signal energy_insufficient(required: float, available: float)

var max_energy: float = 1.0
var current_energy: float = 1.0
var regeneration_per_second: float = 0.0


func initialize(stats: StatsComponent) -> void:
	max_energy = maxf(1.0, stats.get_stat(&"max_energy"))
	current_energy = max_energy
	regeneration_per_second = stats.get_stat(&"energy_regen_per_second")
	energy_changed.emit(current_energy, max_energy)


func _physics_process(delta: float) -> void:
	if current_energy >= max_energy:
		return
	current_energy = minf(max_energy, current_energy + regeneration_per_second * delta)
	energy_changed.emit(current_energy, max_energy)


func can_spend(amount: float) -> bool:
	return current_energy + 0.001 >= amount


func try_spend(amount: float) -> bool:
	if not can_spend(amount):
		energy_insufficient.emit(amount, current_energy)
		return false
	current_energy = maxf(0.0, current_energy - amount)
	energy_spent.emit(amount)
	energy_changed.emit(current_energy, max_energy)
	return true


func restore(amount: float) -> float:
	var before := current_energy
	current_energy = minf(max_energy, current_energy + maxf(0.0, amount))
	energy_changed.emit(current_energy, max_energy)
	return current_energy - before


func energy_ratio() -> float:
	return current_energy / maxf(1.0, max_energy)
