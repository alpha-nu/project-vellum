from unittest.mock import MagicMock, patch
import main as vellum_main
from tests.controller.conftest import MockUIBuilder


def test_main_uses_provided_ui_and_runs():
    # Replace ConverterController with a MagicMock so main() doesn't execute workflow
    mock_controller_cls = MagicMock()
    mock_controller = MagicMock()
    mock_controller_cls.return_value = mock_controller
    ui = MockUIBuilder().build()

    with patch.object(vellum_main, 'ConverterController', mock_controller_cls):
        vellum_main.main(ui=ui)

    mock_controller_cls.assert_called_once()
    mock_controller.run.assert_called_once()
