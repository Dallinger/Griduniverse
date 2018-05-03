from ipywidgets import widgets
from jinja2 import Template
from traitlets import (
    observe,
    Unicode,
)

header_template = Template(u"""
<h2>{{ name }}</h2>
<div>Status: {{ status }}</div>
{% if app_id %}<div>App ID: {{ app_id }}</div>{% endif %}
""")

grid_template = Template(u"""
<table>
{% for row in rows %}
<tr>
{% for col in row %}
    <td>{{ col|safe }}</td>
{% endfor %}
</tr>
{% endfor %}
</table>
""")

scores_template = Template(u"""
<table style="width: 30%">
<tr>
<th>Name</th> <th>Score</th>
</tr>
{% for player in players %}
<tr>
  <td><div style='width: 5px; height: 5px; background-color: {{ player.color_name }};
                  float: left; margin: 10px 5px 0 0'></div> {{ player.name }}</td>
  <td>{{ player.score }}</td>
</tr>
{% endfor %}
</table>
""")

chat_template = Template(u"""
<table style="width: 30%">
<tr>
<th>Name</th> <th>Message</th>
</tr>
{% for sender,timestamp,message in chat_messages %}
<tr>
  <td><div style='width: 5px; height: 5px; background-color: {{ sender.color_name }};
                  float: left; margin: 10px 5px 0 0'></div> {{ sender.name }}</td>
  <td>{{ message }}</td>
</tr>
{% endfor %}
</table>
""")


NOTHING = "<div style='width: 5px; height: 5px; background-color: lightgray'></div>"
FOOD = "<div style='width: 5px; height: 5px; background-color: lime'></div>"
WALL = "<div style='width: 5px; height: 5px; background-color: darkgray'></div>"
PLAYER = "<div style='width: 5px; height: 5px; background-color: %s'></div>"


class ExperimentWidget(widgets.VBox):

    status = Unicode('Unknown')

    def __init__(self, exp):
        self.exp = exp
        super(ExperimentWidget, self).__init__()
        self.render()

    @observe('grid')
    def render(self, change=None):
        header = widgets.HTML(
            header_template.render(
                name=self.exp.task,
                status=self.status,
                app_id=self.exp.app_id,
            ),
        )

        tab_list = []
        if hasattr(self.exp, 'grid'):
            grid = []
            player_positions = {tuple(p.position): p.color for p in self.exp.grid.players.values()}
            for row_idx in range(self.exp.grid.rows):
                row = []
                for col_idx in range(self.exp.grid.columns):
                    position = NOTHING
                    if (row_idx, col_idx) in self.exp.grid.wall_locations:
                        position = WALL
                    if (row_idx, col_idx) in self.exp.grid.food_locations:
                        position = FOOD
                    if (row_idx, col_idx) in player_positions.keys():
                        position = PLAYER % player_positions[(row_idx, col_idx)]
                    row.append(position)
                grid.append(row)

            grid_tab = widgets.HTML(
                grid_template.render(
                    rows=grid,
                ),
            )
            tab_list += [grid_tab]

            scores_tab = widgets.HTML(
                scores_template.render(
                    players=sorted(self.exp.grid.players.values(), key=lambda player: player.id),
                )
            )
            tab_list += [scores_tab]

            chat_tab = widgets.HTML(
                chat_template.render(
                    chat_messages=self.exp.grid.chat_message_history,
                )
            )
            tab_list += [chat_tab]

        tabs = widgets.Tab(children=tab_list)
        tabs.set_title(0, 'Grid')
        tabs.set_title(1, 'Scores')
        tabs.set_title(2, 'Chat')
        try:
            tabs.selected_index = self.children[1].selected_index
        except IndexError:
            pass
        self.children = [header, tabs]
