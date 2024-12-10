# ui.py
from shiny import ui
from typing import List
from libs.ui.components import create_card_with_header

class MemberDataComponents:
    """Member directory display UI components with improved organization and accessibility."""
    
    @staticmethod
    def create_search_filters() -> ui.div:
        return ui.div(
            ui.row(
                ui.column(
                    6,
                    ui.div(
                        ui.input_text(
                            "search_member",
                            "Search by Name or Email",
                            placeholder="",
                            autocomplete="off"
                        ),
                        class_="mb-2"
                    )
                ),
                ui.column(
                    6,
                    ui.div(
                        ui.input_select(
                            "status_filter_member",
                            "Filter by Status",
                            choices={
                                "All": "All Members",
                                "Eligible": "Eligible",
                                "Ineligible": "Ineligible"
                            }
                        ),
                        class_="mb-2"
                    )
                )
            ),
            class_="mt-2"
        )

    @staticmethod
    def create_member_directory() -> ui.card:
        """Create the member directory section with improved structure."""
        return ui.card(
            ui.card_header(
                ui.h2("Member Directory", class_="h5 mb-0"),
                MemberDataComponents.create_search_filters()
            ),
            ui.div(
                ui.div(
                    ui.output_data_frame("member_data"),
                    class_="table-responsive"
                ),
                ui.div(
                    ui.output_text("record_count_member"),
                    class_="mt-2 text-muted small"
                ),
                class_="p-3"
            ),
            full_screen=True,
            class_="shadow-sm"
        )

def create_member_panel() -> ui.nav_panel:
    """Create the complete member management panel with responsive layout."""
    return ui.nav_panel(
        "Member Management",
        ui.row(
            ui.column(
                12,  # Made full width for better responsive behavior
                ui.div(
                    MemberDataComponents.create_member_directory(),
                    class_="mb-4"
                )
            )
        )
    )