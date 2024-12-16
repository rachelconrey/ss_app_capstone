from pathlib import Path
from shiny import App, render, ui

def create_login_page():
    """Create the login page UI."""
    return ui.div(
        # Hidden authentication state input using HTML
        ui.tags.input(
            id="authenticated",
            type="hidden",
            value="false"
        ),
        
        ui.div(
            ui.card(
                ui.card_header(
                    ui.div(
                        # Logo image at the top of the card
                        ui.img(src="sslogo.jpg", height="90px", style="margin:5px;"),
                        ui.h3("Data Management System", class_="h5 mb-0 mt-3"),
                        style="text-align: center;"
                    )
                ),
                ui.card_body(
                    ui.input_text(
                        "username",
                        "Username",
                        placeholder="Enter your username",
                        autocomplete="off"
                    ),
                    ui.input_password(
                        "password",
                        "Password",
                        placeholder="Enter your password"
                    ),
                    ui.div(
                        ui.input_action_button(
                            "login_button",
                            "Login",
                            class_="btn-primary w-100"
                        ),
                        class_="mt-3"
                    ),
                    ui.div(
                        ui.output_text("login_message", inline=True),
                        class_="mt-2 text-danger"
                    ),
                style="align-items: center;"   
                )
            ),
            class_="col-md-4 mx-auto mt-5"
        ),
        class_="container-fluid vh-100 d-flex align-items-center justify-content-center",
        style="background-color: black"
    )