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

import { requestPluginUpdate } from "./pluginUpdate";
import { ControllerDebugClient } from "./controllerDebug";
import { version as pluginVersion } from "../package.json";

import { quickAccessVisibility } from "./quickAccessVisibility";

import { callable, toaster } from "@decky/api";

import React, {
	VFC,
	useEffect,
	useRef,
	useState,
} from "react";

import { FaMicrophone, FaArrowCircleUp } from "react-icons/fa";

import { t, getInterfacePreference, setInterfacePreference, languageName, initializeSteamLanguage, INTERFACE_LANGUAGE_OPTIONS, InterfacePreference } from "./i18n";

type RpcResponse = { success: boolean; error?: string; [key: string]: any };

const setOverlayLabel = callable<[label: string], RpcResponse>("set_overlay_transcribing_label");
const syncOverlayLanguage = () => setOverlayLabel(t("Transcribing...")).catch(() => {});
const getPluginUpdate = callable<[force: boolean], RpcResponse>("get_plugin_update");
const preparePluginUpdate = callable<[version: string], RpcResponse>("prepare_plugin_update");

const getStatus = callable<[], RpcResponse>("get_status");
const startBindingCapture = callable<[], RpcResponse>("start_binding_capture");
const getBindingCapture = callable<[session: string], RpcResponse>("get_binding_capture");
const cancelBindingCapture = callable<[session: string], RpcResponse>("cancel_binding_capture");
const startControllerDebug = callable<[], RpcResponse>("start_controller_debug");
const getControllerDebug = callable<[session: string], RpcResponse>("get_controller_debug");
const stopControllerDebug = callable<[session: string], RpcResponse>("stop_controller_debug");
const uploadControllerDebug = callable<[session: string, consent: boolean], RpcResponse>("upload_controller_debug");
const resumeControllerDebug = callable<[], RpcResponse>("resume_controller_debug");
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
const setTextInsertionModeRpc = callable<[mode: string], RpcResponse>("set_text_insertion_mode");
const setRememberLastChannelRpc = callable<[enabled: boolean], RpcResponse>("set_remember_last_channel");
const setShareDiagnosticsRpc = callable<[enabled: boolean], RpcResponse>("set_share_diagnostics");
const setRecordingIndicatorRpc = callable<[mode: string], RpcResponse>("set_recording_indicator");
const setHapticFeedbackRpc = callable<[enabled: boolean], RpcResponse>("set_haptic_feedback");
const setActivePresetRpc = callable<[game: string], RpcResponse>("set_active_preset");
const setModelSizeRpc = callable<[modelSize: string], RpcResponse>("set_model_size");
const setSpokenPunctuationRpc = callable<[enabled: boolean], RpcResponse>("set_spoken_punctuation");
const setTranscriptionOptionsRpc = callable<
	[language: string],
	RpcResponse
>("set_transcription_options");


class DecktationLogic {
    updateAvailable = false;
    updateListeners = new Set<(available: boolean) => void>();
    setUpdateAvailable(available: boolean) {
        this.updateAvailable = available;
        this.updateListeners.forEach(listener => listener(available));
    }

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
			if (this.recordingIndicator === "toast") this.notify("Decktation", 1000, t("Recording for 3 seconds..."));
			const started = await startRecording();
			if (!started.success) throw new Error(started.error || t("Could not start test recording"));

			await new Promise(resolve => setTimeout(resolve, 3000));
			// Keep the no-send argument: test text must never reach the active game.
			onPhase("transcribing");
			const transcription = stopRecording(false);
			if (this.recordingIndicator === "toast") this.notify("Decktation", 1500, t("Transcribing..."));
			const stopped = await transcription;
			if (!stopped.success) throw new Error(stopped.error || t("Could not transcribe test recording"));

			const result = await getLastTranscription();
			if (!result.success) throw new Error(result.error || t("Could not read test transcription"));
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

type PanelPage = "main" | "advanced" | "updates" | "diagnostics" | "microphone-help" | "help" | "game" | "model";

const DecktationPanel: VFC<{ logic: DecktationLogic }> = ({ logic }) => {
	const [interfaceLanguage, updateInterfaceLanguage] = useState(getInterfacePreference);
    const [, refreshLocale] = useState(0);
    useEffect(() => {
        let mounted = true;
        void initializeSteamLanguage().then(() => { if (mounted) { refreshLocale(value => value + 1); void syncOverlayLanguage(); } });
        return () => { mounted = false; };
    }, []);
	const [page, setPage] = useState<PanelPage>("main");
	const pageRef = useRef<PanelPage>(page);
	pageRef.current = page;
	const panelRef = useRef<HTMLDivElement>(null);
	const languageMenuAnchorRef = useRef<HTMLSpanElement>(null);
	const advancedModelRowRef = useRef<HTMLDivElement>(null);
    const updateActionRowRef = useRef<HTMLDivElement>(null);
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
	const [modelStage, setModelStage] = useState<"idle" | "downloading" | "loading">("idle");
	const modelChangeInFlight = useRef(false);
	const [isToggling, setIsToggling] = useState<boolean>(false);
	const [inputReady, setInputReady] = useState<boolean>(true);
	const [buttonState, setButtonState] = useState<string>("None");
	const [controllerReady, setControllerReady] = useState<boolean>(false);
	const [controllerStatus, setControllerStatus] = useState<string>("Waiting for input");
	const [controllerComboSupported, setControllerComboSupported] = useState<boolean>(true);
	const [buttons, setButtons] = useState<string[]>(["L1", "R1"]);
	const [recordingIndicator, setRecordingIndicator] = useState<string>("toast");
	const [hapticFeedback, setHapticFeedback] = useState<boolean>(false);
	const [activePreset, setActivePreset] = useState<string>("wow");
	const [presets, setPresets] = useState<DropdownOption[]>([]);
	const [sendingMode, setSendingMode] = useState<string>("immediate");
	const [pendingDraft, setPendingDraft] = useState<PendingDraft | null>(null);
	const microphoneHelpRef = useRef<HTMLDivElement>(null);
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
	const [textInsertionMode, setTextInsertionMode] = useState<string>("paste");
	const [rememberLastChannel, setRememberLastChannel] = useState<boolean>(false);
	const [shareDiagnostics, setShareDiagnostics] = useState<boolean>(false);
	const [controllerClient] = useState(() => new ControllerDebugClient({
        start: startControllerDebug, get: getControllerDebug, stop: stopControllerDebug,
        resume: resumeControllerDebug, upload: uploadControllerDebug,
    }));
    const [controllerDebug, setControllerDebug] = useState(controllerClient.view);
    useEffect(() => {
        const unsubscribe = controllerClient.subscribe(setControllerDebug);
        void controllerClient.connect();
        return () => { unsubscribe(); controllerClient.dispose(); };
    }, [controllerClient]);
    const controllerSnapshot = controllerDebug.snapshot;
    const controllerReport = controllerSnapshot.report;
    const controllerDebugError = controllerDebug.error || controllerSnapshot.error || "";
    const controllerSeconds = Math.ceil(controllerSnapshot.remaining_ms / 1000);
    const debugCaptureFocusRef = useRef<HTMLDivElement>(null);
    const debugCaptureActive = !controllerDebug.error && (controllerDebug.pending === "start" ||
        ["starting", "recording", "stopping"].includes(controllerSnapshot.state));
    // Review is separate from Diagnostics; Back dismisses only this frozen session.
    const [dismissedReportSession, setDismissedReportSession] = useState<string | null>(null);
    const debugReportReady = controllerSnapshot.state === "ready" && !!controllerReport &&
        controllerSnapshot.session !== dismissedReportSession;
    const closeControllerReport = () => {
        setDismissedReportSession(controllerSnapshot.session);
        setPage("diagnostics");
    };
    useEffect(() => {
        if (!debugCaptureActive) return;
        const frame = requestAnimationFrame(() => debugCaptureFocusRef.current?.focus());
        return () => cancelAnimationFrame(frame);
    }, [debugCaptureActive]);
    // The primary control stays mounted and focusable: repeat Start is a no-op,
    // never a Stop caused by Decky moving focus after an activation.
    const controllerButtonLabel = controllerDebug.pending === "start" || controllerSnapshot.state === "starting"
        ? t("Starting controller capture...")
        : controllerDebug.pending === "stop" || controllerSnapshot.state === "stopping"
        ? t("Finalizing controller report...")
        : controllerDebug.pending === "resume" ? t("Reconnecting controller capture...")
        : controllerDebug.error ? t("Retry controller status")
        : controllerSnapshot.state === "recording"
        ? `${t("Recording controller input")} · ${controllerSeconds} ${t("seconds remaining")}`
        : t("Start 30-second capture");
	const [modelSize, setModelSize] = useState<string>("base");
	const [transcriptionLanguage, setTranscriptionLanguage] = useState<string>("auto");
	const [spokenPunctuation, setSpokenPunctuation] = useState<boolean>(false);
	const [lastTranscription, setLastTranscription] = useState<string>("");
	const [lastTranscriptionTime, setLastTranscriptionTime] = useState<string>("");
	const [rpcError, setRpcError] = useState<string>("");
	const [reviewBlockReason, setReviewBlockReason] = useState<string>("");
	const [statusError, setStatusError] = useState<string>("");
	const [testPhase, setTestPhase] = useState<"idle" | "recording" | "transcribing">("idle");
	const [hasTestResult, setHasTestResult] = useState<boolean>(false);
    const [transcribing, setTranscribing] = useState(false);
    const [updateInfo, setUpdateInfo] = useState<RpcResponse | null>(null);
    const [updateError, setUpdateError] = useState("");
    const [updatePhase, setUpdatePhase] = useState<"idle" | "preparing" | "waiting">("idle");
    const [checkingUpdate, setCheckingUpdate] = useState(false);
    const updateChecked = useRef(false);
    const updateMounted = useRef(true);
    const updateInFlight = useRef(false);
    const updateTimer = useRef<ReturnType<typeof setTimeout>>();
    const checkUpdate = async (force = false) => {
        setCheckingUpdate(true);
        try {
            const result = await getPluginUpdate(force);
            if (!updateMounted.current) return;
            setUpdateInfo(result);
            logic.setUpdateAvailable(result.success && result.update_available === true);
            setUpdateError(result.success ? "" : t("Could not check for updates."));
        } catch (_error) {
            if (updateMounted.current) {
                setUpdateInfo(null);
                logic.setUpdateAvailable(false);
                setUpdateError(t("Could not check for updates."));
            }
        } finally {
            if (updateMounted.current) setCheckingUpdate(false);
        }
    };
    useEffect(() => {
        updateMounted.current = true;
        return () => {
            updateMounted.current = false;
            if (updateTimer.current) clearTimeout(updateTimer.current);
        };
    }, []);
    useEffect(() => {
        if (qamVisible && !updateChecked.current) {
            updateChecked.current = true;
            void checkUpdate();
        }
    }, [qamVisible]);
    const updateBusy = recording || transcribing || modelLoading || testPhase !== "idle" ||
        !!pendingDraft || !!capture || draftBusy || updatePhase !== "idle";
    const startUpdate = async () => {
        if (updateBusy || updateInFlight.current || !updateInfo?.update_available || logic.readQamVisibility?.() !== true) return;
        updateInFlight.current = true;
        setUpdatePhase("preparing");
        setUpdateError("");
        try {
            const prepared = await preparePluginUpdate(updateInfo.version);
            if (!updateMounted.current || logic.readQamVisibility?.() !== true) return;
            if (!prepared.success) {
                setUpdateError(t(prepared.error || "The update could not be verified, so it was not installed."));
                return;
            }
            const result = await requestPluginUpdate({artifact: prepared.artifact, version: prepared.version, hash: prepared.hash});
            if (!updateMounted.current) return;
            if (!result.success) {
                setUpdateError(t(result.error || "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP."));
                return;
            }
            setUpdatePhase("waiting");
            // Loader has no reliable cancellation callback. Recover if this instance survives.
            updateTimer.current = setTimeout(() => {
                updateTimer.current = undefined;
                updateInFlight.current = false;
                setUpdatePhase("idle");
            }, 8000);
        } catch (_error) {
            if (updateMounted.current) setUpdateError(t("The update could not be verified, so it was not installed."));
        } finally {
            if (!updateTimer.current) {
                updateInFlight.current = false;
                if (updateMounted.current) setUpdatePhase("idle");
            }
        }
    };


	useEffect(() => {
		setEnabled(logic.enabled);
		setRecording(logic.recording);

		// Load button configuration, settings, and active game preset
		getButtonConfig().then((result) => {
			if (result.success) {
				const config = result.config;
				if (config) {
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
					setTextInsertionMode(config.textInsertionMode || (config.typeAsKeys === true ? "ydotool" : "paste"));
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
					setSpokenPunctuation(config.spokenPunctuation === true);
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
					setModelLoading(result.model_loading === true || modelChangeInFlight.current);
					setModelStage(result.model_stage === "downloading" ? "downloading" : result.model_loading ? "loading" : "idle");
                    setTranscribing(result.transcribing === true);
					setInputReady(result.input_ready !== false);
					if (logic.enabled) {
						setRecording(result.recording);
					}
				} else {
					setControllerReady(false);
					setControllerStatus("Status unavailable");
					setStatusError(result.error || t("Backend status request failed"));
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
			if (page === "microphone-help") {
				if (microphoneHelpRef.current) { microphoneHelpRef.current.scrollTop = 0; microphoneHelpRef.current.focus(); }
			}
			if (page === "advanced" || page === "updates") {
				((page === "updates" ? updateActionRowRef.current : advancedModelRowRef.current)?.querySelector('[role="button"], button') as HTMLElement | null)?.focus();
			}
		});
		return () => cancelAnimationFrame(frame);
	}, [page, pendingDraft?.id, debugCaptureActive, debugReportReady, controllerSnapshot.session]);

	useEffect(() => {
		if (!qamVisible || !pendingDraft) return;
		const frame = requestAnimationFrame(() => {
			if (reviewTextRef.current) {
				reviewTextRef.current.scrollTop = 0;
				reviewTextRef.current.focus();
			}
		});
		return () => cancelAnimationFrame(frame);
	}, [qamVisible, pendingDraft?.id]);

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
                        setBindingMessage(t("Binding saved: {binding}", {binding: result.buttons.join(" + ")}));
                    } else setRpcError(t(result.error || "Binding cancelled. Your previous binding is unchanged."));
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
            if (!result.success) { setRpcError(t(result.error || "Could not start binding capture")); return; }
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
	const scrollMicrophoneHelp = (direction: number) => {
		const node = microphoneHelpRef.current;
		if (!node || (direction < 0 ? node.scrollTop <= 0 : node.scrollTop + node.clientHeight >= node.scrollHeight - 1)) return false;
		node.scrollTop += direction * 96;
		return true;
	};
	const goBack = () => setPage(page === "microphone-help" ? "diagnostics" : page === "updates" || page === "diagnostics" || page === "help" || page === "model" ? "advanced" : "main");
	const chooseLanguage = async (language: string) => {
		const result = await setTranscriptionOptionsRpc(language);
		if (result.success) {
			setTranscriptionLanguage(language);
			setRpcError("");
		} else {
			setRpcError(result.error || t("Could not update language setting"));
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
	const statusMessage = statusError ? t("Backend unavailable: {error}", {error: statusError})
		: rpcError ? rpcError
		: !serviceReady ? t("Connecting to Decktation...")
		: !inputReady ? t("Keyboard helper unavailable. Reload or reinstall Decktation.")
		: recording ? t("Recording...")
		: modelStage === "downloading" ? t("Downloading transcription model...")
		: modelLoading ? t("Loading transcription model...")
		: !enabled ? t("Decktation is off")
		: !modelReady ? t("Model not ready")
		: !controllerReady ? t(controllerStatus === "Waiting for input" ? "Waiting for input" : "Controller unavailable")
		: t("Ready");
	const statusProblem = !!(statusError || rpcError || (serviceReady && !inputReady) || (enabled && serviceReady && !controllerReady));

    if (debugCaptureActive) {
        const swallow = (event: CustomEvent) => { event.preventDefault(); event.stopPropagation(); };
        const stopping = controllerDebug.pending === "stop" || controllerSnapshot.state === "stopping";
        const live = controllerSnapshot.live_input;
        // Reserve each changing region: held controls scroll inside the card, not
        // the panel, and lifecycle/count updates never move the touch-only Stop.
        return <Focusable ref={debugCaptureFocusRef} tabIndex={0}
            onButtonDown={swallow} onButtonUp={swallow} onOKButton={swallow} onCancelButton={swallow}
            onGamepadDirection={swallow} onActivate={swallow} onCancel={swallow}>
            <div ref={panelRef} style={{minWidth: 0}}><PanelSection title={t("Controller input debugger")}>
                <PanelSectionRow><div role="status" aria-live="polite" style={{height: "64px", overflow: "hidden", lineHeight: "20px"}}>
                    <strong style={{display: "block", height: "40px"}}>{stopping ? t("Finalizing controller report...")
                        : controllerSnapshot.state === "recording" ? t("Recording controller input")
                        : t("Starting controller capture...")}</strong>
                    <div style={{height: "24px", fontVariantNumeric: "tabular-nums"}}>{controllerSnapshot.state === "recording" && !stopping
                        ? <>{controllerSeconds} {t("seconds remaining")}</> : "\u00a0"}</div>
                </div></PanelSectionRow>
                <PanelSectionRow><div role="status" aria-live="off" style={{height: "40px", lineHeight: "20px", fontSize: "13px", fontVariantNumeric: "tabular-nums", overflow: "hidden"}}>
                    {t("Events captured")}: {controllerSnapshot.event_count} · {t("Controller interfaces")}: {controllerSnapshot.device_count}
                </div></PanelSectionRow>
                <PanelSectionRow><div role="status" aria-live="polite" style={{height: "96px", overflowY: "auto", overflowWrap: "anywhere", fontSize: "14px", lineHeight: "20px"}}>
                    <strong>{t("Held buttons")}</strong>
                    {controllerSnapshot.state === "recording" && !stopping && live ? <>
                        {live.pressed.length ? live.pressed.map((entry, index) =>
                            <div key={`${entry.source}-${entry.button}-${index}`}>{entry.button} · {t("Source")}: {entry.source}</div>)
                            : <div>{t("No buttons held")}</div>}
                    </> : <div>{t("Live input unavailable")}</div>}
                </div></PanelSectionRow>
                <PanelSectionRow><button tabIndex={-1} disabled={!!controllerDebug.pending || stopping || !controllerSnapshot.session}
                    onClick={() => controllerClient.stop()}
                    style={{padding: "10px 12px", maxWidth: "100%", color: "white", background: "#3b4252", border: 0, borderRadius: "4px"}}>
                    {t("Stop and review (touch or mouse)")}
                </button></PanelSectionRow>
                <PanelSectionRow><div style={{fontSize: "12px", lineHeight: "16px", marginTop: "8px"}}>{t("Controller navigation is paused. Steam/Quick Access may open menus. Ends after 30 seconds; touch or mouse can stop early.")}</div></PanelSectionRow>
            </PanelSection></div>
        </Focusable>;
    }

    if (debugReportReady) {
        return <Focusable key={controllerSnapshot.session} onCancel={(event) => {
            event.stopPropagation();
            closeControllerReport();
        }} onCancelActionDescription={t("Back")}>
            <div ref={panelRef} style={{minWidth: 0}}><PanelSection title={t("Controller input debugger")}>
                {!controllerSnapshot.event_id && <PanelSectionRow><ButtonItem layout="below"
                    disabled={!!controllerDebug.pending} onClick={() => controllerClient.upload()}>{t("Send this report to Sentry")}</ButtonItem></PanelSectionRow>}
                <PanelSectionRow><ButtonItem layout="below" onClick={closeControllerReport}>{t("Back")}</ButtonItem></PanelSectionRow>
                <PanelSectionRow><div role="status" aria-live="polite" style={{fontSize: "13px", overflowWrap: "anywhere"}}>
                    {controllerDebug.pending === "upload" ? t("Sending") : controllerSnapshot.event_id
                        ? <>{t("Report submitted. Event ID")}: {controllerSnapshot.event_id}</>
                        : t("Controller report ready for review")}
                </div></PanelSectionRow>
                <PanelSectionRow><div style={{fontSize: "13px"}}>{t("Events captured")}: {controllerSnapshot.event_count} · {t("Controller interfaces")}: {controllerSnapshot.device_count}</div></PanelSectionRow>
                {controllerDebugError && <PanelSectionRow><div role="alert">{t(controllerDebugError)}</div></PanelSectionRow>}
                <PanelSectionRow><div style={{fontSize: "12px", marginTop: "8px"}}>{t("Nothing is sent automatically. Send shares only this report with Sentry.")}</div></PanelSectionRow>
                <PanelSectionRow><div style={{fontSize: "12px", marginTop: "8px"}}><strong>{t("Full sanitized report (scroll to inspect all fields)")}</strong>
                    <pre tabIndex={0} style={{whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: "min(160px, 22vh)", overflowY: "auto", fontSize: "11px"}}>{JSON.stringify(controllerReport, null, 2)}</pre>
                </div></PanelSectionRow>
            </PanelSection></div>
        </Focusable>;
    }

    if (capture) {
        const swallow = (event: CustomEvent) => { event.preventDefault(); event.stopPropagation(); };
        return <Focusable ref={captureFocusRef} tabIndex={0} onButtonDown={swallow} onButtonUp={swallow}
            onOKButton={swallow} onCancelButton={swallow} onGamepadDirection={swallow}
            onActivate={swallow} onCancel={swallow}>
            <PanelSection title={t("Recording binding")}>
                <PanelSectionRow><div role="status">{capture.phase === "release"
                    ? t("Release all buttons to start listening.")
                    : t("Hold your new combination together. Release to save.")}</div></PanelSectionRow>
                <PanelSectionRow><div>{t("Detected:")}{" "}<strong>{capture.buttons.join(" + ") || t("Listening…")}</strong></div></PanelSectionRow>
                <PanelSectionRow><div style={{ fontSize: "12px", opacity: 0.85 }}>{t("One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.")}</div></PanelSectionRow>
                <PanelSectionRow><button tabIndex={-1} onClick={() => { void cancelCapture(); }} style={{ padding: "10px 20px", color: "white", background: "#3b4252", border: 0, borderRadius: "4px" }}>{t("Cancel (touch)")}</button></PanelSectionRow>
            </PanelSection>
        </Focusable>;
    }

	return (
		<Focusable onCancel={page === "main" ? undefined : (event) => {
			event.stopPropagation();
			goBack();
		}} onCancelActionDescription={page === "main" ? undefined : t("Back")}>
			<div ref={panelRef}>
				<style>{`.decktation-trash-focused { outline: 3px solid #66c0f4 !important; outline-offset: 2px; background-color: #456b90 !important; box-shadow: 0 0 0 2px rgba(102, 192, 244, 0.38) !important; }`}</style>
				{pendingDraft && <PanelSection title={t("Review transcription")}>
					<PanelSectionRow><Focusable ref={reviewTextRef} tabIndex={0} aria-label={t("Transcription. Use Up and Down to scroll.")} style={{ fontSize: '16px', lineHeight: '1.5', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: '260px', overflowY: 'auto', padding: '4px' }} onGamepadDirection={(event) => {
						const direction = event.detail.button === GamepadButton.DIR_UP ? -1 : event.detail.button === GamepadButton.DIR_DOWN ? 1 : 0;
						if (direction && scrollReview(direction)) { event.preventDefault(); event.stopPropagation(); }
					}} onKeyDown={(event) => {
						const direction = event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0;
						if (direction && scrollReview(direction)) { event.preventDefault(); event.stopPropagation(); }
					}}>{pendingDraft.text}</Focusable></PanelSectionRow>
					<PanelSectionRow><div style={{ fontSize: '13px', color: '#adb8c4' }}>{t(pendingDraft.destination)}{pendingDraft.manual ? " · " + t("After typing, press Enter in the game") : ""}</div></PanelSectionRow>
					{pendingDraft.error && <PanelSectionRow><div role="alert">{t(pendingDraft.error)}</div></PanelSectionRow>}
					<PanelSectionRow><ButtonItem layout="below" disabled={draftBusy || pendingDraft.sending} onClick={async () => {
						setDraftBusy(true);
						try {
							await setReviewContextRpc(true, true);
							const result = await armDraftRpc(pendingDraft.id);
							if (result.success) {
								logic.armedDraftId = pendingDraft.id;
								Router.CloseSideMenus();
							} else setRpcError(result.error || t("Could not approve draft"));
						} catch (error) { setRpcError(String(error)); }
						finally { setDraftBusy(false); }
					}}>{t(pendingDraft.action)}</ButtonItem></PanelSectionRow>
					<PanelSectionRow><div style={{ fontSize: '12px' }}>{t("Closes this menu before typing into your game. Keep your game in the foreground.")}</div></PanelSectionRow>
					<PanelSectionRow><ButtonItem layout="below" disabled={draftBusy || pendingDraft.sending} onClick={async () => {
						setDraftBusy(true);
						try {
							const result = await cancelDraftRpc(pendingDraft.id);
							if (result.success) setPendingDraft(null);
							else setRpcError(result.error || t("Could not cancel draft"));
						} catch (error) { setRpcError(String(error)); }
						finally { setDraftBusy(false); }
					}}>{t("Cancel")}</ButtonItem></PanelSectionRow>
				</PanelSection>}
				{page !== "main" && (
					<PanelSectionRow><ButtonItem layout="below" onClick={goBack}>{t("Back")}</ButtonItem></PanelSectionRow>
				)}
				{page === "main" && <>
					<PanelSection title="Decktation">
                        {updateInfo?.success && updateInfo.update_available && <PanelSectionRow>
                            <ButtonItem layout="below" onClick={() => setPage("updates")}><span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}><FaArrowCircleUp aria-hidden="true" style={{ color: "#7cdb98", flexShrink: 0 }} /><span>{t("Update available: {version}", {version: updateInfo.version})}</span></span></ButtonItem>
                        </PanelSectionRow>}
						<PanelSectionRow>
							<ToggleField label={t("Enable")} checked={enabled} disabled={!serviceReady || modelLoading || isToggling}
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
											setRpcError(result.error || t("Could not update enabled state"));
											return;
										}
										if (next && logic.enabled) {
											setModelLoading(true);
											const modelResult = await loadModel();
											if (!modelResult.success) {
												setRpcError(modelResult.error || t("Could not load Whisper model"));
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
					<PanelSection title={t("Quick settings")}>

						{presets.length > 0 && <PanelSectionRow><ButtonItem layout="below" onClick={() => setPage("game")}>
							{t("Mode")}: {t(String(presets.find(option => option.data === activePreset)?.label || activePreset))}
						</ButtonItem></PanelSectionRow>}
						<PanelSectionRow><div style={{ position: 'relative', width: '100%' }}>
							<span ref={languageMenuAnchorRef} aria-hidden="true" style={{ position: 'absolute', left: 0, top: 0, width: '1px', height: '1px', pointerEvents: 'none' }} />
							<ButtonItem layout="below" onClick={(event) => {
							showContextMenu(
								<Menu label={t("Language")}>
									<MenuItem selected={transcriptionLanguage === "auto"} onSelected={() => { void chooseLanguage("auto"); }}>{t("Auto Detect")}</MenuItem>
									<div className={gamepadContextMenuClasses.ContextMenuSeparator} />
									<div className={gamepadContextMenuClasses.MenuSectionHeader}>{t("Popular Steam languages")}</div>
									{POPULAR_LANGUAGE_OPTIONS.map(option => <MenuItem key={String(option.data)} selected={option.data === transcriptionLanguage}
										onSelected={() => { void chooseLanguage(String(option.data)); }}>{languageName(String(option.data), String(option.label))}</MenuItem>)}
									<div className={gamepadContextMenuClasses.ContextMenuSeparator} />
									<div className={gamepadContextMenuClasses.MenuSectionHeader}>{t("Other languages")}</div>
									{OTHER_LANGUAGE_OPTIONS.map(option => <MenuItem key={String(option.data)} selected={option.data === transcriptionLanguage}
											onSelected={() => { void chooseLanguage(String(option.data)); }}>{languageName(String(option.data), String(option.label))}</MenuItem>)}
								</Menu>,
								languageMenuAnchorRef.current || event.currentTarget || undefined,
							);
							}}>{t("Language")}: {languageName(transcriptionLanguage, String(WHISPER_LANGUAGE_OPTIONS.find(option => option.data === transcriptionLanguage)?.label || transcriptionLanguage))}</ButtonItem>
						</div></PanelSectionRow>
						<PanelSectionRow><div>{t("Binding")}: <strong>{buttons.join(' + ')}</strong></div></PanelSectionRow>
						<PanelSectionRow><ButtonItem layout="below" disabled={!controllerReady || recording || !!pendingDraft || testPhase !== "idle"} onClick={beginCapture}>{t("Change binding")}</ButtonItem></PanelSectionRow>
                        {bindingMessage && <PanelSectionRow><div role="status">{bindingMessage}</div></PanelSectionRow>}
					</PanelSection>
					<PanelSection title={t("Try it")}>
						<PanelSectionRow><ButtonItem layout="below" onClick={runTest}
							disabled={!enabled || !modelReady || modelLoading || recording || testPhase !== "idle"}>
							<FaMicrophone size={14} /> {testPhase === "recording" ? t("Recording...") : testPhase === "transcribing" ? t("Transcribing...") : t("Test Dictation (3s)")}
						</ButtonItem></PanelSectionRow>
						<PanelSectionRow><div style={{ fontSize: '12px', opacity: 0.85 }}>{t("Shows a transcription here without sending text to your game.")}</div></PanelSectionRow>
						{hasTestResult && <PanelSectionRow><div role="status" style={{ padding: '10px', backgroundColor: '#233829', borderRadius: '6px', overflowWrap: 'anywhere' }}>
							<strong>{t("Result")}</strong><div>{lastTranscription || t("No speech detected")}</div><small>{lastTranscriptionTime}</small>
						</div></PanelSectionRow>}
					</PanelSection>
					<PanelSectionRow><ButtonItem layout="below" onClick={() => setPage("advanced")}>{t("Advanced settings")}</ButtonItem></PanelSectionRow>
				</>}
		{page === "updates" && <>
                    <PanelSection title={t("Updates")}>
                        <PanelSectionRow><div>{t("Version {version}", {version: updateInfo?.current || pluginVersion})}</div></PanelSectionRow>
                        <PanelSectionRow><div role="status">{updateError || (updateInfo?.success ?
                            updateInfo.update_available ? t("Update available: {version}", {version: updateInfo.version}) : t("Up to date") : t("Checking for updates..."))}</div></PanelSectionRow>
                        {updateInfo?.success && updateInfo.update_available && <>
                            <PanelSectionRow><div>{updateInfo.current} → {updateInfo.version}</div></PanelSectionRow>
                            <PanelSectionRow><div ref={updateActionRowRef}><ButtonItem layout="below" disabled={updateBusy} onClick={startUpdate}>
                                {updatePhase === "preparing" ? t("Preparing update...") : updatePhase === "waiting" ? t("Waiting for Decky confirmation...") : t("Update to {version}", {version: updateInfo.version})}
                            </ButtonItem></div></PanelSectionRow>
                        </>}
                        <PanelSectionRow><div ref={updateInfo?.update_available ? undefined : updateActionRowRef}><ButtonItem layout="below" disabled={checkingUpdate || updatePhase !== "idle"} onClick={() => { void checkUpdate(true); }}>{t("Check again")}</ButtonItem></div></PanelSectionRow>
                    </PanelSection>

                </>}
		{page === "advanced" && <>
					<PanelSection title={t("Interface")}>
						<PanelSectionRow><DropdownItem label={t("Interface language")} menuLabel={t("Interface language")}
							rgOptions={[{data:"auto",label:t("Automatic (system)")}, ...INTERFACE_LANGUAGE_OPTIONS]}
							selectedOption={interfaceLanguage} onChange={(option) => {
								const next = option.data as InterfacePreference;
								setInterfacePreference(next);
								updateInterfaceLanguage(next);
								refreshLocale(value => value + 1);
								void syncOverlayLanguage();
							}} /></PanelSectionRow>
					</PanelSection>
					<PanelSection title={t("Transcription model")}>
						<PanelSectionRow><div ref={advancedModelRowRef}><ButtonItem layout="below" onClick={() => setPage("model")}>
							{t("Model")}: {t(String(MODEL_SIZE_OPTIONS.find(option => option.data === modelSize)?.label || modelSize))}
						</ButtonItem></div></PanelSectionRow>
						{modelReady && !modelLoading && inferenceDevice && (
							<PanelSectionRow><div>
								{inferenceDevice === "gpu"
									? t("whisper.cpp runs on the GPU via Vulkan.")
									: t("whisper.cpp runs on the CPU.")}
							</div></PanelSectionRow>
						)}
						<PanelSectionRow><div style={{ fontSize: '12px' }}>{t("Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.")}</div></PanelSectionRow>
					</PanelSection>
					<PanelSection title={t("Sending")}>
						<PanelSectionRow><DropdownItem label={t("Transcription sending")} menuLabel={t("Transcription sending")} rgOptions={[{data:"immediate",label:t("Send immediately")},{data:"review",label:t("Review before sending")},{data:"countdown",label:t("Send after countdown")}]} selectedOption={sendingMode} onChange={async (option) => {
							const next = option.data as string;
							const result = await setSendingModeRpc(next);
							if (result.success) { setSendingMode(next); setRpcError(""); }
							else setRpcError(result.error || t("Could not update sending mode"));
						}} /></PanelSectionRow>
						{sendingMode === "review" && <PanelSectionRow><div style={{ fontSize: '13px', lineHeight: '1.5' }}>{t("Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.", {binding: buttons.join("+")})}</div></PanelSectionRow>}
						<PanelSectionRow><DropdownItem label={t("Text insertion")} menuLabel={t("Text insertion")}
							rgOptions={[{data:"paste",label:t("Paste")},{data:"ydotool",label:t("Type (only English keyboard)")}]}
							selectedOption={textInsertionMode} onChange={async (option) => {
								try {
									const next = String(option.data);
									const result = await setTextInsertionModeRpc(next);
									if (result.success) { setTextInsertionMode(next); setRpcError(""); }
									else setRpcError(result.error || t("Could not update text insertion mode"));
								} catch (error) { setRpcError(String(error)); }
							}} /></PanelSectionRow>
						{textInsertionMode === "ydotool" && <PanelSectionRow><div style={{ fontSize: '12px' }}>{t("Type requires an English (US) keyboard layout and ASCII text. Other text fails without sending.")}</div></PanelSectionRow>}
						<PanelSectionRow><ToggleField label={t("Press Enter yourself")} description={t("Type into chat without submitting")} checked={manualSend}
							onChange={async (next) => { setManualSend(next); await setManualSendRpc(next); }} /></PanelSectionRow>
						<PanelSectionRow><ToggleField label={t("Remember channel")} description={t("Reuse the last spoken channel")} checked={rememberLastChannel}
							onChange={async (next) => {
								setRememberLastChannel(next);
								const result = await setRememberLastChannelRpc(next);
								if (!result.success) { setRememberLastChannel(!next); setRpcError(result.error || t("Could not update channel setting")); }
							}} /></PanelSectionRow>
						<PanelSectionRow><ToggleField label={t("Spoken punctuation")} checked={spokenPunctuation}
							description={t("With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.")}
							onChange={async (next: boolean) => {
								try {
									const result = await setSpokenPunctuationRpc(next);
									if (result.success) { setSpokenPunctuation(next); setRpcError(""); }
									else setRpcError(result.error || t("Could not set spoken punctuation"));
								} catch (error) { setRpcError(String(error)); }
							}} /></PanelSectionRow>
					</PanelSection>
					<PanelSection title={t("Feedback")}>
						<PanelSectionRow><DropdownItem label={t("Recording cue")} menuLabel={t("Recording cue")} rgOptions={[{data:"toast",label:t("Toast")},{data:"overlay",label:t("Overlay")},{data:"none",label:t("None")}]} selectedOption={recordingIndicator} onChange={async (option) => { const mode = option.data as string; setRecordingIndicator(mode); logic.recordingIndicator = mode; const result = await setRecordingIndicatorRpc(mode); if (!result.success) setRpcError(result.error || t("Could not update recording cue")); }} /></PanelSectionRow>
						<PanelSectionRow><ToggleField label={t("Haptic feedback")} description={t("Cues on the controller when recording starts and stops")}
							checked={hapticFeedback} onChange={async (next) => {
								const result = await setHapticFeedbackRpc(next);
								if (result.success) setHapticFeedback(next);
								else setRpcError(result.error || t("Could not update haptic feedback"));
							}} /></PanelSectionRow>
					</PanelSection>
					<PanelSectionRow><ButtonItem layout="below" onClick={() => { setPage("updates"); void checkUpdate(true); }}>{t("Check for updates")}</ButtonItem></PanelSectionRow>
					<PanelSectionRow><ButtonItem layout="below" onClick={() => setPage("diagnostics")}>{t("Diagnostics")}</ButtonItem></PanelSectionRow>
					<PanelSectionRow><ButtonItem layout="below" onClick={() => setPage("help")}>{t("Help & permissions")}</ButtonItem></PanelSectionRow>
				</>}
				{page === "microphone-help" && <PanelSection title={t("Microphone troubleshooting")}>
					<PanelSectionRow><Focusable ref={microphoneHelpRef} tabIndex={0} aria-label={t("Microphone guide. Use Up and Down to scroll.")} style={{ maxHeight: '300px', overflowY: 'auto', overflowWrap: 'anywhere', fontSize: '15px', lineHeight: '1.5', padding: '8px' }} onGamepadDirection={(event) => {
						const direction = event.detail.button === GamepadButton.DIR_UP ? -1 : event.detail.button === GamepadButton.DIR_DOWN ? 1 : 0;
						if (direction && scrollMicrophoneHelp(direction)) { event.preventDefault(); event.stopPropagation(); }
					}} onKeyDown={(event) => {
						const direction = event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0;
						if (direction && scrollMicrophoneHelp(direction)) { event.preventDefault(); event.stopPropagation(); }
					}}>
						<p><strong>{t("Start with a dictation test")}</strong></p>
						<p>{t("Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.")}</p>
						<p>{t("Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.")}</p>
						<p><strong>{t("If audio crackles, pops, or cuts out")}</strong></p>
						<p>{t("A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.")}</p>
						<ol style={{ paddingLeft: '24px' }}>
							<li>{t("Open Steam → Power → Switch to Desktop.")}</li>
							<li>{t("In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.")}</li>
							<li>{t("Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.")}</li>
							<li>{t("Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.")}</li>
							<li>{t("Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.")}</li>
							<li>{t("Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.")}</li>
						</ol>
						<p>{t("Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.")}</p>
						<p><strong>{t("If the problem persists")}</strong></p>
						<p>{t("Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.")}</p>
					</Focusable></PanelSectionRow>
					<PanelSectionRow><ButtonItem layout="below" onClick={() => Router.NavigateToExternalWeb("https://github.com/silverfoxy/decktation/blob/master/doc/TROUBLESHOOTING.md#microphone-crackles-pops-or-cuts-out")}>{t("Open full guide online")}</ButtonItem></PanelSectionRow>
				</PanelSection>}
				{page === "diagnostics" && <>
					<PanelSection title={t("Microphone help")}>
						<PanelSectionRow><div>{t("Voice not recognized, missing words, or crackling audio? Read the microphone guide here.")}</div></PanelSectionRow>
						<PanelSectionRow><ButtonItem layout="below" onClick={() => setPage("microphone-help")}>{t("Having problems with your microphone?")}</ButtonItem></PanelSectionRow>
					</PanelSection>
					<PanelSection title={t("Input and service")}>
						<PanelSectionRow><div>{t("Controller")}: {t(controllerStatus)}</div></PanelSectionRow>
						<PanelSectionRow><div>{t("Binding supported")}: {controllerComboSupported ? t("Yes") : t("No")}</div></PanelSectionRow>
						<PanelSectionRow><div>{t("Held buttons")}: <strong>{t(buttonState)}</strong></div></PanelSectionRow>
						<PanelSectionRow><div>{t("Keyboard helper")}: {inputReady ? t("Ready") : t("Unavailable")}</div></PanelSectionRow>
						<PanelSectionRow><div>{t("Backend")}: {serviceReady ? t("Ready") : t("Unavailable")}</div></PanelSectionRow>
						<PanelSectionRow><div>{t("Model")}: {modelLoading ? t("Loading") : modelReady ? t("Ready") : t("Unavailable")}</div></PanelSectionRow>
						{pendingDraft && <PanelSectionRow><div>{t("Review confirmation")}: {t(reviewBlockReason || "Ready")}</div></PanelSectionRow>}
						{(statusError || rpcError) && <PanelSectionRow><div role="alert">{statusError || rpcError}</div></PanelSectionRow>}
					</PanelSection>
					<PanelSection title={t("Controller input debugger")}>
						<PanelSectionRow><div>{t("Record up to 30 seconds of controller input.")}</div></PanelSectionRow>
						<PanelSectionRow><div>{t("Press each paddle, then A. Do not type.")}</div></PanelSectionRow>
                        <PanelSectionRow><div role="status" aria-live="polite">
                            {controllerSnapshot.state === "starting" && <div>{t("Waiting for controller listener...")}</div>}
                            {controllerSnapshot.state === "recording" && <div>{t("Recording controller input")} · {controllerSeconds} {t("seconds remaining")}</div>}
                            {controllerSnapshot.state === "stopping" && <div>{t("Finalizing controller report...")}</div>}
                            {controllerSnapshot.state === "ready" && <div>{t("Controller report ready for review")}</div>}
                            <div>{t("Events captured")}: {controllerSnapshot.event_count} · {t("Controller interfaces")}: {controllerSnapshot.device_count}</div>
                            {controllerSnapshot.session && <div>{t("Capture continues if you close this panel.")}</div>}
                        </div></PanelSectionRow>
                        <PanelSectionRow><ButtonItem key="controller-debug-start" layout="below" onClick={() =>
                            controllerDebug.error ? controllerClient.refresh() : controllerClient.start()
                        }>{controllerButtonLabel}</ButtonItem></PanelSectionRow>
                        <PanelSectionRow><div style={{fontSize: "12px"}}>{t("Includes host/build details, controller interfaces and button transitions. Excludes typing, audio, transcripts, serials and input paths.")}</div></PanelSectionRow>
                        <PanelSectionRow><div>{t("Nothing is sent automatically. Send shares only this report with Sentry.")}</div></PanelSectionRow>
                        {controllerSnapshot.session && <PanelSectionRow><div>
                            <div>{t("Host metadata available")}: {Object.keys(controllerSnapshot.metadata).length}/16. {t("Unavailable values are omitted.")}</div>
                        </div></PanelSectionRow>}
                        {controllerReport && controllerSnapshot.state === "ready" && <PanelSectionRow><ButtonItem layout="below"
                            onClick={() => setDismissedReportSession(null)}>{t("Controller report ready for review")}</ButtonItem></PanelSectionRow>}
                        {controllerDebugError && <PanelSectionRow><div role="alert">{t(controllerDebugError)}</div></PanelSectionRow>}
					</PanelSection>
					<PanelSection title={t("Diagnostics sharing")}>
						<PanelSectionRow><ToggleField label={t("Share")} description={t("Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.")}
							checked={shareDiagnostics} onChange={async (next) => {
								setShareDiagnostics(next);
								const result = await setShareDiagnosticsRpc(next);
								if (!result.success) { setShareDiagnostics(!next); setRpcError(result.error || t("Could not update diagnostics setting")); }
							}} /></PanelSectionRow>
					</PanelSection>
				</>}
				{page === "game" && <PanelSection title={t("Mode")}>
					{rpcError && <PanelSectionRow><div role="alert">{rpcError}</div></PanelSectionRow>}
					{presets.map(option => <PanelSectionRow key={String(option.data)}><ButtonItem layout="below" onClick={async () => {
						const next = option.data as string;
						setRpcError("");
						const result = await setActivePresetRpc(next);
						if (result.success) { setActivePreset(next); setPage("main"); }
						else setRpcError(result.error || t("Could not update game"));
					}}>{option.data === activePreset ? "✓ " : ""}{t(String(option.label))}</ButtonItem></PanelSectionRow>)}
				</PanelSection>}
				{page === "model" && <PanelSection title={t("Model")}>
					{rpcError && <PanelSectionRow><div role="alert">{rpcError}</div></PanelSectionRow>}
					{modelLoading && <PanelSectionRow><div role="status" aria-live="polite">{modelStage === "downloading" ? t("Downloading transcription model...") : t("Loading transcription model...")}</div></PanelSectionRow>}
					{MODEL_SIZE_OPTIONS.map(option => <PanelSectionRow key={String(option.data)}><ButtonItem layout="below" disabled={modelLoading || modelChangeInFlight.current} onClick={async () => {
						if (modelLoading || modelChangeInFlight.current) return;
						modelChangeInFlight.current = true;
						const next = option.data as string;
						setRpcError("");
						if (enabled && modelReady) setModelLoading(true);
						try {
							const result = await setModelSizeRpc(next);
							if (result.success) { setModelSize(next); if (pageRef.current === "model") setPage("advanced"); }
							else setRpcError(result.error || t("Could not update model size"));
						} catch (error) { setRpcError(String(error)); }
						finally { modelChangeInFlight.current = false; setModelLoading(false); }
					}}>{option.data === modelSize ? "✓ " : ""}{t(String(option.label))}</ButtonItem></PanelSectionRow>)}
				</PanelSection>}

				{page === "help" && <>
					<PanelSection title={t("How to use")}>
						<PanelSectionRow><div style={{ fontSize: '13px', lineHeight: '1.6' }}>
							{t("Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.", {binding: buttons.join("+"), together: buttons.length > 1 ? t("together ") : ""})}
						</div></PanelSectionRow>
						<PanelSectionRow><div style={{ fontSize: '13px', lineHeight: '1.6' }}>
							{t("Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.")}
						</div></PanelSectionRow>
					</PanelSection>
					<PanelSection title={t("Permissions")}>
						<PanelSectionRow><div style={{ fontSize: '13px', lineHeight: '1.5' }}>
							{t("Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.")}
						</div></PanelSectionRow>
					</PanelSection>
				</>}
			</div>
		</Focusable>
	);
};


const DecktationIcon: VFC<{ logic: DecktationLogic }> = ({ logic }) => {
    const [available, setAvailable] = useState(logic.updateAvailable);
    useEffect(() => {
        logic.updateListeners.add(setAvailable);
        setAvailable(logic.updateAvailable);
        return () => { logic.updateListeners.delete(setAvailable); };
    }, [logic]);
    return <span style={{ position: "relative", display: "inline-flex" }} aria-label={available ? t("Decktation update available") : "Decktation"}>
        <FaMicrophone />
        {available && <span aria-hidden="true" style={{ position: "absolute", right: "-3px", top: "-3px", width: "7px", height: "7px", borderRadius: "50%", background: "#7cdb98" }} />}
    </span>;
};

export default definePlugin(() => {
	let logic = new DecktationLogic();
    let disposed = false;
    // One cached discovery check per plugin lifecycle, even before opening its panel.
    void getPluginUpdate(false).then(result => {
        if (!disposed) logic.setUpdateAvailable(result.success && result.update_available === true);
    }).catch(() => {});
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
				if (!sent.success) void logic.notify(t("Review transcription"), 5000, sent.error || t("Open Decktation to retry"));
			}
			const result = await getStatus();
			if (result.success) {
				const startCount: number = result.recording_start_count || 0;
				if (logic.recordingIndicator === "toast" && startCount > logic.prevRecordingStartCount) {
					logic.notify(t("Recording"), 1500, "🎤 " + t("Recording..."));
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
					logic.lastPendingToastId = await logic.notify(t("Review transcription"), 6000,
						t("“{text}” — open Decktation to review, send or cancel", {text: draft.text}));
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
		icon: <DecktationIcon logic={logic} />,
		onDismount() {
            disposed = true;
            logic.updateListeners.clear();
			clearInterval(bgNotifyInterval);
			if (logic.recording) {
				void stopRecording();
			}
		},
		alwaysRender: true
	};
});
