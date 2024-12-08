from shiny import ui
from typing import List
from libs.ui.components import create_card_with_header, create_action_button

class MemberDataComponents:
    """Member data management UI components."""
    
    @staticmethod
    def create_member_form() -> List[ui.tags.div]:
        """Create the member input form with validation."""
        return [
            ui.div(
                ui.h4("Personal Information", class_="mb-3"),
                ui.div(
                    ui.input_text(
                        "first_name",
                        "First Name *"
                    ),
                    ui.input_text(
                        "last_name",
                        "Last Name *"
                    ),
                    class_="name-group"
                ),
                ui.input_text(
                    "email",
                    "Email *"
                ),
                ui.input_text(
                    "phone_number",
                    "Phone (0000000000)"
                ),
                class_="personal-info-section"
            ),
            ui.div(
                ui.h4("Emergency Contact", class_="mb-3"),
                ui.div(
                    ui.input_text(
                        "ice_first_name",
                        "ICE First Name"
                    ),
                    ui.input_text(
                        "ice_last_name",
                        "ICE Last Name"
                    ),
                    class_="name-group"
                ),
                ui.input_text(
                    "ice_phone_number",
                    "ICE Phone (0000000000)"
                ),
                class_="emergency-info-section mt-4"
            ),
            ui.div(
                create_action_button(
                    "add_member",
                    "Add Member",
                    "btn-primary"
                ),
                class_="form-actions mt-4"
            )
        ]

    @staticmethod
    def create_member_directory() -> ui.card:
        """Create the member directory section with search and table."""
        return ui.card(
            ui.card_header(
                "Member Directory",
                ui.div(
                    ui.row(
                        ui.column(
                            6,
                            ui.div(
                                ui.input_text(
                                    "search",
                                    "Search by name or email",
                                    placeholder="Enter search term..."
                                ),
                                class_="mb-2"
                            )
                        ),
                        ui.column(
                            6,
                            ui.div(
                                ui.input_select(
                                    "status_filter",
                                    "Filter by Status",
                                    choices=["All", "Eligible", "Ineligible"]
                                ),
                                class_="mb-2"
                            )
                        )
                    ),
                    class_="mt-2"
                )
            ),
            ui.div(
                ui.output_data_frame("member_data"),
                ui.div(
                    ui.output_text("record_count"),
                    class_="mt-2 text-muted"
                ),
                class_="p-3"
            ),
            full_screen=True
        )

def create_member_panel() -> ui.nav_panel:
    """Create the complete member management panel."""
    return ui.nav_panel(
        "Member Management",
        ui.row(
            ui.column(
                4,
                create_card_with_header(
                    "Add New Member",
                    MemberDataComponents.create_member_form()
                )
            ),
            ui.column(
                8,
                MemberDataComponents.create_member_directory()
            )
        )
    )