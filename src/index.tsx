import {
	definePlugin,
	PanelSection,
	PanelSectionRow,
	ServerAPI,
	quickAccessMenuClasses,
	ToggleField,
	ButtonItem,
	Dropdown,
	SingleDropdownOption,
} from "decky-frontend-lib";

import {
	VFC,
	useEffect,
	useState,
} from "react";

import { FaMicrophone } from "react-icons/fa";

// Steam Deck button mappings
const BUTTONS = {
	R2: 0,
	L2: 1,
	R1: 2,
	L1: 3,
	Y: 4,
	B: 5,
	X: 6,
	A: 7,
	UP: 8,
	RIGHT: 9,
	LEFT: 10,
	DOWN: 11,
	SELECT: 12,
	STEAM: 13,
	START: 14,
	L5: 15,
	R5: 16,
};

const BUTTON_OPTIONS: SingleDropdownOption[] = [
	{ label: "A", data: BUTTONS.A },
	{ label: "B", data: BUTTONS.B },
	{ label: "X", data: BUTTONS.X },
	{ label: "Y", data: BUTTONS.Y },
	{ label: "L1", data: BUTTONS.L1 },
	{ label: "R1", data: BUTTONS.R1 },
	{ label: "L2", data: BUTTONS.L2 },
	{ label: "R2", data: BUTTONS.R2 },
	{ label: "L5", data: BUTTONS.L5 },
	{ label: "R5", data: BUTTONS.R5 },
	{ label: "D-Pad Up", data: BUTTONS.UP },
	{ label: "D-Pad Down", data: BUTTONS.DOWN },
	{ label: "D-Pad Left", data: BUTTONS.LEFT },
	{ label: "D-Pad Right", data: BUTTONS.RIGHT },
];

class DectationLogic {
	serverAPI: ServerAPI;
	enabled: boolean = false;
	recording: boolean = false;
	lastButtonPress: number = Date.now();
	selectedButton: number = BUTTONS.A; // Default: Steam + A
	steamPressed: boolean = false;

	constructor(serverAPI: ServerAPI) {
		this.serverAPI = serverAPI;
		// Load saved button preference
		const saved = localStorage.getItem('decktation_button');
		if (saved !== null) {
			this.selectedButton = parseInt(saved);
		}
	}

	setButton(buttonId: number) {
		this.selectedButton = buttonId;
		localStorage.setItem('decktation_button', buttonId.toString());
	}

	notify = async (message: string, duration: number = 2000, body: string = "") => {
		if (!body) {
			body = message;
		}
		this.serverAPI.toaster.toast({
			title: message,
			body: body,
			duration: duration,
			critical: true
		});
	}

	handleButtonInput = async (val: any[]) => {
		if (!this.enabled) {
			return;
		}

		for (const inputs of val) {
			const steamPressed = !!(inputs.ulButtons && inputs.ulButtons & (1 << BUTTONS.STEAM));
			const buttonPressed = !!(inputs.ulButtons && inputs.ulButtons & (1 << this.selectedButton));

			// Check if Steam + selected button combo is pressed
			const comboPressed = steamPressed && buttonPressed;

			// Start recording when combo is pressed
			if (comboPressed && !this.recording) {
				// Debounce
				if (Date.now() - this.lastButtonPress < 200) {
					continue;
				}
				this.lastButtonPress = Date.now();
				this.recording = true;
				await this.serverAPI.callPluginMethod('start_recording', {});
				this.notify("Decktation", 1500, "Recording...");
			}
			// Stop recording when combo is released
			else if (!comboPressed && this.recording) {
				this.lastButtonPress = Date.now();
				this.recording = false;
				await this.serverAPI.callPluginMethod('stop_recording', {});
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

const DectationPanel: VFC<{ logic: DectationLogic }> = ({ logic }) => {
	const [enabled, setEnabled] = useState<boolean>(false);
	const [recording, setRecording] = useState<boolean>(false);
	const [selectedButton, setSelectedButton] = useState<number>(logic.selectedButton);
	const [depsInstalled, setDepsInstalled] = useState<boolean>(false);
	const [serviceReady, setServiceReady] = useState<boolean>(false);

	useEffect(() => {
		setEnabled(logic.enabled);
		setRecording(logic.recording);
	}, []);

	// Poll plugin status
	useEffect(() => {
		const interval = setInterval(async () => {
			const result = await logic.serverAPI.callPluginMethod('get_status', {});
			if (result.success && result.result) {
				setDepsInstalled(result.result.dependencies_installed);
				setServiceReady(result.result.service_ready);
				if (logic.enabled) {
					setRecording(result.result.recording);
				}
			}
		}, 1000);
		return () => clearInterval(interval);
	}, [logic.enabled]);

	const getButtonLabel = (buttonId: number): string => {
		const option = BUTTON_OPTIONS.find(opt => opt.data === buttonId);
		return option ? option.label : "Unknown";
	};

	return (
		<div>
			<PanelSection>
				{!depsInstalled && (
					<PanelSectionRow>
						<div style={{
							padding: '10px',
							backgroundColor: '#ff9800',
							borderRadius: '8px',
							textAlign: 'center',
							fontWeight: 'bold'
						}}>
							⏳ Installing dependencies... (first run)
						</div>
					</PanelSectionRow>
				)}
				{depsInstalled && !serviceReady && (
					<PanelSectionRow>
						<div style={{
							padding: '10px',
							backgroundColor: '#2196f3',
							borderRadius: '8px',
							textAlign: 'center',
							fontWeight: 'bold'
						}}>
							⏳ Loading Whisper model...
						</div>
					</PanelSectionRow>
				)}
				<PanelSectionRow>
					<ToggleField
						label="Enable Dictation"
						checked={enabled}
						disabled={!serviceReady}
						onChange={(e) => {
							setEnabled(e);
							logic.enabled = e;
							if (!e && logic.recording) {
								logic.serverAPI.callPluginMethod('stop_recording', {});
								logic.recording = false;
								setRecording(false);
							}
						}}
					/>
				</PanelSectionRow>

				<PanelSectionRow>
					<Dropdown
						rgOptions={BUTTON_OPTIONS}
						label="Push-to-Talk Button"
						strDefaultLabel={getButtonLabel(selectedButton)}
						selectedOption={selectedButton}
						onChange={(option) => {
							setSelectedButton(option.data);
							logic.setButton(option.data);
						}}
						disabled={recording}
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
						Hold: <strong>Steam + {getButtonLabel(selectedButton)}</strong>
					</div>
				</PanelSectionRow>

				{enabled && (
					<PanelSectionRow>
						<div style={{
							padding: '10px',
							backgroundColor: recording ? '#4ade80' : '#374151',
							borderRadius: '8px',
							textAlign: 'center',
							fontWeight: 'bold'
						}}>
							{recording ? '🎤 Recording...' : '⏸ Ready'}
						</div>
					</PanelSectionRow>
				)}

				<PanelSectionRow>
					<ButtonItem
						layout="below"
						onClick={() => logic.testRecording()}
						disabled={!enabled}
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
							<li>Hold <strong>Steam + {getButtonLabel(selectedButton)}</strong> to record</li>
							<li>Release to transcribe and type into active window</li>
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
	let input_register = window.SteamClient.Input.RegisterForControllerStateChanges(logic.handleButtonInput);

	return {
		title: <div className={quickAccessMenuClasses.Title}>Decktation</div>,
		content: <DectationPanel logic={logic} />,
		icon: <FaMicrophone />,
		onDismount() {
			// Cleanup
			input_register.unregister();
			if (logic.recording) {
				serverApi.callPluginMethod('stop_recording', {});
			}
		},
		alwaysRender: true
	};
});
