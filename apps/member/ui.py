from shiny import ui

class PersonalComponents:
    
    @staticmethod
    def create_search_filters() -> ui.div:
        """Create search and filter components."""
        return ui.div(
            ui.row(
                ui.column(
                    3,
                    ui.div(
                        ui.input_text(
                            "search_member",
                            "Search by name",
                            placeholder="Enter name",
                            autocomplete="off"
                        ),
                        class_="mb-2"
                    )
                ),
                ui.column(
                    9,
                    ui.div(
                        ui.input_select(
                            "status_filter_member",
                            "Filter by Status",
                            choices={
                                "All": "All",
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
    def create_member_table() -> ui.div:
        """Create the member records table."""
        return ui.div(
            ui.card(
                ui.card_header("Member Records"),
                ui.card_body(
                    ui.output_data_frame("member_table"),
                    class_="table-responsive"
                )
            ),
            class_="mb-3"
        )

    @staticmethod
    def create_add_member_form() -> ui.div:
        """Create form for adding new members."""
        return ui.div(
            ui.input_text("new_first_name", "First Name"),
            ui.input_text("new_last_name", "Last Name"),
            ui.input_text("new_email", "Email"),
            ui.input_text("new_phone", "Phone Number"),
            ui.input_text("new_ice_first_name", "Emergency Contact First Name"),
            ui.input_text("new_ice_last_name", "Emergency Contact Last Name"),
            ui.input_text("new_ice_phone", "Emergency Contact Phone"),
            ui.input_action_button(
                "add_member_btn",
                "Add Member",
                class_="btn-primary mt-2"
            )
        )

    @staticmethod
    def create_edit_member_form() -> ui.div:
        """Create form for editing members."""
        return ui.div(
            ui.output_text("selected_member_text"),
            ui.panel_well(
                ui.div(
                    ui.input_text("edit_first_name", "First Name"),
                    ui.input_text("edit_last_name", "Last Name"),
                    ui.input_text("edit_email", "Email"),
                    ui.input_text("edit_phone", "Phone Number"),
                    ui.input_text("edit_ice_first_name", "Emergency Contact First Name"),
                    ui.input_text("edit_ice_last_name", "Emergency Contact Last Name"),
                    ui.input_text("edit_ice_phone", "Emergency Contact Phone"),
                    ui.input_action_button(
                        "update_member_btn",
                        "Update Member",
                        class_="btn-warning mt-2"
                    ),
                    class_="mb-2"
                ),
                ui.busy_indicators.options(
                    spinner_type=None
                )
            )
        )

    @staticmethod
    def create_delete_member_form() -> ui.div:
        """Create form for deleting members."""
        return ui.div(
            ui.output_text("delete_member_text"),
            ui.panel_well(
                ui.div(
                    ui.p("Are you sure you want to delete this member? This action cannot be undone."),
                    ui.input_action_button(
                        "delete_member_btn",
                        "Delete Member",
                        class_="btn-danger mt-2"
                    ),
                    class_="mb-2"
                )
            )
        )

def create_crud_content() -> ui.div:
    """Create the complete CRUD operations interface."""
    return ui.div(
        ui.h3("Member Management", class_="h5 mb-3"),
        
        # Create tabs for different operations
        ui.navset_card_tab(
            ui.nav_panel(
                "Add Member",
                ui.accordion(
                    ui.accordion_panel(
                        "Add New Member",
                        PersonalComponents.create_add_member_form()
                    ),
                    id="add_member_accordion"
                )
            ),
            
            ui.nav_panel(
                "Edit Member",
                ui.accordion(
                    ui.accordion_panel(
                        "Member",
                        PersonalComponents.create_edit_member_form()
                    ),
                    id="edit_member_accordion"
                )
            ),
            
            ui.nav_panel(
                "Delete Member",
                ui.accordion(
                    ui.accordion_panel(
                        "Delete Member",
                        PersonalComponents.create_delete_member_form()
                    ),
                    id="delete_member_accordion"
                )
            ),
            id="member_crud_tabs"
        ),
        class_="mb-3"
    )

def create_member_panel() -> ui.nav_panel:
    """Create the complete member management panel."""
    return ui.nav_panel(
        "Member Management",
        ui.page_fluid(
            ui.row(
                # CRUD operations sidebar
                ui.column(
                    4,
                    create_crud_content()
                ),
                # Main content area
                ui.column(
                    8,
                    ui.div(
                        PersonalComponents.create_search_filters(),
                        PersonalComponents.create_member_table(),# Add height to main content area
                    )
                )
            )
        )
    )