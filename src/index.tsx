import {
	definePlugin,
	PanelSection,
	PanelSectionRow,
	ServerAPI,
	quickAccessMenuClasses,
	Router,
	ToggleField,
	ButtonItem,
	DropdownItem,
	DropdownOption,
} from "decky-frontend-lib";

import React, {
	VFC,
	useEffect,
	useState,
} from "react";

import { FaMicrophone } from "react-icons/fa";

// L5 = bit 15, R5 = bit 16 in ulButtons (same as antiquitte/decky-dictation)
const L5_MASK = 1 << 15;
const R5_MASK = 1 << 16;

class DectationLogic {
	serverAPI: ServerAPI;
	enabled: boolean = false;
	recording: boolean = false;
	lastButtonState: string = "None";
	inputRegistered: boolean = false;
	inputError: string = "";
	onButtonChange: (() => void) | null = null;
	l5Held: boolean = false;

	constructor(serverAPI: ServerAPI) {
		this.serverAPI = serverAPI;
	}

	notify = async (message: string, duration: number = 2000, body: string = "") => {
		if (!body) {
			body = message;
		}
		this.serverAPI.toaster.toast({
			title: message,
			body: body,
			duration: duration,
			critical: false
		});
	}

	// Handler for RegisterForControllerStateChanges (antiquitte style)
	handleControllerState = (val: any[]) => {
		if (!val || val.length === 0) return;

		const inputs = val[0];
		if (!inputs) return;

		const ulButtons = inputs.ulButtons || 0;
		const l5Pressed = (ulButtons & L5_MASK) !== 0;

		// Debug: show button state
		this.lastButtonState = l5Pressed ? "L5" : "None";
		if (this.onButtonChange) this.onButtonChange();

		if (!this.enabled) {
			return;
		}

		// Push-to-talk: L5 held = recording
		if (l5Pressed && !this.l5Held) {
			this.l5Held = true;
			this.recording = true;
			// Disable system buttons temporarily
			(Router as any).DisableHomeAndQuickAccessButtons();
			setTimeout(() => {
				(Router as any).EnableHomeAndQuickAccessButtons();
			}, 1000);
			this.serverAPI.callPluginMethod('start_recording', {});
			this.notify("Decktation", 1500, "Recording...");
		} else if (!l5Pressed && this.l5Held) {
			this.l5Held = false;
			this.recording = false;
			this.serverAPI.callPluginMethod('stop_recording', {});
			this.notify("Decktation", 1500, "Transcribing...");
		}
	}

	// Fallback handler for RegisterForControllerInputMessages
	handleButtonInput = (controllerIndex: number, gamepadButton: number, isButtonPressed: boolean) => {
		// L5 = 44 in this API
		const buttonName = gamepadButton === 44 ? "L5" : `btn${gamepadButton}`;
		this.lastButtonState = isButtonPressed ? buttonName : "None";
		if (this.onButtonChange) this.onButtonChange();

		if (!this.enabled) {
			return;
		}

		if (gamepadButton === 44) { // L5
			if (isButtonPressed && !this.recording) {
				this.recording = true;
				(Router as any).DisableHomeAndQuickAccessButtons();
				setTimeout(() => {
					(Router as any).EnableHomeAndQuickAccessButtons();
				}, 1000);
				this.serverAPI.callPluginMethod('start_recording', {});
				this.notify("Decktation", 1500, "Recording...");
			} else if (!isButtonPressed && this.recording) {
				this.recording = false;
				this.serverAPI.callPluginMethod('stop_recording', {});
				this.notify("Decktation", 1500, "Transcribing...");
			}
		}
	}

	testRecording = async () => {
		if (!this.recording) {
			this.recording = true;
			await this.serverAPI.callPluginMethod('start_recording', {});
			this.notify("Decktation", 1500, "Recording started (manual test)");
		} else {
			this.recording = false;
			await this.serverAPI.callPluginMethod('stop_recording', {});
			this.notify("Decktation", 1500, "Recording stopped (manual test)");
		}
	}
}

// Available button options
const BUTTON_OPTIONS: DropdownOption[] = [
	{ data: "L1", label: "L1 (Left Bumper)" },
	{ data: "R1", label: "R1 (Right Bumper)" },
	{ data: "L2", label: "L2 (Left Trigger)" },
	{ data: "R2", label: "R2 (Right Trigger)" },
	{ data: "L5", label: "L5 (Left Back Grip)" },
	{ data: "R5", label: "R5 (Right Back Grip)" },
	{ data: "A", label: "A Button" },
	{ data: "B", label: "B Button" },
	{ data: "X", label: "X Button" },
	{ data: "Y", label: "Y Button" },
];

const DectationPanel: VFC<{ logic: DectationLogic }> = ({ logic }) => {
	const [enabled, setEnabled] = useState<boolean>(false);
	const [recording, setRecording] = useState<boolean>(false);
	const [serviceReady, setServiceReady] = useState<boolean>(false);
	const [modelReady, setModelReady] = useState<boolean>(false);
	const [modelLoading, setModelLoading] = useState<boolean>(false);
	const [buttonState, setButtonState] = useState<string>("None");
	const [buttons, setButtons] = useState<string[]>(["L1", "R1"]);
	const [showNotifications, setShowNotifications] = useState<boolean>(true);
	const prevRecordingRef = React.useRef<boolean>(false);

	useEffect(() => {
		setEnabled(logic.enabled);
		setRecording(logic.recording);
		logic.onButtonChange = () => {
			setButtonState(logic.lastButtonState);
		};

		// Load button configuration and settings
		logic.serverAPI.callPluginMethod('get_button_config', {}).then((result) => {
			if (result.success && result.result) {
				const config = result.result.config;
				if (config) {
					if (config.buttons) {
						setButtons(config.buttons);
					}
					if (config.showNotifications !== undefined) {
						setShowNotifications(config.showNotifications);
					}
				}
			}
		});

		return () => {
			logic.onButtonChange = null;
		};
	}, []);

	useEffect(() => {
		const interval = setInterval(async () => {
			const result = await logic.serverAPI.callPluginMethod('get_status', {});
			if (result.success && result.result) {
				setServiceReady(result.result.service_ready);
				setModelReady(result.result.model_ready);
				setModelLoading(result.result.model_loading);
				if (logic.enabled) {
					const isRecording = result.result.recording;

					// Show notification only when recording starts
					if (showNotifications && isRecording && !prevRecordingRef.current) {
						console.log("[Decktation] Showing notification - recording started");
						logic.notify("Recording", 1500, "🎤 Recording...");
					}

					prevRecordingRef.current = isRecording;
					setRecording(isRecording);
				}
			}
		}, 1000);
		return () => clearInterval(interval);
	}, [logic.enabled, showNotifications]);

	return (
		<div>
			<PanelSection>
				{!serviceReady && (
					<PanelSectionRow>
						<div style={{
							padding: '10px',
							backgroundColor: '#2196f3',
							borderRadius: '8px',
							textAlign: 'center',
							fontWeight: 'bold'
						}}>
							Initializing service...
						</div>
					</PanelSectionRow>
				)}
				{serviceReady && modelLoading && (
					<PanelSectionRow>
						<div style={{
							padding: '10px',
							backgroundColor: '#2196f3',
							borderRadius: '8px',
							textAlign: 'center',
							fontWeight: 'bold'
						}}>
							Loading Whisper model...
						</div>
					</PanelSectionRow>
				)}
				<PanelSectionRow>
					<ToggleField
						label="Enable Dictation"
						checked={enabled}
						disabled={!serviceReady || modelLoading}
						onChange={async (e) => {
							setEnabled(e);
							logic.enabled = e;
							await logic.serverAPI.callPluginMethod('set_enabled', { enabled: e });
							if (e && !modelReady) {
								setModelLoading(true);
								await logic.serverAPI.callPluginMethod('load_model', {});
							}
							if (!e && logic.recording) {
								logic.serverAPI.callPluginMethod('stop_recording', {});
								logic.recording = false;
								setRecording(false);
							}
						}}
					/>
				</PanelSectionRow>

				<PanelSectionRow>
					<ToggleField
						label="Show Notifications"
						description="Show toast when recording starts/stops"
						checked={showNotifications}
						onChange={async (e) => {
							setShowNotifications(e);
							// Save setting
							await logic.serverAPI.callPluginMethod('set_button_config', {
								buttons: buttons,
								showNotifications: e
							});
						}}
					/>
				</PanelSectionRow>

				<PanelSectionRow>
					<div style={{
						padding: '8px',
						backgroundColor: '#1a1a1a',
						borderRadius: '4px',
						fontSize: '13px',
						textAlign: 'center',
						border: '1px solid #444'
					}}>
						Hold <strong>{buttons.join('+')}</strong> to record
					</div>
				</PanelSectionRow>

				{buttons.map((button, index) => (
					<div key={index}>
						<PanelSectionRow>
							<DropdownItem
								label={`Button ${index + 1}`}
								menuLabel={`Select Button ${index + 1}`}
								rgOptions={BUTTON_OPTIONS}
								selectedOption={button}
								onChange={async (option) => {
									const newButtons = [...buttons];
									newButtons[index] = option.data as string;
									setButtons(newButtons);
									await logic.serverAPI.callPluginMethod('set_button_config', {
										buttons: newButtons,
										showNotifications: showNotifications
									});
								}}
							/>
						</PanelSectionRow>
						{buttons.length > 1 && (
							<PanelSectionRow>
								<div
									onClick={async () => {
										const newButtons = buttons.filter((_, i) => i !== index);
										setButtons(newButtons);
										await logic.serverAPI.callPluginMethod('set_button_config', {
											buttons: newButtons,
											showNotifications: showNotifications
										});
									}}
									style={{
										width: '100%',
										padding: '6px',
										display: 'flex',
										alignItems: 'center',
										justifyContent: 'center',
										backgroundColor: '#c53030',
										color: 'white',
										borderRadius: '4px',
										cursor: 'pointer',
										fontSize: '14px',
										fontWeight: 'bold',
										userSelect: 'none'
									}}
								>
									Remove Button {index + 1}
								</div>
							</PanelSectionRow>
						)}
					</div>
				))}

				{buttons.length < 5 && (
					<PanelSectionRow>
						<ButtonItem
							layout="below"
							onClick={async () => {
								// Find first button not in current list
								const availableButton = BUTTON_OPTIONS.find(
									opt => !buttons.includes(opt.data as string)
								);
								if (availableButton) {
									const newButtons = [...buttons, availableButton.data as string];
									setButtons(newButtons);
									await logic.serverAPI.callPluginMethod('set_button_config', {
										buttons: newButtons,
										showNotifications: showNotifications
									});
								}
							}}
						>
							+ Add Button
						</ButtonItem>
					</PanelSectionRow>
				)}

				<PanelSectionRow>
					<div style={{
						padding: '8px',
						backgroundColor: logic.inputRegistered ? '#1a3a1a' : '#3a1a1a',
						borderRadius: '4px',
						fontSize: '12px',
						textAlign: 'center',
						fontFamily: 'monospace'
					}}>
						Input: {logic.inputRegistered ? "OK" : "FAILED"}
						<br />
						Button: <strong>{buttonState}</strong>
					</div>
				</PanelSectionRow>

				{enabled && modelReady && (
					<PanelSectionRow>
						<div style={{
							padding: '10px',
							backgroundColor: recording ? '#4ade80' : '#374151',
							borderRadius: '8px',
							textAlign: 'center',
							fontWeight: 'bold'
						}}>
							{recording ? 'Recording...' : 'Ready'}
						</div>
					</PanelSectionRow>
				)}

				<PanelSectionRow>
					<ButtonItem
						layout="below"
						onClick={() => logic.testRecording()}
						disabled={!enabled || !modelReady || modelLoading}
					>
						{recording ? 'Stop Test Recording' : 'Start Test Recording'}
					</ButtonItem>
				</PanelSectionRow>
			</PanelSection>

			<PanelSection title="How to use:">
				<PanelSectionRow>
					<div style={{ fontSize: '13px', lineHeight: '1.6' }}>
						<strong>Push-to-Talk:</strong>
						<ul style={{ marginLeft: '15px', marginTop: '5px', marginBottom: '10px' }}>
							<li>Hold <strong>{buttons.join('+')}</strong> {buttons.length > 1 ? 'together' : ''} to record</li>
							<li>Release to transcribe and type into active window</li>
							<li>Configure button combo above (1-5 buttons)</li>
						</ul>

						<strong>Tips:</strong>
						<ul style={{ marginLeft: '15px', marginTop: '5px' }}>
							<li>Make sure your game/app is the active window</li>
							<li>Speak clearly for best results</li>
							<li>Works great for in-game chat</li>
						</ul>
					</div>
				</PanelSectionRow>
			</PanelSection>
		</div>
	);
};


export default definePlugin((serverApi: ServerAPI) => {
	let logic = new DectationLogic(serverApi);
	let input_register: { unregister: () => void } | null = null;

	// Use RegisterForControllerInputMessages (RegisterForControllerStateChanges doesn't exist)
	try {
		input_register = (window as any).SteamClient.Input.RegisterForControllerInputMessages(logic.handleButtonInput);
		logic.inputRegistered = true;
		console.log("[Decktation] RegisterForControllerInputMessages succeeded");
	} catch (e: any) {
		console.error("[Decktation] RegisterForControllerInputMessages failed:", e);
	}

	return {
		title: <div className={quickAccessMenuClasses.Title}>Decktation</div>,
		content: <DectationPanel logic={logic} />,
		icon: <FaMicrophone />,
		onDismount() {
			if (input_register) {
				input_register.unregister();
			}
			if (logic.recording) {
				serverApi.callPluginMethod('stop_recording', {});
			}
		},
		alwaysRender: true
	};
});
