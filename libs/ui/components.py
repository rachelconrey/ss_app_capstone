from shiny import ui
from typing import List

def create_card_with_header(title: str, content: List[ui.tags.div]) -> ui.card:
    """Create a card with header and content."""
    return ui.card(
        ui.card_header(title),
        *content
    )

def create_action_button(id: str, label: str, button_class: str = "btn-primary") -> ui.tags.div:
    """Create a styled action button."""
    return ui.input_action_button(
        id,
        label,
        class_=f"{button_class} mt-2"
    )