from pathlib import Path


def test_main_status_uses_specific_controller_state_instead_of_generic_error():
    source = (Path(__file__).parents[1] / 'src/index.tsx').read_text()
    assert ': !controllerReady ? t(controllerStatus === "Waiting for input" ? "Waiting for input" : "Controller unavailable")' in source
