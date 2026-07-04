"""Modal screens for Disco Terminal."""

from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static


class PickerScreen(ModalScreen):
    """Modal list picker. Dismisses with the chosen value, or None on escape."""

    CSS = """
    PickerScreen {
        align: center middle;
    }
    #picker {
        width: 70%;
        max-width: 90;
        max-height: 80%;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    #picker-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Close")]

    def __init__(self, title, options, markup=False):
        """options: [(label, value)]. markup=True renders Rich markup in labels."""
        super().__init__()
        self.picker_title = title
        self.options = list(options)
        self.markup = markup

    def compose(self):
        with Vertical(id="picker"):
            yield Static(self.picker_title, id="picker-title")
            yield ListView(
                *[
                    ListItem(Label(label, markup=self.markup), id=f"opt-{i}")
                    for i, (label, _value) in enumerate(self.options)
                ]
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index_str = (event.item.id or "").removeprefix("opt-")
        if index_str.isdigit() and int(index_str) < len(self.options):
            self.dismiss(self.options[int(index_str)][1])

    def action_cancel(self) -> None:
        self.dismiss(None)
