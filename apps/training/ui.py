from shiny import ui
import pandas as pd
from typing import List
from libs.ui.components import create_card_with_header

class TrainingComponents:
    """Training data UI components with improved organization."""
    
    @staticmethod
    def create_search_filters() -> ui.div:
        """Create search and filter controls with improved layout."""
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
                    ui.output_data_frame("training_data"),
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

def create_training_panel() -> ui.nav_panel:
    """Create the complete training management panel with responsive layout."""
    return ui.nav_panel(
        "Training Data",
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