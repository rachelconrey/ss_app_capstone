from shiny import ui
from datetime import datetime

class TrainingComponents:
    """Training data UI components with improved organization."""
    
    @staticmethod
    def create_search_filters() -> ui.div:
        """Create search and filter components."""
        return ui.div(
            ui.row(
                ui.column(
                    3,
                    ui.div(
                        ui.input_select(
                            "search_course",
                            "Search by course",
                            choices={"All": "All"}
                        ),
                        class_="mb-2"
                    )
                ),
                ui.column(
                    9,
                    ui.div(
                        ui.input_select(
                            "status_filter_training",
                            "Filter by Status",
                            choices={
                                "All": "All",
                                "Current": "Current",
                                "Overdue": "Overdue"
                            }
                        ),
                        class_="mb-2"
                    )
                )
            ),
            class_="mt-2"
        )

    @staticmethod
    def create_training_table() -> ui.div:
        """Create the training records table."""
        return ui.div(
            ui.card(
                ui.card_header("Training Records"),
                ui.card_body(
                    ui.output_data_frame("training_table"),
                    class_="table-responsive"
                )
            ),
            class_="mb-3"
        )

    @staticmethod
    def create_add_training_form() -> ui.div:
        """Create form for adding new training records."""
        return ui.div(
            ui.card(
                ui.card_body(
                    ui.input_select(
                        "new_training_course",
                        "Select Course",
                        choices={"": "Select a course"}
                    ),
                    ui.input_select(
                        "new_training_user",
                        "Select User",
                        choices={"": "Select a course first"}
                    ),
                    ui.input_date(
                        "new_training_date",
                        "Completion Date",
                        value=datetime.now().date()
                    ),
                    ui.div(
                        ui.input_action_button(
                            "add_training_btn",
                            "Add Training Record",
                            class_="btn-primary"
                        ),
                        class_="mt-3"
                    )
                )
            ),
            class_="mb-3"
        )

    @staticmethod
    def create_edit_training_form() -> ui.div:
        """Create form for editing training records."""
        return ui.div(
            ui.card(
                ui.card_body(
                    ui.input_date(
                        "edit_training_date",
                        "New Completion Date",
                        value=datetime.now().date()
                    ),
                    ui.div(
                        ui.input_action_button(
                            "update_training_btn",
                            "Update Record",
                            class_="btn-warning"
                        ),
                        class_="mt-3"
                    )
                )
            ),
            class_="mb-3"
        )

    @staticmethod
    def create_delete_training_form() -> ui.div:
        """Create form for deleting training records."""
        return ui.div(
            ui.card(
                ui.card_body(
                    ui.p(
                        "Are you sure you want to delete this training record? This action cannot be undone.",
                        class_="text-danger"
                    ),
                    ui.div(
                        ui.input_action_button(
                            "delete_training_btn",
                            "Delete Record",
                            class_="btn-danger"
                        ),
                        class_="mt-3"
                    )
                )
            ),
            class_="mb-3"
        )

def create_crud_content() -> ui.div:
    """Create the complete CRUD operations interface."""
    return ui.div(
        ui.h3("Training Management", class_="h5 mb-3"),
        ui.navset_tab(
            ui.nav_panel(
                "Add Training",
                TrainingComponents.create_add_training_form()
            ),
            ui.nav_panel(
                "Edit Training",
                TrainingComponents.create_edit_training_form()
            ),
            ui.nav_panel(
                "Delete Training",
                TrainingComponents.create_delete_training_form()
            ),
            id="training_crud_tabs"
        )
    )

def create_training_panel() -> ui.nav_panel:
    """Create the complete training management panel."""
    return ui.nav_panel(
        "Training Management",
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
                        TrainingComponents.create_search_filters(),
                        TrainingComponents.create_training_table(),
                        class_="mt-3"
                    )
                )
            )
        )
    )