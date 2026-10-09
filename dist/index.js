(function (deckyFrontendLib, React) {
    'use strict';

    function _interopDefaultLegacy (e) { return e && typeof e === 'object' && 'default' in e ? e : { 'default': e }; }

    var React__default = /*#__PURE__*/_interopDefaultLegacy(React);

    // Read the actual QAM surface. Document visibility alone does not establish
    // whether a persistent Steam sidebar is on screen.
    function quickAccessVisibility(documents, classNames) {
        let foundMenu = false;
        for (const doc of documents) {
            // Prefer the sidebar itself over its full-screen transparent container.
            for (const name of classNames) {
                if (!name)
                    continue;
                const menus = Array.from(doc.getElementsByClassName(name));
                if (!menus.length)
                    continue;
                foundMenu = true;
                if (doc.hidden)
                    break;
                const view = doc.defaultView;
                if (!view)
                    break;
                for (const menu of menus) {
                    if (!menu.isConnected)
                        continue;
                    const rect = menu.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0 || rect.right <= 0 || rect.bottom <= 0 || rect.left >= view.innerWidth || rect.top >= view.innerHeight)
                        continue;
                    let visible = true;
                    for (let node = menu; node; node = node.parentElement) {
                        const style = view.getComputedStyle(node);
                        if (style.display === "none" || style.visibility === "hidden" || style.visibility === "collapse" || Number(style.opacity) === 0) {
                            visible = false;
                            break;
                        }
                    }
                    if (visible)
                        return true;
                }
                break;
            }
        }
        // Missing markup is unknown, rather than an assertion that QAM is open.
        return foundMenu ? false : null;
    }

    var _manifest = {"name":"Decktation","version":"0.3.18","author":"silverfoxy","flags":["root"],"api_version":1,"publish":{"tags":["voice","dictation","speech-to-text","input","chat","gaming","accessibility"],"description":"Push-to-talk dictation for Steam Deck. Context-aware speech-to-text using whisper.cpp.","image":"https://raw.githubusercontent.com/silverfoxy/decktation/master/store-card.png"}};

    const manifest = _manifest;
    const API_VERSION = 2;
    if (!manifest?.name) {
        throw new Error('[@decky/api]: Failed to find plugin manifest.');
    }
    const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
    if (!internalAPIConnection) {
        throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
    }
    let api;
    try {
        api = internalAPIConnection.connect(API_VERSION, manifest.name);
    }
    catch {
        api = internalAPIConnection.connect(1, manifest.name);
        console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
    }
    if (api._version != API_VERSION) {
        console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
    }
    api.call;
    const callable = api.callable;
    api.addEventListener;
    api.removeEventListener;
    api.routerHook;
    const toaster = api.toaster;
    api.openFilePicker;
    api.executeInTab;
    api.injectCssIntoTab;
    api.removeCssFromTab;
    api.fetchNoCors;
    api.getExternalResourceURL;
    api.useQuickAccessVisible;

    var DefaultContext = {
      color: undefined,
      size: undefined,
      className: undefined,
      style: undefined,
      attr: undefined
    };
    var IconContext = React__default["default"].createContext && React__default["default"].createContext(DefaultContext);

    var __assign = window && window.__assign || function () {
      __assign = Object.assign || function (t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
          s = arguments[i];
          for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
        }
        return t;
      };
      return __assign.apply(this, arguments);
    };
    var __rest = window && window.__rest || function (s, e) {
      var t = {};
      for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0) t[p] = s[p];
      if (s != null && typeof Object.getOwnPropertySymbols === "function") for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
        if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i])) t[p[i]] = s[p[i]];
      }
      return t;
    };
    function Tree2Element(tree) {
      return tree && tree.map(function (node, i) {
        return React__default["default"].createElement(node.tag, __assign({
          key: i
        }, node.attr), Tree2Element(node.child));
      });
    }
    function GenIcon(data) {
      // eslint-disable-next-line react/display-name
      return function (props) {
        return React__default["default"].createElement(IconBase, __assign({
          attr: __assign({}, data.attr)
        }, props), Tree2Element(data.child));
      };
    }
    function IconBase(props) {
      var elem = function (conf) {
        var attr = props.attr,
          size = props.size,
          title = props.title,
          svgProps = __rest(props, ["attr", "size", "title"]);
        var computedSize = size || conf.size || "1em";
        var className;
        if (conf.className) className = conf.className;
        if (props.className) className = (className ? className + " " : "") + props.className;
        return React__default["default"].createElement("svg", __assign({
          stroke: "currentColor",
          fill: "currentColor",
          strokeWidth: "0"
        }, conf.attr, attr, svgProps, {
          className: className,
          style: __assign(__assign({
            color: props.color || conf.color
          }, conf.style), props.style),
          height: computedSize,
          width: computedSize,
          xmlns: "http://www.w3.org/2000/svg"
        }), title && React__default["default"].createElement("title", null, title), props.children);
      };
      return IconContext !== undefined ? React__default["default"].createElement(IconContext.Consumer, null, function (conf) {
        return elem(conf);
      }) : elem(DefaultContext);
    }

    // THIS FILE IS AUTO GENERATED
    function FaMicrophone (props) {
      return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 352 512"},"child":[{"tag":"path","attr":{"d":"M176 352c53.02 0 96-42.98 96-96V96c0-53.02-42.98-96-96-96S80 42.98 80 96v160c0 53.02 42.98 96 96 96zm160-160h-16c-8.84 0-16 7.16-16 16v48c0 74.8-64.49 134.82-140.79 127.38C96.71 376.89 48 317.11 48 250.3V208c0-8.84-7.16-16-16-16H16c-8.84 0-16 7.16-16 16v40.16c0 89.64 63.97 169.55 152 181.69V464H96c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16h-56v-33.77C285.71 418.47 352 344.9 352 256v-48c0-8.84-7.16-16-16-16z"}}]})(props);
    }

    const getStatus = callable("get_status");
    const startBindingCapture = callable("start_binding_capture");
    const getBindingCapture = callable("get_binding_capture");
    const cancelBindingCapture = callable("cancel_binding_capture");
    const setRecordingModeRpc = callable("set_recording_mode");
    const getButtonConfig = callable("get_button_config");
    const getPresets = callable("get_presets");
    const setEnabledRpc = callable("set_enabled");
    const loadModel = callable("load_model");
    const startRecording = callable("start_recording");
    const stopRecording = callable("stop_recording");
    const getLastTranscription = callable("get_last_transcription");
    const setSendingModeRpc = callable("set_sending_mode");
    const cancelDraftRpc = callable("cancel_draft");
    const armDraftRpc = callable("arm_draft");
    const setReviewContextRpc = callable("set_review_context");
    const sendArmedDraftRpc = callable("send_armed_draft");
    const setManualSendRpc = callable("set_manual_send");
    const setRememberLastChannelRpc = callable("set_remember_last_channel");
    const setShareDiagnosticsRpc = callable("set_share_diagnostics");
    const setRecordingIndicatorRpc = callable("set_recording_indicator");
    const setHapticFeedbackRpc = callable("set_haptic_feedback");
    const setActivePresetRpc = callable("set_active_preset");
    const setModelSizeRpc = callable("set_model_size");
    const setTranscriptionOptionsRpc = callable("set_transcription_options");
    callable("set_button_config");
    class DecktationLogic {
        constructor() {
            this.enabled = false;
            this.recording = false;
            this.recordingIndicator = "toast";
            this.prevRecordingStartCount = 0;
            this.prevPendingId = "";
            this.pendingSince = 0;
            this.announcedDraftId = "";
            this.qamVisible = false;
            this.qamKnown = false;
            this.readQamVisibility = null;
            this.qamClosedAt = Date.now();
            this.armedDraftId = "";
            this.lastPendingToastId = -1;
            this.notify = async (message, duration = 2000, body = "") => {
                if (!body) {
                    body = message;
                }
                const toast = {
                    title: message,
                    body: body,
                    duration: duration,
                    critical: false,
                };
                const id = window.NotificationStore ? window.NotificationStore.m_nNextTestNotificationID++ : 0;
                const toastData = {
                    nNotificationID: id,
                    bNewIndicator: false,
                    rtCreated: Date.now(),
                    eType: 43,
                    eSource: 1,
                    nToastDurationMS: duration,
                    data: toast,
                    decky: true,
                };
                const info = {
                    showToast: true,
                    sound: 6,
                    playSound: false,
                    eFeature: 0,
                    toastDurationMS: duration,
                    bCritical: false,
                    fnTray: (_t, tray) => { tray.unshift({ eType: 31, notifications: [toastData] }); },
                };
                try {
                    window.NotificationStore.ProcessNotification(info, toastData, 0);
                }
                catch (_e) {
                    // fallback to standard toaster if direct call fails
                    toaster.toast({ title: message, body: toast.body, duration: duration, critical: false });
                }
                return id;
            };
            this.dismissNotification = (id) => {
                // Force-expire the toast by reprocessing it with a 1ms duration
                try {
                    const toastData = {
                        nNotificationID: id,
                        bNewIndicator: false,
                        rtCreated: Date.now(),
                        eType: 43,
                        eSource: 1,
                        nToastDurationMS: 1,
                        data: { title: "", body: "", duration: 1, critical: false },
                        decky: true,
                    };
                    const info = {
                        showToast: true,
                        sound: 6,
                        playSound: false,
                        eFeature: 0,
                        toastDurationMS: 1,
                        bCritical: false,
                        fnTray: (_t, tray) => { tray.unshift({ eType: 31, notifications: [toastData] }); },
                    };
                    window.NotificationStore.ProcessNotification(info, toastData, 0);
                }
                catch (_e) { }
            };
            this.testRecording = async (onComplete, onPhase) => {
                onPhase("recording");
                try {
                    if (this.recordingIndicator === "toast")
                        this.notify("Decktation", 1000, "Recording for 3 seconds...");
                    const started = await startRecording();
                    if (!started.success)
                        throw new Error(started.error || "Could not start test recording");
                    await new Promise(resolve => setTimeout(resolve, 3000));
                    // Keep the no-send argument: test text must never reach the active game.
                    onPhase("transcribing");
                    const transcription = stopRecording(false);
                    if (this.recordingIndicator === "toast")
                        this.notify("Decktation", 1500, "Transcribing...");
                    const stopped = await transcription;
                    if (!stopped.success)
                        throw new Error(stopped.error || "Could not transcribe test recording");
                    const result = await getLastTranscription();
                    if (!result.success)
                        throw new Error(result.error || "Could not read test transcription");
                    const data = result.transcription;
                    onComplete(data?.text || "", data?.timestamp ? new Date(data.timestamp * 1000).toLocaleTimeString() : "");
                }
                finally {
                    onPhase("idle");
                }
            };
        }
    }
    const WHISPER_LANGUAGE_OPTIONS = [
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
    const MODEL_SIZE_OPTIONS = [
        { data: "base", label: "Base · Fast" },
        { data: "small", label: "Small · Balanced" },
        { data: "medium", label: "Medium · More accurate" },
    ];
    const POPULAR_STEAM_LANGUAGE_CODES = new Set(["en", "zh", "ru", "es", "pt", "de", "ja", "fr", "pl", "ko"]);
    const byLanguageName = (left, right) => String(left.label).localeCompare(String(right.label));
    const POPULAR_LANGUAGE_OPTIONS = WHISPER_LANGUAGE_OPTIONS.filter(option => POPULAR_STEAM_LANGUAGE_CODES.has(String(option.data))).sort(byLanguageName);
    const OTHER_LANGUAGE_OPTIONS = WHISPER_LANGUAGE_OPTIONS.filter(option => option.data !== "auto" && !POPULAR_STEAM_LANGUAGE_CODES.has(String(option.data))).sort(byLanguageName);
    const PRESET_DISPLAY_NAMES = {
        wow: "World of Warcraft",
        guildwars2: "Guild Wars 2",
        generic: "Generic",
    };
    const DecktationPanel = ({ logic }) => {
        const [page, setPage] = React.useState("main");
        const panelRef = React.useRef(null);
        const languageMenuAnchorRef = React.useRef(null);
        const advancedModelRowRef = React.useRef(null);
        const [capture, setCapture] = React.useState(null);
        const captureRef = React.useRef(null);
        const captureFocusRef = React.useRef(null);
        const [bindingMessage, setBindingMessage] = React.useState("");
        const [enabled, setEnabled] = React.useState(false);
        const [recording, setRecording] = React.useState(false);
        const [serviceReady, setServiceReady] = React.useState(false);
        const [modelReady, setModelReady] = React.useState(false);
        const [inferenceDevice, setInferenceDevice] = React.useState(null);
        const [modelLoading, setModelLoading] = React.useState(false);
        const [isToggling, setIsToggling] = React.useState(false);
        const [inputReady, setInputReady] = React.useState(true);
        const [buttonState, setButtonState] = React.useState("None");
        const [controllerReady, setControllerReady] = React.useState(false);
        const [recordingMode, setRecordingMode] = React.useState("hold");
        const [controllerStatus, setControllerStatus] = React.useState("Waiting for input");
        const [controllerComboSupported, setControllerComboSupported] = React.useState(true);
        const [buttons, setButtons] = React.useState(["L1", "R1"]);
        const [recordingIndicator, setRecordingIndicator] = React.useState("toast");
        const [hapticFeedback, setHapticFeedback] = React.useState(false);
        const [activePreset, setActivePreset] = React.useState("wow");
        const [presets, setPresets] = React.useState([]);
        const [sendingMode, setSendingMode] = React.useState("immediate");
        const [pendingDraft, setPendingDraft] = React.useState(null);
        const reviewTextRef = React.useRef(null);
        const [draftBusy, setDraftBusy] = React.useState(false);
        const [qamVisible, setQamVisible] = React.useState(false);
        React.useEffect(() => {
            const read = () => {
                const documents = [];
                if (panelRef.current)
                    documents.push(panelRef.current.ownerDocument);
                try {
                    for (const tree of deckyFrontendLib.getGamepadNavigationTrees() || []) {
                        if (!String(tree?.id || "").startsWith("QuickAccess"))
                            continue;
                        const doc = tree?.m_Root?.m_element?.ownerDocument;
                        if (doc && !documents.includes(doc))
                            documents.push(doc);
                    }
                }
                catch (_error) { /* Inspect the mounted panel's document instead. */ }
                return quickAccessVisibility(documents, [deckyFrontendLib.quickAccessMenuClasses.QuickAccessMenu, deckyFrontendLib.quickAccessMenuClasses.Menu]);
            };
            const update = () => {
                const visible = read();
                if (visible === false && logic.qamVisible)
                    logic.qamClosedAt = Date.now();
                const changed = logic.qamKnown !== (visible !== null) || logic.qamVisible !== (visible === true);
                logic.qamKnown = visible !== null;
                logic.qamVisible = visible === true;
                setQamVisible(visible === true);
                if (changed)
                    void setReviewContextRpc(logic.qamVisible, logic.qamKnown).catch(() => { });
            };
            logic.readQamVisibility = read;
            update();
            const interval = setInterval(update, 200);
            return () => { clearInterval(interval); logic.readQamVisibility = null; logic.qamKnown = false; };
        }, []);
        const [manualSend, setManualSend] = React.useState(false);
        const [rememberLastChannel, setRememberLastChannel] = React.useState(false);
        const [shareDiagnostics, setShareDiagnostics] = React.useState(false);
        const [modelSize, setModelSize] = React.useState("base");
        const [transcriptionLanguage, setTranscriptionLanguage] = React.useState("auto");
        const [lastTranscription, setLastTranscription] = React.useState("");
        const [lastTranscriptionTime, setLastTranscriptionTime] = React.useState("");
        const [rpcError, setRpcError] = React.useState("");
        const [reviewBlockReason, setReviewBlockReason] = React.useState("");
        const [statusError, setStatusError] = React.useState("");
        const [testPhase, setTestPhase] = React.useState("idle");
        const [hasTestResult, setHasTestResult] = React.useState(false);
        React.useEffect(() => {
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
                    const opts = result.presets.map((p) => ({
                        data: p.id,
                        label: PRESET_DISPLAY_NAMES[p.id] || p.name,
                    }));
                    setPresets(opts);
                }
            }).catch((error) => setRpcError(String(error)));
        }, []);
        React.useEffect(() => {
            let cancelled = false;
            let timeout;
            const poll = async () => {
                try {
                    const result = await getStatus();
                    if (cancelled)
                        return;
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
                        setInferenceDevice(result.inference_device === "gpu" || result.inference_device === "cpu"
                            ? result.inference_device
                            : null);
                        setModelLoading(result.model_loading);
                        setInputReady(result.input_ready !== false);
                        if (logic.enabled) {
                            setRecording(result.recording);
                        }
                    }
                    else {
                        setControllerReady(false);
                        setControllerStatus("Status unavailable");
                        setStatusError(result.error || "Backend status request failed");
                    }
                }
                catch (error) {
                    setControllerReady(false);
                    setControllerStatus("Status unavailable");
                    setStatusError(String(error));
                }
                finally {
                    if (!cancelled)
                        timeout = setTimeout(poll, 100);
                }
            };
            void poll();
            return () => {
                cancelled = true;
                if (timeout)
                    clearTimeout(timeout);
            };
        }, [logic.enabled]);
        React.useEffect(() => {
            // Steam's QAM keeps its scroll position when the content changes in place.
            const resetScroll = () => {
                let node = panelRef.current?.parentElement;
                while (node) {
                    if (node.scrollHeight > node.clientHeight)
                        node.scrollTop = 0;
                    node = node.parentElement;
                }
            };
            resetScroll();
            const frame = requestAnimationFrame(() => {
                resetScroll();
                if (page === "advanced") {
                    advancedModelRowRef.current?.querySelector('[role="button"], button')?.focus();
                }
            });
            return () => cancelAnimationFrame(frame);
        }, [page]);
        React.useEffect(() => {
            if (!capture)
                return;
            let disposed = false;
            let timer;
            const pollCapture = async () => {
                try {
                    const result = await getBindingCapture(capture.session);
                    if (disposed)
                        return;
                    if (!result.success || result.phase === "cancelled" || result.phase === "saved") {
                        if (result.phase === "saved") {
                            setButtons(result.buttons);
                            setBindingMessage(`Binding saved: ${result.buttons.join(" + ")}`);
                        }
                        else
                            setRpcError(result.error || "Binding cancelled. Your previous binding is unchanged.");
                        captureRef.current = null;
                        setCapture(null);
                        return;
                    }
                    setCapture({ session: capture.session, phase: result.phase, buttons: result.buttons || [] });
                }
                catch (error) {
                    if (!disposed) {
                        setRpcError(String(error));
                        void cancelCapture();
                    }
                    return;
                }
                if (!disposed)
                    timer = setTimeout(pollCapture, 80);
            };
            captureFocusRef.current?.focus();
            void pollCapture();
            return () => { disposed = true; clearTimeout(timer); };
        }, [capture?.session]);
        React.useEffect(() => () => {
            if (captureRef.current)
                void cancelBindingCapture(captureRef.current);
        }, []);
        const beginCapture = async () => {
            setRpcError("");
            setBindingMessage("");
            try {
                const result = await startBindingCapture();
                if (!result.success) {
                    setRpcError(result.error || "Could not start binding capture");
                    return;
                }
                captureRef.current = result.session;
                setCapture({ session: result.session, phase: "release", buttons: [] });
            }
            catch (error) {
                setRpcError(String(error));
            }
        };
        const cancelCapture = async () => {
            const session = captureRef.current;
            captureRef.current = null;
            setCapture(null);
            if (session)
                await cancelBindingCapture(session);
        };
        const scrollReview = (direction) => {
            const node = reviewTextRef.current;
            if (!node || (direction < 0 ? node.scrollTop <= 0 : node.scrollTop + node.clientHeight >= node.scrollHeight - 1))
                return false;
            node.scrollTop += direction * 96;
            return true;
        };
        const goBack = () => setPage(page === "diagnostics" || page === "help" || page === "model" ? "advanced" : "main");
        const chooseLanguage = async (language) => {
            const result = await setTranscriptionOptionsRpc(language);
            if (result.success) {
                setTranscriptionLanguage(language);
                setRpcError("");
            }
            else {
                setRpcError(result.error || "Could not update language setting");
            }
        };
        const runTest = async () => {
            if (testPhase !== "idle")
                return;
            setRpcError("");
            setHasTestResult(false);
            try {
                await logic.testRecording((text, time) => {
                    setLastTranscription(text);
                    setLastTranscriptionTime(time);
                    setHasTestResult(true);
                }, setTestPhase);
            }
            catch (error) {
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
            const swallow = (event) => { event.preventDefault(); event.stopPropagation(); };
            return React__default["default"].createElement(deckyFrontendLib.Focusable, { ref: captureFocusRef, tabIndex: 0, onButtonDown: swallow, onButtonUp: swallow, onOKButton: swallow, onCancelButton: swallow, onGamepadDirection: swallow, onActivate: swallow, onCancel: swallow },
                React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Recording binding" },
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { role: "status" }, capture.phase === "release"
                            ? "Release all buttons to start listening."
                            : "Hold your new combination together. Release to save.")),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", null,
                            "Detected: ",
                            React__default["default"].createElement("strong", null, capture.buttons.join(" + ") || "Listening…"))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { style: { fontSize: "12px", opacity: 0.85 } }, "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.")),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("button", { tabIndex: -1, onClick: () => { void cancelCapture(); }, style: { padding: "10px 20px", color: "white", background: "#3b4252", border: 0, borderRadius: "4px" } }, "Cancel (touch)"))));
        }
        return (React__default["default"].createElement(deckyFrontendLib.Focusable, { onCancel: page === "main" ? undefined : (event) => {
                event.stopPropagation();
                goBack();
            }, onCancelActionDescription: page === "main" ? undefined : "Back" },
            React__default["default"].createElement("div", { ref: panelRef },
                React__default["default"].createElement("style", null, `.decktation-trash-focused { outline: 3px solid #66c0f4 !important; outline-offset: 2px; background-color: #456b90 !important; box-shadow: 0 0 0 2px rgba(102, 192, 244, 0.38) !important; }`),
                pendingDraft && React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Review transcription" },
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.Focusable, { ref: reviewTextRef, tabIndex: 0, "aria-label": "Transcription. Use Up and Down to scroll.", style: { fontSize: '16px', lineHeight: '1.5', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: '260px', overflowY: 'auto', padding: '4px' }, onGamepadDirection: (event) => {
                                const direction = event.detail.button === deckyFrontendLib.GamepadButton.DIR_UP ? -1 : event.detail.button === deckyFrontendLib.GamepadButton.DIR_DOWN ? 1 : 0;
                                if (direction && scrollReview(direction)) {
                                    event.preventDefault();
                                    event.stopPropagation();
                                }
                            }, onKeyDown: (event) => {
                                const direction = event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0;
                                if (direction && scrollReview(direction)) {
                                    event.preventDefault();
                                    event.stopPropagation();
                                }
                            } }, pendingDraft.text)),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { style: { fontSize: '13px', color: '#adb8c4' } },
                            pendingDraft.destination,
                            pendingDraft.manual ? " · After typing, press Enter in the game" : "")),
                    pendingDraft.error && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { role: "alert" }, pendingDraft.error)),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", disabled: draftBusy || pendingDraft.sending, onClick: async () => {
                                setDraftBusy(true);
                                try {
                                    await setReviewContextRpc(true, true);
                                    const result = await armDraftRpc(pendingDraft.id);
                                    if (result.success) {
                                        logic.armedDraftId = pendingDraft.id;
                                        deckyFrontendLib.Router.CloseSideMenus();
                                    }
                                    else
                                        setRpcError(result.error || "Could not approve draft");
                                }
                                catch (error) {
                                    setRpcError(String(error));
                                }
                                finally {
                                    setDraftBusy(false);
                                }
                            } }, pendingDraft.action)),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { style: { fontSize: '12px' } }, "Closes this menu before typing into your game. Keep your game in the foreground.")),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", disabled: draftBusy || pendingDraft.sending, onClick: async () => {
                                setDraftBusy(true);
                                try {
                                    const result = await cancelDraftRpc(pendingDraft.id);
                                    if (result.success)
                                        setPendingDraft(null);
                                    else
                                        setRpcError(result.error || "Could not cancel draft");
                                }
                                catch (error) {
                                    setRpcError(String(error));
                                }
                                finally {
                                    setDraftBusy(false);
                                }
                            } }, "Cancel"))),
                page !== "main" && (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                    React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: goBack }, "Back"))),
                page === "main" && React__default["default"].createElement(React__default["default"].Fragment, null,
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Decktation" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Enable", checked: enabled, disabled: !serviceReady || modelLoading || isToggling, onChange: async (next) => {
                                    if (isToggling)
                                        return;
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
                                    }
                                    catch (error) {
                                        setEnabled(!next);
                                        logic.enabled = !next;
                                        setRpcError(String(error));
                                    }
                                    finally {
                                        setIsToggling(false);
                                    }
                                } })),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { role: "status", style: { padding: statusProblem ? '10px' : '4px 0', borderRadius: '6px', backgroundColor: statusProblem ? '#713030' : undefined } }, statusMessage))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Quick settings" },
                        presets.length > 0 && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("game") },
                                "Game: ",
                                presets.find(option => option.data === activePreset)?.label || activePreset)),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { position: 'relative', width: '100%' } },
                                React__default["default"].createElement("span", { ref: languageMenuAnchorRef, "aria-hidden": "true", style: { position: 'absolute', left: 0, top: 0, width: '1px', height: '1px', pointerEvents: 'none' } }),
                                React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: (event) => {
                                        deckyFrontendLib.showContextMenu(React__default["default"].createElement(deckyFrontendLib.Menu, { label: "Language" },
                                            React__default["default"].createElement(deckyFrontendLib.MenuItem, { selected: transcriptionLanguage === "auto", onSelected: () => { void chooseLanguage("auto"); } }, "Auto Detect"),
                                            React__default["default"].createElement("div", { className: deckyFrontendLib.gamepadContextMenuClasses.ContextMenuSeparator }),
                                            React__default["default"].createElement("div", { className: deckyFrontendLib.gamepadContextMenuClasses.MenuSectionHeader }, "Popular Steam languages"),
                                            POPULAR_LANGUAGE_OPTIONS.map(option => React__default["default"].createElement(deckyFrontendLib.MenuItem, { key: String(option.data), selected: option.data === transcriptionLanguage, onSelected: () => { void chooseLanguage(String(option.data)); } }, option.label)),
                                            React__default["default"].createElement("div", { className: deckyFrontendLib.gamepadContextMenuClasses.ContextMenuSeparator }),
                                            React__default["default"].createElement("div", { className: deckyFrontendLib.gamepadContextMenuClasses.MenuSectionHeader }, "Other languages"),
                                            OTHER_LANGUAGE_OPTIONS.map(option => React__default["default"].createElement(deckyFrontendLib.MenuItem, { key: String(option.data), selected: option.data === transcriptionLanguage, onSelected: () => { void chooseLanguage(String(option.data)); } }, option.label))), languageMenuAnchorRef.current || event.currentTarget);
                                    } },
                                    "Language: ",
                                    WHISPER_LANGUAGE_OPTIONS.find(option => option.data === transcriptionLanguage)?.label || transcriptionLanguage)))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Recording binding" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", disabled: recording || testPhase !== "idle", onClick: () => setPage("recording-mode") },
                                "Mode: ",
                                recordingMode === "hold" ? "Hold to record" : "Tap to start/stop")),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                recordingMode === "hold" ? "Hold " : "Tap ",
                                React__default["default"].createElement("strong", null, buttons.join(" + ")),
                                recordingMode === "hold" ? " to record" : " to start; tap again to stop")),
                        recordingMode === "tap" && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: "12px", opacity: 0.85 } }, "You can also hold and release for a quick message.")),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", disabled: !controllerReady || recording || testPhase !== "idle", onClick: beginCapture }, "Change binding")),
                        bindingMessage && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { role: "status" }, bindingMessage))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Try it" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: runTest, disabled: !enabled || !modelReady || modelLoading || recording || testPhase !== "idle" },
                                React__default["default"].createElement(FaMicrophone, { size: 14 }),
                                " ",
                                testPhase === "recording" ? "Recording..." : testPhase === "transcribing" ? "Transcribing..." : "Test Dictation (3s)")),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '12px', opacity: 0.85 } }, "Shows a transcription here without sending text to your game.")),
                        hasTestResult && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { role: "status", style: { padding: '10px', backgroundColor: '#233829', borderRadius: '6px', overflowWrap: 'anywhere' } },
                                React__default["default"].createElement("strong", null, "Result"),
                                React__default["default"].createElement("div", null, lastTranscription || "No speech detected"),
                                React__default["default"].createElement("small", null, lastTranscriptionTime)))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("advanced") }, "Advanced settings"))),
                page === "advanced" && React__default["default"].createElement(React__default["default"].Fragment, null,
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Transcription model" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { ref: advancedModelRowRef },
                                React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("model") },
                                    "Model: ",
                                    MODEL_SIZE_OPTIONS.find(option => option.data === modelSize)?.label || modelSize))),
                        modelReady && !modelLoading && inferenceDevice && (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null, inferenceDevice === "gpu"
                                ? "whisper.cpp runs on the GPU via Vulkan."
                                : "whisper.cpp runs on the CPU."))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '12px' } }, "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use."))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Sending" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: "Transcription sending", menuLabel: "Transcription sending", rgOptions: [{ data: "immediate", label: "Send immediately" }, { data: "review", label: "Review before sending" }, { data: "countdown", label: "Send after countdown" }], selectedOption: sendingMode, onChange: async (option) => {
                                    const next = option.data;
                                    const result = await setSendingModeRpc(next);
                                    if (result.success) {
                                        setSendingMode(next);
                                        setRpcError("");
                                    }
                                    else
                                        setRpcError(result.error || "Could not update sending mode");
                                } })),
                        sendingMode === "review" && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '13px', lineHeight: '1.5' } },
                                "Review stays visible until you decide. Tap ",
                                buttons.join('+'),
                                " to send; hold it to cancel. Open Decktation to review longer text.")),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Press Enter yourself", description: "Type into chat without submitting", checked: manualSend, onChange: async (next) => { setManualSend(next); await setManualSendRpc(next); } })),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Remember channel", description: "Reuse the last spoken channel", checked: rememberLastChannel, onChange: async (next) => {
                                    setRememberLastChannel(next);
                                    const result = await setRememberLastChannelRpc(next);
                                    if (!result.success) {
                                        setRememberLastChannel(!next);
                                        setRpcError(result.error || "Could not update channel setting");
                                    }
                                } }))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Feedback" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: "Recording cue", menuLabel: "Recording cue", rgOptions: [{ data: "toast", label: "Toast" }, { data: "overlay", label: "Overlay" }, { data: "none", label: "None" }], selectedOption: recordingIndicator, onChange: async (option) => { const mode = option.data; setRecordingIndicator(mode); logic.recordingIndicator = mode; const result = await setRecordingIndicatorRpc(mode); if (!result.success)
                                    setRpcError(result.error || "Could not update recording cue"); } })),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Haptic feedback", description: "Cues on the controller when recording starts and stops", checked: hapticFeedback, onChange: async (next) => {
                                    const result = await setHapticFeedbackRpc(next);
                                    if (result.success)
                                        setHapticFeedback(next);
                                    else
                                        setRpcError(result.error || "Could not update haptic feedback");
                                } }))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("diagnostics") }, "Diagnostics")),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("help") }, "Help & permissions"))),
                page === "diagnostics" && React__default["default"].createElement(React__default["default"].Fragment, null,
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Input and service" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                "Controller: ",
                                controllerStatus)),
                        pendingDraft && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                "Review confirmation: ",
                                reviewBlockReason || "Ready")),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                "Binding supported: ",
                                controllerComboSupported ? "Yes" : "No")),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                "Held buttons: ",
                                React__default["default"].createElement("strong", null, buttonState))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                "Keyboard helper: ",
                                inputReady ? "Ready" : "Unavailable")),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                "Backend: ",
                                serviceReady ? "Ready" : "Unavailable")),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                "Model: ",
                                modelLoading ? "Loading" : modelReady ? "Ready" : "Unavailable")),
                        (statusError || rpcError) && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { role: "alert" }, statusError || rpcError))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Diagnostics sharing" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Share", description: "Optional scrubbed diagnostics sent to Sentry", checked: shareDiagnostics, onChange: async (next) => {
                                    setShareDiagnostics(next);
                                    const result = await setShareDiagnosticsRpc(next);
                                    if (!result.success) {
                                        setShareDiagnostics(!next);
                                        setRpcError(result.error || "Could not update diagnostics setting");
                                    }
                                } })))),
                page === "game" && React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Game" },
                    rpcError && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { role: "alert" }, rpcError)),
                    presets.map(option => React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, { key: String(option.data) },
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: async () => {
                                const next = option.data;
                                setRpcError("");
                                const result = await setActivePresetRpc(next);
                                if (result.success) {
                                    setActivePreset(next);
                                    setPage("main");
                                }
                                else
                                    setRpcError(result.error || "Could not update game");
                            } },
                            option.data === activePreset ? "✓ " : "",
                            option.label)))),
                page === "recording-mode" && React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Recording mode" },
                    rpcError && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { role: "alert" }, rpcError)),
                    ["hold", "tap"].map(mode => React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, { key: mode },
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", disabled: recording, onClick: async () => {
                                setRpcError("");
                                try {
                                    const result = await setRecordingModeRpc(mode);
                                    if (result.success) {
                                        setRecordingMode(mode);
                                        setPage("main");
                                    }
                                    else
                                        setRpcError(result.error || "Could not change recording mode");
                                }
                                catch (error) {
                                    setRpcError(String(error));
                                }
                            } },
                            mode === recordingMode ? "✓ " : "",
                            mode === "hold" ? "Hold to record" : "Tap to start/stop"),
                        React__default["default"].createElement("div", { style: { fontSize: "12px", padding: "6px 0", opacity: 0.85 } }, mode === "hold"
                            ? "Hold the binding to record. Release to stop and send."
                            : "Tap once to start recording, then tap again to stop. You can also hold and release for a quick message.")))),
                page === "model" && React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Model" },
                    rpcError && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { role: "alert" }, rpcError)),
                    MODEL_SIZE_OPTIONS.map(option => React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, { key: String(option.data) },
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: async () => {
                                const next = option.data;
                                setRpcError("");
                                if (enabled && modelReady)
                                    setModelLoading(true);
                                const result = await setModelSizeRpc(next);
                                if (result.success) {
                                    setModelSize(next);
                                    setPage("advanced");
                                }
                                else {
                                    setModelLoading(false);
                                    setRpcError(result.error || "Could not update model size");
                                }
                            } },
                            option.data === modelSize ? "✓ " : "",
                            option.label)))),
                page === "help" && React__default["default"].createElement(React__default["default"].Fragment, null,
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "How to use" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '13px', lineHeight: '1.6' } },
                                recordingMode === "hold" ? "Hold " : "Tap ",
                                React__default["default"].createElement("strong", null, buttons.join('+')),
                                " ",
                                recordingMode === "hold" ? "to record." : "to start recording; tap again to stop. Holding and releasing also works for quick messages.",
                                "Stopping transcribes and types into the active game or app. Keep it in the foreground."))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Permissions" },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '13px', lineHeight: '1.5' } }, "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.")))))));
    };
    var index = deckyFrontendLib.definePlugin(() => {
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
            if (!logic.enabled || notifyPollInFlight)
                return;
            notifyPollInFlight = true;
            try {
                const visible = logic.readQamVisibility?.() ?? null;
                if (visible === false && logic.qamVisible)
                    logic.qamClosedAt = Date.now();
                logic.qamKnown = visible !== null;
                logic.qamVisible = visible === true;
                await setReviewContextRpc(logic.qamVisible, logic.qamKnown);
                if (logic.armedDraftId && logic.qamKnown && !logic.qamVisible && Date.now() - logic.qamClosedAt >= 500) {
                    const draftId = logic.armedDraftId;
                    logic.armedDraftId = "";
                    const sent = await sendArmedDraftRpc(draftId);
                    if (!sent.success)
                        void logic.notify("Review transcription", 5000, sent.error || "Open Decktation to retry");
                }
                const result = await getStatus();
                if (result.success) {
                    const startCount = result.recording_start_count || 0;
                    if (logic.recordingIndicator === "toast" && startCount > logic.prevRecordingStartCount) {
                        logic.notify("Recording", 1500, "🎤 Recording...");
                    }
                    logic.prevRecordingStartCount = startCount;
                    const draft = result.pending_draft;
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
                        logic.lastPendingToastId = await logic.notify("Review transcription", 6000, `“${draft.text}” — open Decktation to ${draft.action.toLowerCase()} or cancel`);
                    }
                    logic.prevPendingId = draftId;
                }
            }
            catch (_e) {
            }
            finally {
                notifyPollInFlight = false;
            }
        }, 1000);
        return {
            title: React__default["default"].createElement("div", { className: deckyFrontendLib.quickAccessMenuClasses.Title }, "Decktation"),
            content: React__default["default"].createElement(DecktationPanel, { logic: logic }),
            icon: React__default["default"].createElement(FaMicrophone, null),
            onDismount() {
                clearInterval(bgNotifyInterval);
                if (logic.recording) {
                    void stopRecording();
                }
            },
            alwaysRender: true
        };
    });

    return index;

})(DFL, SP_REACT);
