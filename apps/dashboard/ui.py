from shiny import ui
import pandas as pd
from libs.ui.components import create_card_with_header

class DashboardComponents:
    """Dashboard UI component management."""
    
    @staticmethod
    def create_value_boxes() -> ui.layout_columns:
        """Create metric value boxes."""
        return ui.layout_columns(
            ui.value_box(
                "Total Members",
                ui.output_text("total_members"),
                showcase=ui.HTML('<i class="fas fa-users"></i>'),
                #theme="primary"
            ),
            ui.value_box(
                "Eligible Members",
                ui.output_text("eligible_members"),
                showcase=ui.HTML('<i class="fas fa-check-circle"></i>'),
                #theme="success"
            ),
            ui.value_box(
                "Ineligible Members",
                ui.output_text("ineligible_members"),
                showcase=ui.HTML('<i class="fas fa-times-circle"></i>'),
                #theme="warning"
            ),
            col_widths={
                "sm": 4
            }
        )

    @staticmethod
    def create_training_section() -> ui.div:
        """Create training overview section."""
        return ui.div(
            create_card_with_header(
                "Course Completion Overview",
                [
                    ui.output_plot("plot"),
                    ui.div(
                        ui.output_text("training_summary"),
                        class_="mt-3 text-muted"
                    )
                ]
            ),
            class_="mt-4"
        )

def create_dashboard_panel() -> ui.nav_panel:
    """Create the main dashboard panel."""
    return ui.nav_panel(
        "Dashboard",
        ui.div(
            ui.div(
                DashboardComponents.create_value_boxes(),
                class_="dashboard-metrics mb-4"
            ),
            DashboardComponents.create_training_section(),
            class_="p-3"
        )
    )