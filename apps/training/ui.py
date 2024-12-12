from shiny import ui
import pandas as pd
from typing import List
from libs.ui.components import create_card_with_header

class TrainingComponents:
    """Training data UI components with improved organization."""
    
    @staticmethod
    def create_search_filters() -> ui.div:
        return ui.div(
        ui.row(
            ui.column(
                6,
                ui.div(
                    ui.input_text(
                        "search_course",
                        "Search by course",
                        placeholder="Enter search term...",
                        autocomplete="off"
                    ),
                    class_="mb-2"
                )
            ),
            ui.column(
                6,
                ui.div(
                    ui.input_select(
                        "status_filter_training",
                        "Filter by Status",
                        choices={
                            "All": "All Courses",
                            "Complete": "Complete",
                            "Incomplete": "Incomplete"
                        }
                    ),
                    class_="mb-2"
                )
            )
        ),
        class_="mt-2"
    )


    @staticmethod
    def create_training_table() -> ui.card:
        """Create training directory section with improved structure."""
        return ui.card(
            ui.card_header(
                ui.h2("Training Data", class_="h5 mb-0"),
                TrainingComponents.create_search_filters()
            ),
            ui.div(
                ui.div(
                    ui.output_data_frame("training_table"),
                    class_="table-responsive"
                ),
                ui.div(
                    ui.output_text("record_count_training"),
                    class_="mt-2 text-muted small"
                ),
                class_="p-3"
            ),
            full_screen=True,
            class_="shadow-sm"
        )

def create_training_crud_sidebar():
    """Create sidebar with CRUD operations for training data."""
    return ui.sidebar(
        ui.div(
            ui.h3("Training Management", class_="h5 mb-3"),
            
            # Add New Training Record
            ui.accordion(
                ui.accordion_panel(
                    "Add New Training",
                    ui.input_select(
                        "new_training_user",
                        "Select User",
                        choices={"": "Select a course first"}
                    ),
                    ui.input_select(
                        "new_training_course",
                        "Select Course",
                        choices={"": "Loading courses..."}
                    ),
                    ui.input_date(
                        "new_training_date",
                        "Completion Date"
                    ),
                    ui.input_action_button(
                        "add_training_btn",
                        "Add Training Record",
                        class_="btn-primary mt-2"
                    )
                )
            ),
            
            # Edit Training Record
            ui.accordion(
                ui.accordion_panel(
                    "Edit Training",
                    ui.output_ui("edit_training_inputs"),
                    ui.input_action_button(
                        "update_training_btn",
                        "Update Record",
                        class_="btn-warning mt-2"
                    )
                )
            ),
            
            # Delete Training Record
            ui.accordion(
                ui.accordion_panel(
                    "Delete Training",
                    ui.output_text("selected_record_info"),
                    ui.input_action_button(
                        "delete_training_btn",
                        "Delete Record",
                        class_="btn-danger mt-2"
                    )
                )
            ),
            class_="mb-3"
        )
    )
def create_training_panel():
    """Create training panel with CRUD sidebar."""
    return ui.nav_panel(
        "Training Data",
        ui.layout_sidebar(
            create_training_crud_sidebar(),
            ui.row(
                ui.column(
                    12,
                    ui.div(
                        TrainingComponents.create_training_table(),
                        class_="mb-4"
                    )
                )
            )
        )
    )