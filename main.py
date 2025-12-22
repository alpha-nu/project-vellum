"""
Vellum - Document extraction engine for PDFs and ePubs.

Entry point for the application. Delegates all business logic to the controller.
"""
from view.ui import RetroCLI
from controller.converter_controller import ConverterController


def main(ui=None):
    """
    Application entry point.
    
    Args:
        ui: Optional UI interface for dependency injection (primarily for testing)
    """
    ui = ui or RetroCLI()
    controller = ConverterController(ui)
    controller.run()


if __name__ == "__main__":
    main()