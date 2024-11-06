import re
from collections import defaultdict

from dlgr.griduniverse.experiment import Gridworld

player_regex = re.compile(r"(p\d+)(c\d+)?")
color_names = Gridworld.player_color_names


def matrix2gridworld(matrix):
    """Transform a 2D matrix representing an initial grid state
    into the serialized format used by Gridworld.

    Example:

    +---------------+---------+--------------------+
    | w             | stone   | gooseberry_bush|3  |
    | p1c1          | w       | w                  |
    |               |         | p3c2               |
    |               | p4c2    |                    |
    | big_hard_rock | w       | p2c1               |
    +---------------+---------+--------------------+

    Explanation:

    - "w": a wall
    - "stone": item defined by item_id "stone" in game_config.yml
    - "gooseberry_bush|3": similar to the above, with the added detail
        that the item has 3 remaining uses
    - "p2c1": player ID 2, who is on team (color) 1
    - Empty cells: empty space in the grid
    """
    result = defaultdict(list)

    result["rows"] = len(matrix)
    if matrix:
        result["columns"] = len(matrix[0])
    else:
        result["columns"] = 0

    for row_num, row in enumerate(matrix):
        for col_num, cell in enumerate(row):
            # NB: we use [y, x] format in GU!! (╯°□°)╯︵ ┻━┻
            position = [row_num, col_num]
            cell = cell.strip()
            player_match = player_regex.match(cell)
            if not cell:
                # emtpy
                continue
            if cell == "w":
                result["walls"].append(position)
            elif player_match:
                id_str, color_str = player_match.groups()
                player_id = id_str.replace("p", "")
                player_data = {
                    "id": player_id,
                    "position": position,
                }
                if color_str is not None:
                    player_color_index = int(color_str.replace("c", "")) - 1
                    try:
                        player_data["color"] = color_names[player_color_index]
                    except IndexError:
                        max_color = len(color_names)
                        raise ValueError(
                            f'Invalid player color specified in "{cell}" at postion {position}. '
                            f"Max color value is {max_color}, "
                            f"but you specified {player_color_index + 1}."
                        )

                result["players"].append(player_data)
            else:
                # assume an Item
                id_and_maybe_uses = [s.strip() for s in cell.split("|")]
                item_data = {
                    "id": len(result["items"]) + 1,
                    "item_id": id_and_maybe_uses[0],
                    "position": position,
                }
                if len(id_and_maybe_uses) == 2:
                    item_data["remaining_uses"] = int(id_and_maybe_uses[1])
                result["items"].append(item_data)

    return dict(result)
