class_name HeroDemoHUD
extends Control
## Functional HUD and optional button bridge for touch devices.

var hero: HeroCharacter
var _health_bar: ProgressBar
var _energy_bar: ProgressBar
var _status: Label
var _mobile_panel: Control
var _movement_held: Dictionary = {&"left": false, &"right": false, &"forward": false, &"back": false}


func _ready() -> void:
	_build_desktop_hud()
	_build_mobile_controls()


func set_hero(next_hero: HeroCharacter) -> void:
	hero = next_hero


func _process(_delta: float) -> void:
	if hero == null or not is_instance_valid(hero) or not hero.is_combat_ready():
		return
	_health_bar.value = hero.health.health_ratio() * 100.0
	_energy_bar.value = hero.energy.energy_ratio() * 100.0
	var target := hero.get_targeting().get_target() if hero.get_targeting() != null else null
	var target_name := target.name if target != null else "None"
	_status.text = (
		"LYRA VESPER  |  Target: %s\nQ Prism Volley  •  E Phase Step  •  R Tether Snare  •  F Apex Constellation\nPassive Vantage: %d  |  Basic: %d%%"
		% [
			target_name,
			hero.passive.get_vantage_stacks(),
			int((1.0 - hero.basic_attack.get_cooldown_ratio()) * 100.0),
		]
	)


func _build_desktop_hud() -> void:
	var panel := ColorRect.new()
	panel.color = Color(0.035, 0.05, 0.12, 0.72)
	panel.position = Vector2(18, 16)
	panel.size = Vector2(470, 112)
	add_child(panel)
	var title := Label.new()
	title.text = "LUMEN HUNTRESS // PLAYABLE HERO DEMO"
	title.position = Vector2(14, 10)
	title.add_theme_color_override("font_color", Color("79eaff"))
	panel.add_child(title)
	_health_bar = _make_bar(Color("e95a71"), Vector2(14, 35), "HP")
	panel.add_child(_health_bar)
	_energy_bar = _make_bar(Color("6ce3ff"), Vector2(14, 58), "ENERGY")
	panel.add_child(_energy_bar)
	_status = Label.new()
	_status.position = Vector2(14, 80)
	_status.size = Vector2(450, 52)
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.add_theme_font_size_override("font_size", 12)
	panel.add_child(_status)
	var help := Label.new()
	help.text = "WASD move • Space basic attack • Tab cycle target\nTouch controls appear on mobile."
	help.position = Vector2(18, 142)
	help.add_theme_color_override("font_color", Color("d4ddff"))
	add_child(help)


func _make_bar(color: Color, position_value: Vector2, label_text: String) -> ProgressBar:
	var bar := ProgressBar.new()
	bar.position = position_value
	bar.size = Vector2(440, 16)
	bar.max_value = 100.0
	bar.value = 100.0
	bar.show_percentage = false
	bar.tooltip_text = label_text
	bar.add_theme_color_override("font_color", color)
	return bar


func _build_mobile_controls() -> void:
	_mobile_panel = Control.new()
	_mobile_panel.name = "MobileControls"
	_mobile_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_mobile_panel.mouse_filter = Control.MOUSE_FILTER_PASS
	_mobile_panel.visible = OS.has_feature("mobile")
	add_child(_mobile_panel)
	_make_direction_button("◀", &"left", Vector2(54, 610))
	_make_direction_button("▶", &"right", Vector2(166, 610))
	_make_direction_button("▲", &"forward", Vector2(110, 554))
	_make_direction_button("▼", &"back", Vector2(110, 666))
	_make_action_button(
		"ATK", Vector2(1060, 612), func() -> void: _player_input().set_mobile_attack_held(true), func() -> void: _player_input().set_mobile_attack_held(false)
	)
	_make_action_button("Q", Vector2(988, 548), func() -> void: _player_input().request_mobile_ability(&"skill_01"))
	_make_action_button("E", Vector2(1104, 548), func() -> void: _player_input().request_mobile_ability(&"skill_02"))
	_make_action_button("R", Vector2(988, 660), func() -> void: _player_input().request_mobile_ability(&"skill_03"))
	_make_action_button("F", Vector2(1104, 660), func() -> void: _player_input().request_mobile_ability(&"ultimate"))


func _make_direction_button(label_text: String, direction_id: StringName, position_value: Vector2) -> void:
	_make_action_button(
		label_text,
		position_value,
		func() -> void:
			_movement_held[direction_id] = true
			_update_mobile_move(),
		func() -> void:
			_movement_held[direction_id] = false
			_update_mobile_move()
	)


func _make_action_button(label_text: String, position_value: Vector2, on_down: Callable, on_up: Callable = Callable()) -> void:
	var button := Button.new()
	button.text = label_text
	button.position = position_value
	button.size = Vector2(62, 52)
	button.add_theme_font_size_override("font_size", 18)
	button.modulate = Color(0.67, 0.91, 1.0, 0.86)
	button.button_down.connect(on_down)
	if on_up.is_valid():
		button.button_up.connect(on_up)
	_mobile_panel.add_child(button)


func _update_mobile_move() -> void:
	var move := Vector2(float(_movement_held[&"right"]) - float(_movement_held[&"left"]), float(_movement_held[&"back"]) - float(_movement_held[&"forward"]))
	_player_input().set_mobile_move(move)


func _player_input() -> PlayerInputSource:
	if hero == null:
		return null
	return hero.get_node_or_null("Control/CharacterController/PlayerInput") as PlayerInputSource
