class_name StatsComponent
extends Node
## Runtime stat facade. Modifiers are data-driven and do not touch presentation nodes.

signal stat_changed(stat_name: StringName, new_value: float)

@export var base_stats: HeroStats

var runtime_stats: HeroStats
var _flat_modifiers: Dictionary = {}
var _percent_modifiers: Dictionary = {}


func initialize() -> void:
	if base_stats == null:
		base_stats = HeroStats.new()
	runtime_stats = base_stats.duplicate(true) as HeroStats


func get_stat(stat_name: StringName) -> float:
	if runtime_stats == null:
		initialize()
	var base_value: Variant = runtime_stats.get(stat_name)
	if base_value == null:
		push_warning("Unknown hero stat: %s" % stat_name)
		return 0.0
	var flat := _modifier_total(_flat_modifiers, stat_name)
	var percent := _modifier_total(_percent_modifiers, stat_name)
	return (float(base_value) + flat) * (1.0 + percent)


func set_flat_modifier(source_id: StringName, stat_name: StringName, value: float) -> void:
	var key := _modifier_key(source_id, stat_name)
	_flat_modifiers[key] = value
	_emit_stat_value(stat_name)


func set_percent_modifier(source_id: StringName, stat_name: StringName, value: float) -> void:
	var key := _modifier_key(source_id, stat_name)
	_percent_modifiers[key] = value
	_emit_stat_value(stat_name)


func clear_modifier(source_id: StringName, stat_name: StringName) -> void:
	var key := _modifier_key(source_id, stat_name)
	_flat_modifiers.erase(key)
	_percent_modifiers.erase(key)
	_emit_stat_value(stat_name)


func _modifier_key(source_id: StringName, stat_name: StringName) -> StringName:
	return StringName("%s::%s" % [source_id, stat_name])


func _modifier_total(store: Dictionary, stat_name: StringName) -> float:
	var total := 0.0
	for key: Variant in store:
		if String(key).ends_with("::%s" % stat_name):
			total += float(store[key])
	return total


func _emit_stat_value(stat_name: StringName) -> void:
	# Fold source-scoped modifiers only when a value is requested. Keeping source keys
	# lets temporary effects be removed without rebuilding a full stat sheet.
	var flat := _modifier_total(_flat_modifiers, stat_name)
	var percent := _modifier_total(_percent_modifiers, stat_name)
	var base_value := float(runtime_stats.get(stat_name))
	stat_changed.emit(stat_name, (base_value + flat) * (1.0 + percent))


func get_attack_damage() -> float:
	return get_stat(&"attack_damage")


func get_attack_speed() -> float:
	return maxf(0.05, get_stat(&"attack_speed"))


func get_attack_interval() -> float:
	return 1.0 / get_attack_speed()


func get_movement_speed() -> float:
	return maxf(0.0, get_stat(&"movement_speed"))
