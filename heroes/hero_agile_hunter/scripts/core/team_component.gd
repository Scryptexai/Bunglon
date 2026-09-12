class_name TeamComponent
extends Node
## Tiny faction boundary so targeting remains reusable by player, AI, and network input.

@export var team_id: int = 1


func is_hostile_to(other_team_id: int) -> bool:
	return team_id != other_team_id
