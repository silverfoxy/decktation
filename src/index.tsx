import {
	definePlugin,
	Router,
	getGamepadNavigationTrees,
	PanelSection,
	PanelSectionRow,
	quickAccessMenuClasses,
	ToggleField,
	ButtonItem,
	DropdownOption,
	DropdownItem,
	Focusable,
	GamepadButton,
	Menu,
	MenuItem,
	showContextMenu,
	gamepadContextMenuClasses,
} from "decky-frontend-lib";

import { quickAccessVisibility } from "./quickAccessVisibility";

import { callable, toaster } from "@decky/api";

import React, {
	VFC,
	useEffect,
	useRef,
	useState,
} from "react";

import { FaMicrophone, FaTrash } from "react-icons/fa";

type RpcResponse = { success: boolean; error?: string; [key: string]: any };

const getStatus = callable<[], RpcResponse>("get_status");
const startBindingCapture = callable<[], RpcResponse>("start_binding_capture");
const getBindingCapture = callable<[session: string], RpcResponse>("get_binding_capture");
const cancelBindingCapture = callable<[session: string], RpcResponse>("cancel_binding_capture");
const setRecordingModeRpc = callable<[mode: string], RpcResponse>("set_recording_mode");
const getButtonConfig = callable<[], RpcResponse>("get_button_config");
const getPresets = callable<[], RpcResponse>("get_presets");
const setEnabledRpc = callable<[enabled: boolean], RpcResponse>("set_enabled");
const loadModel = callable<[], RpcResponse>("load_model");
const startRecording = callable<[], RpcResponse>("start_recording");
const stopRecording = callable<[send?: boolean], RpcResponse>("stop_recording");
const getLastTranscription = callable<[], RpcResponse>("get_last_transcription");
const setSendingModeRpc = callable<[mode: string], RpcResponse>("set_sending_mode");
const cancelDraftRpc = callable<[draftId: string], RpcResponse>("cancel_draft");
const armDraftRpc = callable<[draftId: string], RpcResponse>("arm_draft");
const setReviewContextRpc = callable<[visible: boolean, known: boolean], RpcResponse>("set_review_context");
const sendArmedDraftRpc = callable<[draftId: string], RpcResponse>("send_armed_draft");
type PendingDraft = { id: string; text: string; destination: string; action: string; mode: string; error: string; sending: boolean; manual: boolean };
const setManualSendRpc = callable<[enabled: boolean], RpcResponse>("set_manual_send");
const setRememberLastChannelRpc = callable<[enabled: boolean], RpcResponse>("set_remember_last_channel");
const setShareDiagnosticsRpc = callable<[enabled: boolean], RpcResponse>("set_share_diagnostics");
const setRecordingIndicatorRpc = callable<[mode: string], RpcResponse>("set_recording_indicator");
const setHapticFeedbackRpc = callable<[enabled: boolean], RpcResponse>("set_haptic_feedback");
const setActivePresetRpc = callable<[game: string], RpcResponse>("set_active_preset");
const setModelSizeRpc = callable<[modelSize: string], RpcResponse>("set_model_size");
const setTranscriptionOptionsRpc = callable<
	[language: string],
	RpcResponse
>("set_transcription_options");
const setButtonConfig = callable<
	[buttons: string[]],
	RpcResponse
>("set_button_config");

class DecktationLogic {
	enabled: boolean = false;
	recording: boolean = false;
	recordingIndicator: string = "toast";
	prevRecordingStartCount: number = 0;
	prevPendingId: string = "";
	pendingSince: number = 0;
	announcedDraftId: string = "";
	qamVisible: boolean = false;
	qamKnown: boolean = false;
	readQamVisibility: (() => boolean | null) | null = null;
	qamClosedAt: number = Date.now();
	armedDraftId: string = "";
	lastPendingToastId: number = -1;

	notify = async (message: string, duration: number = 2000, body: string = ""): Promise<number> => {
		if (!body) {
			body = message;
		}
		const toast: any = {
			title: message,
			body: body,
			duration: duration,
			critical: false,
		};
		const id: number = (window as any).NotificationStore ? (window as any).NotificationStore.m_nNextTestNotificationID++ : 0;
		const toastData: any = {
			nNotificationID: id,
			bNewIndicator: false,
			rtCreated: Date.now(),
			eType: 43,
			eSource: 1,
			nToastDurationMS: duration,
			data: toast,
			decky: true,
		};
		const info: any = {
			showToast: true,
			sound: 6,
			playSound: false,
			eFeature: 0,
			toastDurationMS: duration,
			bCritical: false,
			fnTray: (_t: any, tray: any) => { tray.unshift({ eType: 31, notifications: [toastData] }); },
		};
		try {
			(window as any).NotificationStore.ProcessNotification(info, toastData, 0);
		} catch (_e) {
			// fallback to standard toaster if direct call fails
			toaster.toast({ title: message, body: toast.body, duration: duration, critical: false });
		}
		return id;
	}

	dismissNotification = (id: number) => {
		// Force-expire the toast by reprocessing it with a 1ms duration
		try {
			const toastData: any = {
				nNotificationID: id,
				bNewIndicator: false,
				rtCreated: Date.now(),
				eType: 43,
				eSource: 1,
				nToastDurationMS: 1,
				data: { title: "", body: "", duration: 1, critical: false },
				decky: true,
			};
			const info: any = {
				showToast: true,
				sound: 6,
				playSound: false,
				eFeature: 0,
				toastDurationMS: 1,
				bCritical: false,
				fnTray: (_t: any, tray: any) => { tray.unshift({ eType: 31, notifications: [toastData] }); },
			};
			(window as any).NotificationStore.ProcessNotification(info, toastData, 0);
		} catch (_e) {}
	}

	testRecording = async (
		onComplete: (text: string, time: string) => void,
		onPhase: (phase: "recording" | "transcribing" | "idle") => void,
	) => {
		onPhase("recording");
		try {
			if (this.recordingIndicator === "toast") this.notify("Decktation", 1000, "Recording for 3 seconds...");
			const started = await startRecording();
			if (!started.success) throw new Error(started.error || "Could not start test recording");

			await new Promise(resolve => setTimeout(resolve, 3000));
			// Keep the no-send argument: test text must never reach the active game.
			onPhase("transcribing");
			const transcription = stopRecording(false);
			if (this.recordingIndicator === "toast") this.notify("Decktation", 1500, "Transcribing...");
			const stopped = await transcription;
			if (!stopped.success) throw new Error(stopped.error || "Could not transcribe test recording");

			const result = await getLastTranscription();
			if (!result.success) throw new Error(result.error || "Could not read test transcription");
			const data = result.transcription;
			onComplete(
				data?.text || "",
				data?.timestamp ? new Date(data.timestamp * 1000).toLocaleTimeString() : "",
			);
		} finally {
			onPhase("idle");
		}
	}
}

// Available button options
const BUTTON_OPTIONS: DropdownOption[] = [
	{ data: "L1", label: "L1 Bumper" },
	{ data: "R1", label: "R1 Bumper" },
	{ data: "L2", label: "L2 Trigger" },
	{ data: "R2", label: "R2 Trigger" },
	{ data: "L4", label: "L4 Grip" },
	{ data: "R4", label: "R4 Grip" },
	{ data: "L5", label: "L5 Grip" },
	{ data: "R5", label: "R5 Grip" },
	{ data: "A", label: "A" },
	{ data: "B", label: "B" },
	{ data: "X", label: "X" },
	{ data: "Y", label: "Y" },
];

const WHISPER_LANGUAGE_OPTIONS: DropdownOption[] = [
	{ data: "auto", label: "Auto Detect" },
	{ data: "af", label: "Afrikaans" },
	{ data: "am", label: "Amharic" },
	{ data: "ar", label: "Arabic" },
	{ data: "as", label: "Assamese" },
	{ data: "az", label: "Azerbaijani" },
	{ data: "ba", label: "Bashkir" },
	{ data: "be", label: "Belarusian" },
	{ data: "bg", label: "Bulgarian" },
	{ data: "bn", label: "Bengali" },
	{ data: "bo", label: "Tibetan" },
	{ data: "br", label: "Breton" },
	{ data: "bs", label: "Bosnian" },
	{ data: "ca", label: "Catalan" },
	{ data: "cs", label: "Czech" },
	{ data: "cy", label: "Welsh" },
	{ data: "da", label: "Danish" },
	{ data: "de", label: "German" },
	{ data: "el", label: "Greek" },
	{ data: "en", label: "English" },
	{ data: "es", label: "Spanish" },
	{ data: "et", label: "Estonian" },
	{ data: "eu", label: "Basque" },
	{ data: "fa", label: "Persian" },
	{ data: "fi", label: "Finnish" },
	{ data: "fo", label: "Faroese" },
	{ data: "fr", label: "French" },
	{ data: "gl", label: "Galician" },
	{ data: "gu", label: "Gujarati" },
	{ data: "ha", label: "Hausa" },
	{ data: "haw", label: "Hawaiian" },
	{ data: "he", label: "Hebrew" },
	{ data: "hi", label: "Hindi" },
	{ data: "hr", label: "Croatian" },
	{ data: "ht", label: "Haitian Creole" },
	{ data: "hu", label: "Hungarian" },
	{ data: "hy", label: "Armenian" },
	{ data: "id", label: "Indonesian" },
	{ data: "is", label: "Icelandic" },
	{ data: "it", label: "Italian" },
	{ data: "ja", label: "Japanese" },
	{ data: "jw", label: "Javanese" },
	{ data: "ka", label: "Georgian" },
	{ data: "kk", label: "Kazakh" },
	{ data: "km", label: "Khmer" },
	{ data: "kn", label: "Kannada" },
	{ data: "ko", label: "Korean" },
	{ data: "la", label: "Latin" },
	{ data: "lb", label: "Luxembourgish" },
	{ data: "ln", label: "Lingala" },
	{ data: "lo", label: "Lao" },
	{ data: "lt", label: "Lithuanian" },
	{ data: "lv", label: "Latvian" },
	{ data: "mg", label: "Malagasy" },
	{ data: "mi", label: "Maori" },
	{ data: "mk", label: "Macedonian" },
	{ data: "ml", label: "Malayalam" },
	{ data: "mn", label: "Mongolian" },
	{ data: "mr", label: "Marathi" },
	{ data: "ms", label: "Malay" },
	{ data: "mt", label: "Maltese" },
	{ data: "my", label: "Myanmar" },
	{ data: "ne", label: "Nepali" },
	{ data: "nl", label: "Dutch" },
	{ data: "nn", label: "Norwegian Nynorsk" },
	{ data: "no", label: "Norwegian" },
	{ data: "oc", label: "Occitan" },
	{ data: "pa", label: "Punjabi" },
	{ data: "pl", label: "Polish" },
	{ data: "ps", label: "Pashto" },
	{ data: "pt", label: "Portuguese" },
	{ data: "ro", label: "Romanian" },
	{ data: "ru", label: "Russian" },
	{ data: "sa", label: "Sanskrit" },
	{ data: "sd", label: "Sindhi" },
	{ data: "si", label: "Sinhala" },
	{ data: "sk", label: "Slovak" },
	{ data: "sl", label: "Slovenian" },
	{ data: "sn", label: "Shona" },
	{ data: "so", label: "Somali" },
	{ data: "sq", label: "Albanian" },
	{ data: "sr", label: "Serbian" },
	{ data: "su", label: "Sundanese" },
	{ data: "sv", label: "Swedish" },
	{ data: "sw", label: "Swahili" },
	{ data: "ta", label: "Tamil" },
	{ data: "te", label: "Telugu" },
	{ data: "tg", label: "Tajik" },
	{ data: "th", label: "Thai" },
	{ data: "tk", label: "Turkmen" },
	{ data: "tl", label: "Tagalog" },
	{ data: "tr", label: "Turkish" },
	{ data: "tt", label: "Tatar" },
	{ data: "uk", label: "Ukrainian" },
	{ data: "ur", label: "Urdu" },
	{ data: "uz", label: "Uzbek" },
	{ data: "vi", label: "Vietnamese" },
	{ data: "yi", label: "Yiddish" },
	{ data: "yo", label: "Yoruba" },
	{ data: "yue", label: "Cantonese" },
	{ data: "zh", label: "Chinese" },
];

const MODEL_SIZE_OPTIONS: DropdownOption[] = [
	{ data: "base", label: "Base · Fast" },
	{ data: "small", label: "Small · Balanced" },
	{ data: "medium", label: "Medium · More accurate" },
];

const POPULAR_STEAM_LANGUAGE_CODES = new Set(["en", "zh", "ru", "es", "pt", "de", "ja", "fr", "pl", "ko"]);
const byLanguageName = (left: DropdownOption, right: DropdownOption) => String(left.label).localeCompare(String(right.label));
const POPULAR_LANGUAGE_OPTIONS = WHISPER_LANGUAGE_OPTIONS.filter(option => POPULAR_STEAM_LANGUAGE_CODES.has(String(option.data))).sort(byLanguageName);
const OTHER_LANGUAGE_OPTIONS = WHISPER_LANGUAGE_OPTIONS.filter(option => option.data !== "auto" && !POPULAR_STEAM_LANGUAGE_CODES.has(String(option.data))).sort(byLanguageName);

const PRESET_DISPLAY_NAMES: Record<string, string> = {
	wow: "World of Warcraft",
	guildwars2: "Guild Wars 2",
	generic: "Generic",
};

type PanelPage = "main" | "advanced" | "diagnostics" | "help" | "game" | "model" | "recording-mode";

const DecktationPanel: VFC<{ logic: DecktationLogic }> = ({ logic }) => {
	const [page, setPage] = useState<PanelPage>("main");
	const panelRef = useRef<HTMLDivElement>(null);
	const languageMenuAnchorRef = useRef<HTMLSpanElement>(null);
	const advancedModelRowRef = useRef<HTMLDivElement>(null);
	const [capture, setCapture] = useState<{ session: string; phase: string; buttons: string[] } | null>(null);
	const captureRef = useRef<string | null>(null);
	const captureFocusRef = useRef<HTMLDivElement>(null);
	const [bindingMessage, setBindingMessage] = useState("");
	const [enabled, setEnabled] = useState<boolean>(false);
	const [recording, setRecording] = useState<boolean>(false);
	const [serviceReady, setServiceReady] = useState<boolean>(false);
	const [modelReady, setModelReady] = useState<boolean>(false);
	const [inferenceDevice, setInferenceDevice] = useState<"cpu" | "gpu" | null>(null);
	const [modelLoading, setModelLoading] = useState<boolean>(false);
	const [isToggling, setIsToggling] = useState<boolean>(false);
	const [inputReady, setInputReady] = useState<boolean>(true);
	const [buttonState, setButtonState] = useState<string>("None");
	const [controllerReady, setControllerReady] = useState<boolean>(false);
	const [recordingMode, setRecordingMode] = useState<"hold" | "tap">("hold");
	const [controllerStatus, setControllerStatus] = useState<string>("Waiting for input");
	const [controllerComboSupported, setControllerComboSupported] = useState<boolean>(true);
	const [buttons, setButtons] = useState<string[]>(["L1", "R1"]);
	const [recordingIndicator, setRecordingIndicator] = useState<string>("toast");
	const [hapticFeedback, setHapticFeedback] = useState<boolean>(false);
	const [activePreset, setActivePreset] = useState<string>("wow");
	const [presets, setPresets] = useState<DropdownOption[]>([]);
	const [sendingMode, setSendingMode] = useState<string>("immediate");
	const [pendingDraft, setPendingDraft] = useState<PendingDraft | null>(null);
	const reviewTextRef = useRef<HTMLDivElement>(null);
	const [draftBusy, setDraftBusy] = useState<boolean>(false);
	const [qamVisible, setQamVisible] = useState<boolean>(false);
	useEffect(() => {
		const read = () => {
			const documents: Document[] = [];
			if (panelRef.current) documents.push(panelRef.current.ownerDocument);
			try {
				for (const tree of getGamepadNavigationTrees() || []) {
					if (!String(tree?.id || "").startsWith("QuickAccess")) continue;
					const doc = tree?.m_Root?.m_element?.ownerDocument as Document | undefined;
					if (doc && !documents.includes(doc)) documents.push(doc);
				}
			} catch (_error) { /* Inspect the mounted panel's document instead. */ }
			return quickAccessVisibility(documents, [quickAccessMenuClasses.QuickAccessMenu, quickAccessMenuClasses.Menu]);
		};
		const update = () => {
			const visible = read();
			if (visible === false && logic.qamVisible) logic.qamClosedAt = Date.now();
			const changed = logic.qamKnown !== (visible !== null) || logic.qamVisible !== (visible === true);
			logic.qamKnown = visible !== null;
			logic.qamVisible = visible === true;
			setQamVisible(visible === true);
			if (changed) void setReviewContextRpc(logic.qamVisible, logic.qamKnown).catch(() => {});
		};
		logic.readQamVisibility = read;
		update();
		const interval = setInterval(update, 200);
		return () => { clearInterval(interval); logic.readQamVisibility = null; logic.qamKnown = false; };
	}, []);
	const [manualSend, setManualSend] = useState<boolean>(false);
	const [rememberLastChannel, setRememberLastChannel] = useState<boolean>(false);
	const [shareDiagnostics, setShareDiagnostics] = useState<boolean>(false);
	const [modelSize, setModelSize] = useState<string>("base");
	const [transcriptionLanguage, setTranscriptionLanguage] = useState<string>("auto");
	const [lastTranscription, setLastTranscription] = useState<string>("");
	const [lastTranscriptionTime, setLastTranscriptionTime] = useState<string>("");
	const [rpcError, setRpcError] = useState<string>("");
	const [reviewBlockReason, setReviewBlockReason] = useState<string>("");
	const [statusError, setStatusError] = useState<string>("");
	const [testPhase, setTestPhase] = useState<"idle" | "recording" | "transcribing">("idle");
	const [hasTestResult, setHasTestResult] = useState<boolean>(false);

	useEffect(() => {
		setEnabled(logic.enabled);
		setRecording(logic.recording);

		// Load button configuration, settings, and active game preset
		getButtonConfig().then((result) => {
			if (result.success) {
				const config = result.config;
				if (config) {
					setRecordingMode(config.recordingMode === "tap" ? "tap" : "hold");
					if (config.buttons) {
						setButtons(config.buttons);
					}
					const indicator = config.recordingIndicator || (config.showNotifications === false ? "none" : "toast");
					setRecordingIndicator(indicator);
					logic.recordingIndicator = indicator;
					if (config.hapticFeedback !== undefined) {
						setHapticFeedback(config.hapticFeedback);
					}
					if (config.game) {
						setActivePreset(config.game);
					}
					setSendingMode(config.sendingMode || (config.confirmMode ? "countdown" : "immediate"));
					if (config.manualSend !== undefined) {
						setManualSend(config.manualSend);
					}
					if (config.rememberLastChannel !== undefined) {
						setRememberLastChannel(config.rememberLastChannel);
					}
					if (config.shareDiagnostics !== undefined) {
						setShareDiagnostics(config.shareDiagnostics);
					}
					if (config.modelSize) {
						setModelSize(config.modelSize);
					}
					if (config.transcriptionLanguage) {
						setTranscriptionLanguage(config.transcriptionLanguage);
					}
					// Restore enabled state
					if (config.enabled) {
						setEnabled(true);
						logic.enabled = true;
						setModelLoading(true);
						void loadModel();
					}
				}
			}
		}).catch((error) => setRpcError(String(error)));

		// Load available game presets
		getPresets().then((result) => {
			if (result.success) {
				const opts: DropdownOption[] = result.presets.map((p: { id: string; name: string }) => ({
					data: p.id,
					label: PRESET_DISPLAY_NAMES[p.id] || p.name,
				}));
				setPresets(opts);
			}
		}).catch((error) => setRpcError(String(error)));
	}, []);

	useEffect(() => {
		let cancelled = false;
		let timeout: ReturnType<typeof setTimeout> | undefined;
		const poll = async () => {
			try {
				const result = await getStatus();
				if (cancelled) return;
				if (result.success) {
					setStatusError("");
					setButtonState(result.detected_button || "None");
					setControllerReady(result.controller_ready === true);
					setControllerStatus(result.controller_status || "Waiting for input");
					setControllerComboSupported(result.controller_combo_supported !== false);
					setStatusError("");
					setPendingDraft(result.pending_draft || null);
					setReviewBlockReason(result.review_block_reason || "");
					setServiceReady(result.service_ready);
					setModelReady(result.model_ready);
					setInferenceDevice(
						result.inference_device === "gpu" || result.inference_device === "cpu"
							? result.inference_device
							: null,
					);
					setModelLoading(result.model_loading);
					setInputReady(result.input_ready !== false);
					if (logic.enabled) {
						setRecording(result.recording);
					}
				} else {
					setControllerReady(false);
					setControllerStatus("Status unavailable");
					setStatusError(result.error || "Backend status request failed");
				}
			} catch (error) {
				setControllerReady(false);
				setControllerStatus("Status unavailable");
				setStatusError(String(error));
			} finally {
				if (!cancelled) timeout = setTimeout(poll, 100);
			}
		};
		void poll();
		return () => {
			cancelled = true;
			if (timeout) clearTimeout(timeout);
		};
	}, [logic.enabled]);

	useEffect(() => {
		// Steam's QAM keeps its scroll position when the content changes in place.
		const resetScroll = () => {
			let node = panelRef.current?.parentElement;
			while (node) {
				if (node.scrollHeight > node.clientHeight) node.scrollTop = 0;
				node = node.parentElement;
			}
		};
		resetScroll();
		const frame = requestAnimationFrame(() => {
			resetScroll();
			if (page === "advanced") {
				(advancedModelRowRef.current?.querySelector('[role="button"], button') as HTMLElement | null)?.focus();
			}
		});
		return () => cancelAnimationFrame(frame);
	}, [page]);

	useEffect(() => {
        if (!capture) return;
        let disposed = false;
        let timer: ReturnType<typeof setTimeout>;
        const pollCapture = async () => {
            try {
                const result = await getBindingCapture(capture.session);
                if (disposed) return;
                if (!result.success || result.phase === "cancelled" || result.phase === "saved") {
                    if (result.phase === "saved") {
                        setButtons(result.buttons);
                        setBindingMessage(`Binding saved: ${result.buttons.join(" + ")}`);
                    } else setRpcError(result.error || "Binding cancelled. Your previous binding is unchanged.");
                    captureRef.current = null;
                    setCapture(null);
                    return;
                }
                setCapture({ session: capture.session, phase: result.phase, buttons: result.buttons || [] });
            } catch (error) {
                if (!disposed) { setRpcError(String(error)); void cancelCapture(); }
                return;
            }
            if (!disposed) timer = setTimeout(pollCapture, 80);
        };
        captureFocusRef.current?.focus();
        void pollCapture();
        return () => { disposed = true; clearTimeout(timer); };
    }, [capture?.session]);
    useEffect(() => () => {
        if (captureRef.current) void cancelBindingCapture(captureRef.current);
    }, []);
    const beginCapture = async () => {
        setRpcError(""); setBindingMessage("");
        try {
            const result = await startBindingCapture();
            if (!result.success) { setRpcError(result.error || "Could not start binding capture"); return; }
            captureRef.current = result.session;
            setCapture({ session: result.session, phase: "release", buttons: [] });
        } catch (error) { setRpcError(String(error)); }
    };
    const cancelCapture = async () => {
        const session = captureRef.current;
        captureRef.current = null;
        setCapture(null);
        if (session) await cancelBindingCapture(session);
    };

	const scrollReview = (direction: number) => {
        const node = reviewTextRef.current;
        if (!node || (direction < 0 ? node.scrollTop <= 0 : node.scrollTop + node.clientHeight >= node.scrollHeight - 1)) return false;
        node.scrollTop += direction * 96;
        return true;
    };
	const goBack = () => setPage(page === "diagnostics" || page === "help" || page === "model" ? "advanced" : "main");
	const chooseLanguage = async (language: string) => {
		const result = await setTranscriptionOptionsRpc(language);
		if (result.success) {
			setTranscriptionLanguage(language);
			setRpcError("");
		} else {
			setRpcError(result.error || "Could not update language setting");
		}
	};
	const runTest = async () => {
		if (testPhase !== "idle") return;
		setRpcError("");
		setHasTestResult(false);
		try {
			await logic.testRecording((text, time) => {
				setLastTranscription(text);
				setLastTranscriptionTime(time);
				setHasTestResult(true);
			}, setTestPhase);
		} catch (error) {
			setRpcError(String(error));
		}
	};
	const statusMessage = statusError ? `Backend unavailable: ${statusError}`
		: rpcError ? rpcError
		: !serviceReady ? "Connecting to Decktation..."
		: !inputReady ? "Keyboard helper unavailable. Reload or reinstall Decktation."
		: recording ? "Recording..."
		: modelLoading ? "Loading transcription model..."
		: !enabled ? "Decktation is off"
		: !modelReady ? "Model not ready"
		: !controllerReady ? "Controller unavailable"
		: "Ready";
	const statusProblem = !!(statusError || rpcError || (serviceReady && !inputReady) || (enabled && serviceReady && !controllerReady));

    if (capture) {
        const swallow = (event: CustomEvent) => { event.preventDefault(); event.stopPropagation(); };
        return <Focusable ref={captureFocusRef} tabIndex={0} onButtonDown={swallow} onButtonUp={swallow}
            onOKButton={swallow} onCancelButton={swallow} onGamepadDirection={swallow}
            onActivate={swallow} onCancel={swallow}>
            <PanelSection title="Recording binding">
                <PanelSectionRow><div role="status">{capture.phase === "release"
                    ? "Release all buttons to start listening."
                    : "Hold your new combination together. Release to save."}</div></PanelSectionRow>
                <PanelSectionRow><div>Detected: <strong>{capture.buttons.join(" + ") || "Listening…"}</strong></div></PanelSectionRow>
                <PanelSectionRow><div style={{ fontSize: "12px", opacity: 0.85 }}>One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.</div></PanelSectionRow>
                <PanelSectionRow><button tabIndex={-1} onClick={() => { void cancelCapture(); }} style={{ padding: "10px 20px", color: "white", background: "#3b4252", border: 0, borderRadius: "4px" }}>Cancel (touch)</button></PanelSectionRow>
            </PanelSection>
        </Focusable>;
    }

	return (
		<Focusable onCancel={page === "main" ? undefined : (event) => {
			event.stopPropagation();
			goBack();
		}} onCancelActionDescription={page === "main" ? undefined : "Back"}>
			<div ref={panelRef}>
				<style>{`.decktation-trash-focused { outline: 3px solid #66c0f4 !important; outline-offset: 2px; background-color: #456b90 !important; box-shadow: 0 0 0 2px rgba(102, 192, 244, 0.38) !important; }`}</style>
				{pendingDraft && <PanelSection title="Review transcription">
					<PanelSectionRow><Focusable ref={reviewTextRef} tabIndex={0} aria-label="Transcription. Use Up and Down to scroll." style={{ fontSize: '16px', lineHeight: '1.5', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: '260px', overflowY: 'auto', padding: '4px' }} onGamepadDirection={(event) => {
						const direction = event.detail.button === GamepadButton.DIR_UP ? -1 : event.detail.button === GamepadButton.DIR_DOWN ? 1 : 0;
						if (direction && scrollReview(direction)) { event.preventDefault(); event.stopPropagation(); }
					}} onKeyDown={(event) => {
						const direction = event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0;
						if (direction && scrollReview(direction)) { event.preventDefault(); event.stopPropagation(); }
					}}>{pendingDraft.text}</Focusable></PanelSectionRow>
					<PanelSectionRow><div style={{ fontSize: '13px', color: '#adb8c4' }}>{pendingDraft.destination}{pendingDraft.manual ? " · After typing, press Enter in the game" : ""}</div></PanelSectionRow>
					{pendingDraft.error && <PanelSectionRow><div role="alert">{pendingDraft.error}</div></PanelSectionRow>}
					<PanelSectionRow><ButtonItem layout="below" disabled={draftBusy || pendingDraft.sending} onClick={async () => {
						setDraftBusy(true);
						try {
							await setReviewContextRpc(true, true);
							const result = await armDraftRpc(pendingDraft.id);
							if (result.success) {
								logic.armedDraftId = pendingDraft.id;
								Router.CloseSideMenus();
							} else setRpcError(result.error || "Could not approve draft");
						} catch (error) { setRpcError(String(error)); }
						finally { setDraftBusy(false); }
					}}>{pendingDraft.action}</ButtonItem></PanelSectionRow>
					<PanelSectionRow><div style={{ fontSize: '12px' }}>Closes this menu before typing into your game. Keep your game in the foreground.</div></PanelSectionRow>
					<PanelSectionRow><ButtonItem layout="below" disabled={draftBusy || pendingDraft.sending} onClick={async () => {
						setDraftBusy(true);
						try {
							const result = await cancelDraftRpc(pendingDraft.id);
							if (result.success) setPendingDraft(null);
							else setRpcError(result.error || "Could not cancel draft");
						} catch (error) { setRpcError(String(error)); }
						finally { setDraftBusy(false); }
					}}>Cancel</ButtonItem></PanelSectionRow>
				</PanelSection>}
				{page !== "main" && (
					<PanelSectionRow><ButtonItem layout="below" onClick={goBack}>Back</ButtonItem></PanelSectionRow>
				)}
				{page === "main" && <>
					<PanelSection title="Decktation">
						<PanelSectionRow>
							<ToggleField label="Enable" checked={enabled} disabled={!serviceReady || modelLoading || isToggling}
								onChange={async (next) => {
									if (isToggling) return;
									setIsToggling(true);
									setEnabled(next);
									logic.enabled = next;
									if (!next) {
										setModelReady(false);
										logic.recording = false;
										setRecording(false);
									}
									try {
										const result = await setEnabledRpc(next);
										if (!result.success) {
											setEnabled(!next);
											logic.enabled = !next;
											setRpcError(result.error || "Could not update enabled state");
											return;
										}
										if (next && logic.enabled) {
											setModelLoading(true);
											const modelResult = await loadModel();
											if (!modelResult.success) {
												setRpcError(modelResult.error || "Could not load Whisper model");
											}
										}
									} catch (error) {
										setEnabled(!next);
										logic.enabled = !next;
										setRpcError(String(error));
									} finally {
										setIsToggling(false);
									}
								}} />
						</PanelSectionRow>
						<PanelSectionRow>
							<div role="status" style={{ padding: statusProblem ? '10px' : '4px 0', borderRadius: '6px', backgroundColor: statusProblem ? '#713030' : undefined }}>
								{statusMessage}
							</div>
						</PanelSectionRow>
					</PanelSection>
					<PanelSection title="Quick settings">
						{presets.length > 0 && <PanelSectionRow><ButtonItem layout="below" onClick={() => setPage("game")}>
							Game: {presets.find(option => option.data === activePreset)?.label || activePreset}
						</ButtonItem></PanelSectionRow>}
						<PanelSectionRow><div style={{ position: 'relative', width: '100%' }}>
							<span ref={languageMenuAnchorRef} aria-hidden="true" style={{ position: 'absolute', left: 0, top: 0, width: '1px', height: '1px', pointerEvents: 'none' }} />
							<ButtonItem layout="below" onClick={(event) => {
							showContextMenu(
								<Menu label="Language">
									<MenuItem selected={transcriptionLanguage === "auto"} onSelected={() => { void chooseLanguage("auto"); }}>Auto Detect</MenuItem>
									<div className={gamepadContextMenuClasses.ContextMenuSeparator} />
									<div className={gamepadContextMenuClasses.MenuSectionHeader}>Popular Steam languages</div>
									{POPULAR_LANGUAGE_OPTIONS.map(option => <MenuItem key={String(option.data)} selected={option.data === transcriptionLanguage}
										onSelected={() => { void chooseLanguage(String(option.data)); }}>{option.label}</MenuItem>)}
									<div className={gamepadContextMenuClasses.ContextMenuSeparator} />
									<div className={gamepadContextMenuClasses.MenuSectionHeader}>Other languages</div>
									{OTHER_LANGUAGE_OPTIONS.map(option => <MenuItem key={String(option.data)} selected={option.data === transcriptionLanguage}
											onSelected={() => { void chooseLanguage(String(option.data)); }}>{option.label}</MenuItem>)}
								</Menu>,
								languageMenuAnchorRef.current || event.currentTarget,
							);
							}}>Language: {WHISPER_LANGUAGE_OPTIONS.find(option => option.data === transcriptionLanguage)?.label || transcriptionLanguage}</ButtonItem>
						</div></PanelSectionRow>

					</PanelSection>
                    <PanelSection title="Recording binding">
                        <PanelSectionRow><ButtonItem layout="below" disabled={recording || testPhase !== "idle"} onClick={() => setPage("recording-mode")}>Mode: {recordingMode === "hold" ? "Hold to record" : "Tap to start/stop"}</ButtonItem></PanelSectionRow>
                        <PanelSectionRow><div>{recordingMode === "hold" ? "Hold " : "Tap "}<strong>{buttons.join(" + ")}</strong>{recordingMode === "hold" ? " to record" : " to start; tap again to stop"}</div></PanelSectionRow>
                        {recordingMode === "tap" && <PanelSectionRow><div style={{ fontSize: "12px", opacity: 0.85 }}>You can also hold and release for a quick message.</div></PanelSectionRow>}
                        <PanelSectionRow><ButtonItem layout="below" disabled={!controllerReady || recording || testPhase !== "idle"} onClick={beginCapture}>Change binding</ButtonItem></PanelSectionRow>
                        {bindingMessage && <PanelSectionRow><div role="status">{bindingMessage}</div></PanelSectionRow>}
                    </PanelSection>
					<PanelSection title="Try it">
						<PanelSectionRow><ButtonItem layout="below" onClick={runTest}
							disabled={!enabled || !modelReady || modelLoading || recording || testPhase !== "idle"}>
							<FaMicrophone size={14} /> {testPhase === "recording" ? "Recording..." : testPhase === "transcribing" ? "Transcribing..." : "Test Dictation (3s)"}
						</ButtonItem></PanelSectionRow>
						<PanelSectionRow><div style={{ fontSize: '12px', opacity: 0.85 }}>Shows a transcription here without sending text to your game.</div></PanelSectionRow>
						{hasTestResult && <PanelSectionRow><div role="status" style={{ padding: '10px', backgroundColor: '#233829', borderRadius: '6px', overflowWrap: 'anywhere' }}>
							<strong>Result</strong><div>{lastTranscription || "No speech detected"}</div><small>{lastTranscriptionTime}</small>
						</div></PanelSectionRow>}
					</PanelSection>
					<PanelSectionRow><ButtonItem layout="below" onClick={() => setPage("advanced")}>Advanced settings</ButtonItem></PanelSectionRow>
				</>}
		{page === "advanced" && <>
					<PanelSection title="Transcription model">
						<PanelSectionRow><div ref={advancedModelRowRef}><ButtonItem layout="below" onClick={() => setPage("model")}>
							Model: {MODEL_SIZE_OPTIONS.find(option => option.data === modelSize)?.label || modelSize}
						</ButtonItem></div></PanelSectionRow>
						{modelReady && !modelLoading && inferenceDevice && (
							<PanelSectionRow><div>
								{inferenceDevice === "gpu"
									? "whisper.cpp runs on the GPU via Vulkan."
									: "whisper.cpp runs on the CPU."}
							</div></PanelSectionRow>
						)}
						<PanelSectionRow><div style={{ fontSize: '12px' }}>Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.</div></PanelSectionRow>
					</PanelSection>
					<PanelSection title="Sending">
						<PanelSectionRow><DropdownItem label="Transcription sending" menuLabel="Transcription sending" rgOptions={[{data:"immediate",label:"Send immediately"},{data:"review",label:"Review before sending"},{data:"countdown",label:"Send after countdown"}]} selectedOption={sendingMode} onChange={async (option) => {
							const next = option.data as string;
							const result = await setSendingModeRpc(next);
							if (result.success) { setSendingMode(next); setRpcError(""); }
							else setRpcError(result.error || "Could not update sending mode");
						}} /></PanelSectionRow>
						{sendingMode === "review" && <PanelSectionRow><div style={{ fontSize: '13px', lineHeight: '1.5' }}>Review stays visible until you decide. Tap {buttons.join('+')} to send; hold it to cancel. Open Decktation to review longer text.</div></PanelSectionRow>}
						<PanelSectionRow><ToggleField label="Press Enter yourself" description="Type into chat without submitting" checked={manualSend}
							onChange={async (next) => { setManualSend(next); await setManualSendRpc(next); }} /></PanelSectionRow>
						<PanelSectionRow><ToggleField label="Remember channel" description="Reuse the last spoken channel" checked={rememberLastChannel}
							onChange={async (next) => {
								setRememberLastChannel(next);
								const result = await setRememberLastChannelRpc(next);
								if (!result.success) { setRememberLastChannel(!next); setRpcError(result.error || "Could not update channel setting"); }
							}} /></PanelSectionRow>
					</PanelSection>
					<PanelSection title="Feedback">
						<PanelSectionRow><DropdownItem label="Recording cue" menuLabel="Recording cue" rgOptions={[{data:"toast",label:"Toast"},{data:"overlay",label:"Overlay"},{data:"none",label:"None"}]} selectedOption={recordingIndicator} onChange={async (option) => { const mode = option.data as string; setRecordingIndicator(mode); logic.recordingIndicator = mode; const result = await setRecordingIndicatorRpc(mode); if (!result.success) setRpcError(result.error || "Could not update recording cue"); }} /></PanelSectionRow>
						<PanelSectionRow><ToggleField label="Haptic feedback" description="Cues on the controller when recording starts and stops"
							checked={hapticFeedback} onChange={async (next) => {
								const result = await setHapticFeedbackRpc(next);
								if (result.success) setHapticFeedback(next);
								else setRpcError(result.error || "Could not update haptic feedback");
							}} /></PanelSectionRow>
					</PanelSection>
					<PanelSectionRow><ButtonItem layout="below" onClick={() => setPage("diagnostics")}>Diagnostics</ButtonItem></PanelSectionRow>
					<PanelSectionRow><ButtonItem layout="below" onClick={() => setPage("help")}>Help & permissions</ButtonItem></PanelSectionRow>
				</>}
				{page === "diagnostics" && <>
					<PanelSection title="Input and service">
						<PanelSectionRow><div>Controller: {controllerStatus}</div></PanelSectionRow>
						{pendingDraft && <PanelSectionRow><div>Review confirmation: {reviewBlockReason || "Ready"}</div></PanelSectionRow>}
						<PanelSectionRow><div>Binding supported: {controllerComboSupported ? "Yes" : "No"}</div></PanelSectionRow>
						<PanelSectionRow><div>Held buttons: <strong>{buttonState}</strong></div></PanelSectionRow>
						<PanelSectionRow><div>Keyboard helper: {inputReady ? "Ready" : "Unavailable"}</div></PanelSectionRow>
						<PanelSectionRow><div>Backend: {serviceReady ? "Ready" : "Unavailable"}</div></PanelSectionRow>
						<PanelSectionRow><div>Model: {modelLoading ? "Loading" : modelReady ? "Ready" : "Unavailable"}</div></PanelSectionRow>
						{(statusError || rpcError) && <PanelSectionRow><div role="alert">{statusError || rpcError}</div></PanelSectionRow>}
					</PanelSection>
					<PanelSection title="Diagnostics sharing">
						<PanelSectionRow><ToggleField label="Share" description="Optional scrubbed diagnostics sent to Sentry"
							checked={shareDiagnostics} onChange={async (next) => {
								setShareDiagnostics(next);
								const result = await setShareDiagnosticsRpc(next);
								if (!result.success) { setShareDiagnostics(!next); setRpcError(result.error || "Could not update diagnostics setting"); }
							}} /></PanelSectionRow>
					</PanelSection>
				</>}
				{page === "game" && <PanelSection title="Game">
					{rpcError && <PanelSectionRow><div role="alert">{rpcError}</div></PanelSectionRow>}
					{presets.map(option => <PanelSectionRow key={String(option.data)}><ButtonItem layout="below" onClick={async () => {
						const next = option.data as string;
						setRpcError("");
						const result = await setActivePresetRpc(next);
						if (result.success) { setActivePreset(next); setPage("main"); }
						else setRpcError(result.error || "Could not update game");
					}}>{option.data === activePreset ? "✓ " : ""}{option.label}</ButtonItem></PanelSectionRow>)}
				</PanelSection>}
                {page === "recording-mode" && <PanelSection title="Recording mode">
                    {rpcError && <PanelSectionRow><div role="alert">{rpcError}</div></PanelSectionRow>}
                    {(["hold", "tap"] as const).map(mode => <PanelSectionRow key={mode}>
                        <ButtonItem layout="below" disabled={recording} onClick={async () => {
                            setRpcError("");
                            try {
                                const result = await setRecordingModeRpc(mode);
                                if (result.success) { setRecordingMode(mode); setPage("main"); }
                                else setRpcError(result.error || "Could not change recording mode");
                            } catch (error) { setRpcError(String(error)); }
                        }}>{mode === recordingMode ? "✓ " : ""}{mode === "hold" ? "Hold to record" : "Tap to start/stop"}</ButtonItem>
                        <div style={{ fontSize: "12px", padding: "6px 0", opacity: 0.85 }}>{mode === "hold"
                            ? "Hold the binding to record. Release to stop and send."
                            : "Tap once to start recording, then tap again to stop. You can also hold and release for a quick message."}</div>
                    </PanelSectionRow>)}
                </PanelSection>}
				{page === "model" && <PanelSection title="Model">
					{rpcError && <PanelSectionRow><div role="alert">{rpcError}</div></PanelSectionRow>}
					{MODEL_SIZE_OPTIONS.map(option => <PanelSectionRow key={String(option.data)}><ButtonItem layout="below" onClick={async () => {
						const next = option.data as string;
						setRpcError("");
						if (enabled && modelReady) setModelLoading(true);
						const result = await setModelSizeRpc(next);
						if (result.success) { setModelSize(next); setPage("advanced"); }
						else { setModelLoading(false); setRpcError(result.error || "Could not update model size"); }
					}}>{option.data === modelSize ? "✓ " : ""}{option.label}</ButtonItem></PanelSectionRow>)}
				</PanelSection>}
				{page === "help" && <>
					<PanelSection title="How to use">
						<PanelSectionRow><div style={{ fontSize: '13px', lineHeight: '1.6' }}>
							{recordingMode === "hold" ? "Hold " : "Tap "}<strong>{buttons.join('+')}</strong> {recordingMode === "hold" ? "to record." : "to start recording; tap again to stop. Holding and releasing also works for quick messages."}
							Stopping transcribes and types into the active game or app. Keep it in the foreground.
						</div></PanelSectionRow>
					</PanelSection>
					<PanelSection title="Permissions">
						<PanelSectionRow><div style={{ fontSize: '13px', lineHeight: '1.5' }}>
							Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text.
							Your transcription is passed to the bundled keyboard helper as data, never as a shell command.
						</div></PanelSectionRow>
					</PanelSection>
				</>}
			</div>
		</Focusable>
	);
};


export default definePlugin(() => {
	let logic = new DecktationLogic();
	// Seed the recording start count so we don't fire a spurious toast on load
	getStatus().then((result) => {
		if (result.success) {
			logic.prevRecordingStartCount = result.recording_start_count || 0;
		}
	});

	// Background notification polling — runs for the full plugin lifetime regardless
	// of whether the Decky panel is open, so toasts appear while in-game.
	let notifyPollInFlight = false;
	const bgNotifyInterval = setInterval(async () => {
		if (!logic.enabled || notifyPollInFlight) return;
		notifyPollInFlight = true;
		try {
			const visible = logic.readQamVisibility?.() ?? null;
			if (visible === false && logic.qamVisible) logic.qamClosedAt = Date.now();
			logic.qamKnown = visible !== null;
			logic.qamVisible = visible === true;
			await setReviewContextRpc(logic.qamVisible, logic.qamKnown);
			if (logic.armedDraftId && logic.qamKnown && !logic.qamVisible && Date.now() - logic.qamClosedAt >= 500) {
				const draftId = logic.armedDraftId;
				logic.armedDraftId = "";
				const sent = await sendArmedDraftRpc(draftId);
				if (!sent.success) void logic.notify("Review transcription", 5000, sent.error || "Open Decktation to retry");
			}
			const result = await getStatus();
			if (result.success) {
				const startCount: number = result.recording_start_count || 0;
				if (logic.recordingIndicator === "toast" && startCount > logic.prevRecordingStartCount) {
					logic.notify("Recording", 1500, "🎤 Recording...");
				}
				logic.prevRecordingStartCount = startCount;

				const draft = result.pending_draft as PendingDraft | null;
				const draftId = draft?.id || "";
				if (draftId !== logic.prevPendingId) {
					logic.pendingSince = Date.now();
					logic.announcedDraftId = "";
					if (logic.lastPendingToastId >= 0) {
						logic.dismissNotification(logic.lastPendingToastId);
						logic.lastPendingToastId = -1;
					}
				}
				// Allow the native renderer time to start; notify on later failure too.
				if (draft && !result.preview_overlay?.visible && logic.announcedDraftId !== draftId && Date.now() - logic.pendingSince >= 2000) {
					logic.announcedDraftId = draftId;
					logic.lastPendingToastId = await logic.notify("Review transcription", 6000,
						`“${draft.text}” — open Decktation to ${draft.action.toLowerCase()} or cancel`);
				}
				logic.prevPendingId = draftId;
			}
		} catch (_e) {
		} finally {
			notifyPollInFlight = false;
		}
	}, 1000);

	return {
		title: <div className={quickAccessMenuClasses.Title}>Decktation</div>,
		content: <DecktationPanel logic={logic} />,
		icon: <FaMicrophone />,
		onDismount() {
			clearInterval(bgNotifyInterval);
			if (logic.recording) {
				void stopRecording();
			}
		},
		alwaysRender: true
	};
});
