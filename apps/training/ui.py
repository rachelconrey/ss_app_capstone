from shiny import ui
import pandas as pd
from libs.ui.components import create_card_with_header

class TrainingComponents:
    """Training data UI components."""
    
    @staticmethod
    def create_training_filters() -> ui.sidebar:
        """Create training data filters."""
        return ui.sidebar(
            # ui.h3("Filter Options"),
            # ui.div(
            #     ui.input_date_range(
            #         "date_range",
            #         "Date Range",
            #         start=pd.Timestamp.now().strftime("%Y-%m-01"),
            #         end=pd.Timestamp.now().strftime("%Y-%m-%d")
            #     ),
            #     class_="mb-3"
            #),
            # Dynamic training type choices from server
            # ui.div(
            #     ui.output_ui("training_type_choices"),
            #     class_="mb-3"
            # ),
            # ui.div(
            #     ui.input_text(
            #         "training_search",
            #         "Search",
            #         placeholder="Search by name or course..."
            #     ),
            #     class_="mt-3"
            # )
        )

    @staticmethod
    def create_training_content() -> ui.div:
        """Create the main training content area."""
        return ui.div(
            ui.row(
                ui.column(
                    12,
                    create_card_with_header(
                        "Training Records",
                        [
                            ui.div(
                                ui.output_data_frame("training_table"),
                                class_="mb-2"
                            ),
                            ui.div(
                                ui.output_text("training_count"),
                                class_="text-muted"
                            )
                        ]
                    )
                )
            )
        )

def create_training_panel() -> ui.nav_panel:
    """Create the training management panel."""
    return ui.nav_panel(
        "Training Data",
        ui.layout_sidebar(
            TrainingComponents.create_training_filters(),
            TrainingComponents.create_training_content()
        )
    )