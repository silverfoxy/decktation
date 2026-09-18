from pathlib import Path


FRONTEND = Path(__file__).parents[1] / "src" / "index.tsx"


def test_button_preview_uses_backend_status_without_steam_input_mapping():
    source = FRONTEND.read_text()
    assert 'setButtonState(result.detected_button || "None")' in source
    assert 'RegisterForControllerInputMessages' not in source
    assert 'CONTROLLER_BUTTON_NAMES' not in source


def test_settings_rpc_functions_are_not_shadowed_by_react_state_setters():
    source = FRONTEND.read_text()

    expected_calls = {
        "set_enabled": "setEnabledRpc",
        "set_confirm_mode": "setConfirmModeRpc",
        "set_manual_send": "setManualSendRpc",
        "set_remember_last_channel": "setRememberLastChannelRpc",
        "set_active_preset": "setActivePresetRpc",
        "set_share_diagnostics": "setShareDiagnosticsRpc",
        "set_transcription_options": "setTranscriptionOptionsRpc",
    }

    for backend_method, rpc_name in expected_calls.items():
        assert (
            f'const {rpc_name} = callable' in source
            and f'>("{backend_method}")' in source
        )
        assert f"await {rpc_name}(" in source
