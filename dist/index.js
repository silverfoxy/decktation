(function (deckyFrontendLib, React) {
    'use strict';

    function _interopDefaultLegacy (e) { return e && typeof e === 'object' && 'default' in e ? e : { 'default': e }; }

    var React__default = /*#__PURE__*/_interopDefaultLegacy(React);

    const unavailable = "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.";
    async function requestPluginUpdate(update) {
        try {
            const loader = (typeof window === "undefined" ? undefined :
                window.DeckyBackend);
            if (typeof loader?.call !== "function")
                return { success: false, error: unavailable };
            // Defense against accidentally handing a remote artifact to Loader.
            if (!/^file:\/\/\/tmp\/decktation-update-[A-Za-z0-9_-]+\.zip$/.test(update.artifact)) {
                return { success: false, error: "The update could not be verified, so it was not installed." };
            }
            const result = await loader.call("utilities/install_plugin", update.artifact, "Decktation", update.version, update.hash, 2);
            if (result === false || (result && typeof result === "object" &&
                "success" in result && result.success === false)) {
                return { success: false, error: unavailable };
            }
            // This requests a native prompt; it does not report installation success.
            leaveStalePluginPanel();
            return { success: true };
        }
        catch (_error) {
            return { success: false, error: unavailable };
        }
    }
    /** Optional navigation workaround for Loader #976; no Steam patches or reloads. */
    function leaveStalePluginPanel() {
        try {
            const state = (typeof window === "undefined" ? undefined :
                window.DeckyPluginLoader?.deckyState);
            if (typeof state?.publicState !== "function" || typeof state.closeActivePlugin !== "function" ||
                state.publicState().activePlugin?.name !== "Decktation")
                return false;
            state.closeActivePlugin();
            return true;
        }
        catch (_error) {
            return false;
        }
    }

    var version = "0.3.19";

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

    var _manifest = {"name":"Decktation","version":"0.3.19","author":"silverfoxy","flags":["root"],"api_version":1,"publish":{"tags":["voice","dictation","speech-to-text","input","chat","gaming","accessibility"],"description":"Push-to-talk dictation for Steam Deck. Context-aware speech-to-text using whisper.cpp.","image":"https://raw.githubusercontent.com/silverfoxy/decktation/master/store-card.png"}};

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
    function FaArrowCircleUp (props) {
      return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M8 256C8 119 119 8 256 8s248 111 248 248-111 248-248 248S8 393 8 256zm143.6 28.9l72.4-75.5V392c0 13.3 10.7 24 24 24h16c13.3 0 24-10.7 24-24V209.4l72.4 75.5c9.3 9.7 24.8 9.9 34.3.4l10.9-11c9.4-9.4 9.4-24.6 0-33.9L273 107.7c-9.4-9.4-24.6-9.4-33.9 0L106.3 240.4c-9.4 9.4-9.4 24.6 0 33.9l10.9 11c9.6 9.5 25.1 9.3 34.4-.4z"}}]})(props);
    }function FaMicrophone (props) {
      return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 352 512"},"child":[{"tag":"path","attr":{"d":"M176 352c53.02 0 96-42.98 96-96V96c0-53.02-42.98-96-96-96S80 42.98 80 96v160c0 53.02 42.98 96 96 96zm160-160h-16c-8.84 0-16 7.16-16 16v48c0 74.8-64.49 134.82-140.79 127.38C96.71 376.89 48 317.11 48 250.3V208c0-8.84-7.16-16-16-16H16c-8.84 0-16 7.16-16 16v40.16c0 89.64 63.97 169.55 152 181.69V464H96c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16h-56v-33.77C285.71 418.47 352 344.9 352 256v-48c0-8.84-7.16-16-16-16z"}}]})(props);
    }

    var Back$9 = "Back";
    var Enable$9 = "Enable";
    var Language$9 = "Language";
    var Binding$9 = "Binding";
    var Result$9 = "Result";
    var Model$9 = "Model";
    var Sending$9 = "Sending";
    var Confirm$9 = "Confirm";
    var Manual$9 = "Manual";
    var Feedback$9 = "Feedback";
    var Toast$9 = "Toast";
    var Overlay$9 = "Overlay";
    var None$9 = "None";
    var Diagnostics$9 = "Diagnostics";
    var Controller$9 = "Controller";
    var Yes$9 = "Yes";
    var No$9 = "No";
    var Backend$9 = "Backend";
    var Ready$9 = "Ready";
    var Unavailable$9 = "Unavailable";
    var Loading$9 = "Loading";
    var Share$9 = "Share";
    var Permissions$9 = "Permissions";
    var Recording$9 = "Recording";
    var Generic$9 = "Generic";
    var Interface$9 = "Interface";
    var Mode$9 = "Mode";
    var Send$9 = "Send";
    var Cancel$9 = "Cancel";
    var Updates$9 = "Updates";
    var en$1 = {
      Back: Back$9,
      Enable: Enable$9,
      "Quick settings": "Quick settings",
      Language: Language$9,
      Binding: Binding$9,
      "Edit Bindings": "Edit Bindings",
      "Try it": "Try it",
      "Recording...": "Recording...",
      "Transcribing...": "Transcribing...",
      "Test Dictation (3s)": "Test Dictation (3s)",
      "Shows a transcription here without sending text to your game.": "Shows a transcription here without sending text to your game.",
      Result: Result$9,
      "No speech detected": "No speech detected",
      "Advanced settings": "Advanced settings",
      "Transcription model": "Transcription model",
      Model: Model$9,
      "Recording binding": "Recording binding",
      Sending: Sending$9,
      Confirm: Confirm$9,
      "Delay before send": "Delay before send",
      Manual: Manual$9,
      "You press Enter": "You press Enter",
      "Remember channel": "Remember channel",
      "Reuse the last spoken channel": "Reuse the last spoken channel",
      Feedback: Feedback$9,
      "Recording cue": "Recording cue",
      Toast: Toast$9,
      Overlay: Overlay$9,
      None: None$9,
      "Haptic feedback": "Haptic feedback",
      "Cues on the controller when recording starts and stops": "Cues on the controller when recording starts and stops",
      Diagnostics: Diagnostics$9,
      "Help & permissions": "Help & permissions",
      "Input and service": "Input and service",
      Controller: Controller$9,
      "Binding supported": "Binding supported",
      Yes: Yes$9,
      No: No$9,
      "Held buttons": "Held buttons",
      "Keyboard helper": "Keyboard helper",
      Backend: Backend$9,
      Ready: Ready$9,
      Unavailable: Unavailable$9,
      Loading: Loading$9,
      "Diagnostics sharing": "Diagnostics sharing",
      Share: Share$9,
      "Optional scrubbed diagnostics sent to Sentry": "Optional scrubbed diagnostics sent to Sentry",
      "How to use": "How to use",
      Permissions: Permissions$9,
      "Auto Detect": "Auto Detect",
      "Popular Steam languages": "Popular Steam languages",
      "Other languages": "Other languages",
      "Add Button": "Add Button",
      "Button {number}": "Button {number}",
      "Remove button {number}": "Remove button {number}",
      "Hold {binding} to record": "Hold {binding} to record",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.",
      "together ": "together ",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cpp runs on the GPU via Vulkan.",
      "whisper.cpp runs on the CPU.": "whisper.cpp runs on the CPU.",
      "Connecting to Decktation...": "Connecting to Decktation...",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "Keyboard helper unavailable. Reload or reinstall Decktation.",
      "Loading transcription model...": "Loading transcription model...",
      "Decktation is off": "Decktation is off",
      "Model not ready": "Model not ready",
      "Controller unavailable": "Controller unavailable",
      "Backend unavailable: {error}": "Backend unavailable: {error}",
      "Recording for 3 seconds...": "Recording for 3 seconds...",
      Recording: Recording$9,
      "Sending in {seconds}s": "Sending in {seconds}s",
      "\"{text}\" — hold PTT to cancel": "\"{text}\" — hold PTT to cancel",
      "Interface language": "Interface language",
      "Automatic (system)": "Automatic (Steam)",
      "Only changes the menu language, not the dictation language.": "Only changes the menu language, not the dictation language.",
      Generic: Generic$9,
      "Base · Fast": "Base · Fast",
      "Small · Balanced": "Small · Balanced",
      "Medium · More accurate": "Medium · More accurate",
      "Could not start test recording": "Could not start test recording",
      "Could not transcribe test recording": "Could not transcribe test recording",
      "Could not read test transcription": "Could not read test transcription",
      "Could not update enabled state": "Could not update enabled state",
      "Could not load Whisper model": "Could not load Whisper model",
      "Could not remove button": "Could not remove button",
      "Could not update channel setting": "Could not update channel setting",
      "Could not update recording cue": "Could not update recording cue",
      "Could not update haptic feedback": "Could not update haptic feedback",
      "Could not update diagnostics setting": "Could not update diagnostics setting",
      "Could not update game": "Could not update game",
      "Could not update model size": "Could not update model size",
      "Could not update binding": "Could not update binding",
      "Could not update language": "Could not update language",
      "L1 Bumper": "L1 Bumper",
      "R1 Bumper": "R1 Bumper",
      "L2 Trigger": "L2 Trigger",
      "R2 Trigger": "R2 Trigger",
      "L4 Grip": "L4 Grip",
      "R4 Grip": "R4 Grip",
      "L5 Grip": "L5 Grip",
      "R5 Grip": "R5 Grip",
      "Waiting for input": "Waiting for input",
      "Status unavailable": "Status unavailable",
      "Backend status request failed": "Backend status request failed",
      "Could not update language setting": "Could not update language setting",
      Interface: Interface$9,
      Mode: Mode$9,
      "Review transcription": "Review transcription",
      "Transcription sending": "Transcription sending",
      "Send immediately": "Send immediately",
      "Review before sending": "Review before sending",
      "Send after countdown": "Send after countdown",
      "Press Enter yourself": "Press Enter yourself",
      "Type into chat without submitting": "Type into chat without submitting",
      Send: Send$9,
      Cancel: Cancel$9,
      "Type into chat": "Type into chat",
      "Review confirmation": "Review confirmation",
      "After typing, press Enter in the game": "After typing, press Enter in the game",
      "Open Decktation to retry": "Open Decktation to retry",
      "Could not approve draft": "Could not approve draft",
      "Could not cancel draft": "Could not cancel draft",
      "Could not update sending mode": "Could not update sending mode",
      "Transcription. Use Up and Down to scroll.": "Transcription. Use Up and Down to scroll.",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "Closes this menu before typing into your game. Keep your game in the foreground.",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — open Decktation to review, send or cancel",
      "Typing transcription…": "Typing transcription…",
      "Open Decktation to retry typing": "Open Decktation to retry typing",
      "Open Decktation to review and send": "Open Decktation to review and send",
      "Open Decktation to review all": "Open Decktation to review all",
      "Close Steam menus and return to your game": "Close Steam menus and return to your game",
      "Open Decktation to confirm sending": "Open Decktation to confirm sending",
      "Update available": "Update available",
      "Preparing update...": "Preparing update...",
      "Waiting for Decky confirmation...": "Waiting for Decky confirmation...",
      "Update to {version}": "Update to {version}",
      Updates: Updates$9,
      "Version {version}": "Version {version}",
      "Update available: {version}": "Update available: {version}",
      "Up to date": "Up to date",
      "Checking for updates...": "Checking for updates...",
      "Check again": "Check again",
      "Check for updates": "Check for updates",
      "Decktation update available": "Decktation update available",
      "Could not check for updates.": "Could not check for updates.",
      "The update could not be verified, so it was not installed.": "The update could not be verified, so it was not installed.",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.",
      "An update is already being prepared.": "An update is already being prepared.",
      "Wait for the transcription model to finish loading.": "Wait for the transcription model to finish loading.",
      "Finish the current dictation before updating.": "Finish the current dictation before updating.",
      "Binding saved: {binding}": "Binding saved: {binding}",
      "Binding cancelled. Your previous binding is unchanged.": "Binding cancelled. Your previous binding is unchanged.",
      "Could not start binding capture": "Could not start binding capture",
      "Release all buttons to start listening.": "Release all buttons to start listening.",
      "Hold your new combination together. Release to save.": "Hold your new combination together. Release to save.",
      "Detected:": "Detected:",
      "Listening…": "Listening…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.",
      "Cancel (touch)": "Cancel (touch)",
      "Change binding": "Change binding",
      "Spoken punctuation": "Spoken punctuation",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.",
      "Could not set spoken punctuation": "Could not set spoken punctuation",
      "Microphone troubleshooting": "Microphone troubleshooting",
      "Microphone guide. Use Up and Down to scroll.": "Microphone guide. Use Up and Down to scroll.",
      "Start with a dictation test": "Start with a dictation test",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.",
      "If audio crackles, pops, or cuts out": "If audio crackles, pops, or cuts out",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.",
      "Open Steam → Power → Switch to Desktop.": "Open Steam → Power → Switch to Desktop.",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.",
      "If the problem persists": "If the problem persists",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.",
      "Open full guide online": "Open full guide online",
      "Microphone help": "Microphone help",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.",
      "Having problems with your microphone?": "Having problems with your microphone?",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.",
      "Binding timed out. Your previous binding is unchanged.": "Binding timed out. Your previous binding is unchanged.",
      "Controller disconnected. Your previous binding is unchanged.": "Controller disconnected. Your previous binding is unchanged.",
      "Use at most five buttons.": "Use at most five buttons.",
      "Finish recording before changing the binding.": "Finish recording before changing the binding.",
      "Controller listener unavailable.": "Controller listener unavailable.",
      "Binding session ended.": "Binding session ended."
    };

    var af = "Afrikaans";
    var am = "አማርኛ";
    var ar = "العربية";
    var as = "অসমীয়া";
    var az = "Azərbaycanca";
    var ba = "Башҡортса";
    var be = "Беларуская";
    var bg = "Български";
    var bn = "বাংলা";
    var bo = "བོད་སྐད་";
    var br = "Brezhoneg";
    var bs = "Bosanski";
    var ca = "Català";
    var cs = "Čeština";
    var cy = "Cymraeg";
    var da = "Dansk";
    var de$1 = "Deutsch";
    var el = "Ελληνικά";
    var en = "English";
    var es$1 = "Español";
    var et = "Eesti";
    var eu = "Euskara";
    var fa = "فارسی";
    var fi = "Suomi";
    var fo = "Føroyskt";
    var fr$1 = "Français";
    var gl = "Galego";
    var gu = "ગુજરાતી";
    var ha = "Hausa";
    var haw = "ʻŌlelo Hawaiʻi";
    var he = "עברית";
    var hi = "हिन्दी";
    var hr = "Hrvatski";
    var ht = "Kreyòl ayisyen";
    var hu = "Magyar";
    var hy = "Հայերեն";
    var id = "Bahasa Indonesia";
    var is = "Íslenska";
    var it = "Italiano";
    var ja$1 = "日本語";
    var jw = "Basa Jawa";
    var ka = "ქართული";
    var kk = "Қазақша";
    var km = "ខ្មែរ";
    var kn = "ಕನ್ನಡ";
    var ko$1 = "한국어";
    var la = "Latina";
    var lb = "Lëtzebuergesch";
    var ln = "Lingála";
    var lo = "ລາວ";
    var lt = "Lietuvių";
    var lv = "Latviešu";
    var mg = "Malagasy";
    var mi = "Māori";
    var mk = "Македонски";
    var ml = "മലയാളം";
    var mn = "Монгол";
    var mr = "मराठी";
    var ms = "Bahasa Melayu";
    var mt = "Malti";
    var my = "မြန်မာ";
    var ne = "नेपाली";
    var nl = "Nederlands";
    var nn = "Norsk nynorsk";
    var no = "Norsk";
    var oc = "Occitan";
    var pa = "ਪੰਜਾਬੀ";
    var pl$1 = "Polski";
    var ps = "پښتو";
    var pt$1 = "Português";
    var ro = "Română";
    var ru$1 = "Русский";
    var sa = "संस्कृतम्";
    var sd = "سنڌي";
    var si = "සිංහල";
    var sk = "Slovenčina";
    var sl = "Slovenščina";
    var sn = "ChiShona";
    var so = "Soomaali";
    var sq = "Shqip";
    var sr = "Српски";
    var su = "Basa Sunda";
    var sv = "Svenska";
    var sw = "Kiswahili";
    var ta = "தமிழ்";
    var te = "తెలుగు";
    var tg = "Тоҷикӣ";
    var th = "ไทย";
    var tk = "Türkmençe";
    var tl = "Tagalog";
    var tr = "Türkçe";
    var tt = "Татарча";
    var uk = "Українська";
    var ur = "اردو";
    var uz = "Oʻzbekcha";
    var vi = "Tiếng Việt";
    var yi = "ייִדיש";
    var yo = "Yorùbá";
    var yue = "粵語";
    var zh$1 = "中文";
    var nativeLanguageNames = {
      af: af,
      am: am,
      ar: ar,
      as: as,
      az: az,
      ba: ba,
      be: be,
      bg: bg,
      bn: bn,
      bo: bo,
      br: br,
      bs: bs,
      ca: ca,
      cs: cs,
      cy: cy,
      da: da,
      de: de$1,
      el: el,
      en: en,
      es: es$1,
      et: et,
      eu: eu,
      fa: fa,
      fi: fi,
      fo: fo,
      fr: fr$1,
      gl: gl,
      gu: gu,
      ha: ha,
      haw: haw,
      he: he,
      hi: hi,
      hr: hr,
      ht: ht,
      hu: hu,
      hy: hy,
      id: id,
      is: is,
      it: it,
      ja: ja$1,
      jw: jw,
      ka: ka,
      kk: kk,
      km: km,
      kn: kn,
      ko: ko$1,
      la: la,
      lb: lb,
      ln: ln,
      lo: lo,
      lt: lt,
      lv: lv,
      mg: mg,
      mi: mi,
      mk: mk,
      ml: ml,
      mn: mn,
      mr: mr,
      ms: ms,
      mt: mt,
      my: my,
      ne: ne,
      nl: nl,
      nn: nn,
      no: no,
      oc: oc,
      pa: pa,
      pl: pl$1,
      ps: ps,
      pt: pt$1,
      ro: ro,
      ru: ru$1,
      sa: sa,
      sd: sd,
      si: si,
      sk: sk,
      sl: sl,
      sn: sn,
      so: so,
      sq: sq,
      sr: sr,
      su: su,
      sv: sv,
      sw: sw,
      ta: ta,
      te: te,
      tg: tg,
      th: th,
      tk: tk,
      tl: tl,
      tr: tr,
      tt: tt,
      uk: uk,
      ur: ur,
      uz: uz,
      vi: vi,
      yi: yi,
      yo: yo,
      yue: yue,
      zh: zh$1
    };

    var Back$8 = "Volver";
    var Enable$8 = "Activar";
    var Language$8 = "Idioma del dictado";
    var Binding$8 = "Combinación";
    var Result$8 = "Resultado";
    var Model$8 = "Modelo";
    var Sending$8 = "Envío";
    var Confirm$8 = "Confirmar";
    var Manual$8 = "Envío manual";
    var Feedback$8 = "Indicadores";
    var Toast$8 = "Notificación";
    var Overlay$8 = "Indicador en pantalla";
    var None$8 = "Ninguno";
    var Diagnostics$8 = "Diagnóstico";
    var Controller$8 = "Mando";
    var Yes$8 = "Sí";
    var No$8 = "No";
    var Backend$8 = "Servicio del plugin";
    var Ready$8 = "Listo";
    var Unavailable$8 = "No disponible";
    var Loading$8 = "Cargando";
    var Share$8 = "Compartir";
    var Permissions$8 = "Permisos";
    var Recording$8 = "Grabación";
    var Generic$8 = "Texto general";
    var Interface$8 = "Interfaz";
    var Mode$8 = "Modo";
    var Send$8 = "Enviar";
    var Cancel$8 = "Cancelar";
    var Updates$8 = "Actualizaciones";
    var es = {
      Back: Back$8,
      Enable: Enable$8,
      "Quick settings": "Ajustes rápidos",
      Language: Language$8,
      Binding: Binding$8,
      "Edit Bindings": "Editar combinación",
      "Try it": "Prueba de dictado",
      "Recording...": "Grabando...",
      "Transcribing...": "Transcribiendo...",
      "Test Dictation (3s)": "Probar dictado (3 s)",
      "Shows a transcription here without sending text to your game.": "Muestra el texto aquí sin enviarlo al juego.",
      Result: Result$8,
      "No speech detected": "No se detectó voz",
      "Advanced settings": "Ajustes avanzados",
      "Transcription model": "Modelo de transcripción",
      Model: Model$8,
      "Recording binding": "Combinación para grabar",
      Sending: Sending$8,
      Confirm: Confirm$8,
      "Delay before send": "Esperar antes de enviar",
      Manual: Manual$8,
      "You press Enter": "Pulsa Intro para enviar",
      "Remember channel": "Recordar canal",
      "Reuse the last spoken channel": "Reutilizar el último canal indicado",
      Feedback: Feedback$8,
      "Recording cue": "Indicador de grabación",
      Toast: Toast$8,
      Overlay: Overlay$8,
      None: None$8,
      "Haptic feedback": "Vibración al grabar",
      "Cues on the controller when recording starts and stops": "Vibración en el mando al iniciar y terminar la grabación",
      Diagnostics: Diagnostics$8,
      "Help & permissions": "Ayuda y permisos",
      "Input and service": "Entrada y servicio",
      Controller: Controller$8,
      "Binding supported": "Combinación compatible",
      Yes: Yes$8,
      No: No$8,
      "Held buttons": "Botones pulsados",
      "Keyboard helper": "Servicio de teclado",
      Backend: Backend$8,
      Ready: Ready$8,
      Unavailable: Unavailable$8,
      Loading: Loading$8,
      "Diagnostics sharing": "Compartir diagnóstico",
      Share: Share$8,
      "Optional scrubbed diagnostics sent to Sentry": "Envía datos de diagnóstico depurados a Sentry (opcional)",
      "How to use": "Cómo usarlo",
      Permissions: Permissions$8,
      "Auto Detect": "Detección automática",
      "Popular Steam languages": "Idiomas habituales de Steam",
      "Other languages": "Otros idiomas",
      "Add Button": "Añadir botón",
      "Button {number}": "Botón {number}",
      "Remove button {number}": "Eliminar botón {number}",
      "Hold {binding} to record": "Mantén {binding} para grabar",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "Mantén {binding} {together}para grabar. Suelta para transcribir y escribir en el juego o aplicación que esté en primer plano.",
      "together ": "a la vez ",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktation usa el acceso root de Decky para leer los botones del mando y generar eventos de teclado con el dictado. La transcripción se transmite como texto, nunca como un comando de consola.",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Base es el más rápido. Small equilibra rapidez y precisión. Medium ofrece más precisión, pero es más lento y puede descargarse al usarlo por primera vez.",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cpp usa la GPU mediante Vulkan.",
      "whisper.cpp runs on the CPU.": "whisper.cpp usa la CPU.",
      "Connecting to Decktation...": "Conectando con Decktation...",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "El servicio de teclado no está disponible. Recarga o reinstala Decktation.",
      "Loading transcription model...": "Cargando el modelo de transcripción...",
      "Decktation is off": "Decktation está desactivado",
      "Model not ready": "El modelo no está listo",
      "Controller unavailable": "Mando no disponible",
      "Backend unavailable: {error}": "Servicio no disponible: {error}",
      "Recording for 3 seconds...": "Grabando durante 3 segundos...",
      Recording: Recording$8,
      "Sending in {seconds}s": "Envío en {seconds} s",
      "\"{text}\" — hold PTT to cancel": "«{text}» — mantén la combinación de grabación para cancelar",
      "Interface language": "Idioma de la interfaz",
      "Automatic (system)": "Automático (Steam)",
      "Only changes the menu language, not the dictation language.": "Solo cambia el idioma del menú, no el del dictado.",
      Generic: Generic$8,
      "Base · Fast": "Base · Rápido",
      "Small · Balanced": "Small · Equilibrado",
      "Medium · More accurate": "Medium · Más preciso",
      "Could not start test recording": "No se pudo iniciar la prueba",
      "Could not transcribe test recording": "No se pudo transcribir la prueba",
      "Could not read test transcription": "No se pudo leer el resultado de la prueba",
      "Could not update enabled state": "No se pudo activar o desactivar Decktation",
      "Could not load Whisper model": "No se pudo cargar el modelo Whisper",
      "Could not remove button": "No se pudo eliminar el botón",
      "Could not update channel setting": "No se pudo cambiar el ajuste del canal",
      "Could not update recording cue": "No se pudo cambiar el indicador de grabación",
      "Could not update haptic feedback": "No se pudo cambiar la vibración",
      "Could not update diagnostics setting": "No se pudo cambiar el ajuste de diagnóstico",
      "Could not update game": "No se pudo cambiar el modo",
      "Could not update model size": "No se pudo cambiar el modelo",
      "Could not update binding": "No se pudo cambiar la combinación",
      "Could not update language": "No se pudo cambiar el idioma",
      "L1 Bumper": "L1 (superior)",
      "R1 Bumper": "R1 (superior)",
      "L2 Trigger": "L2 (gatillo)",
      "R2 Trigger": "R2 (gatillo)",
      "L4 Grip": "L4 (trasero)",
      "R4 Grip": "R4 (trasero)",
      "L5 Grip": "L5 (trasero)",
      "R5 Grip": "R5 (trasero)",
      "Waiting for input": "Esperando entrada",
      "Status unavailable": "Estado no disponible",
      "Backend status request failed": "No se pudo consultar el estado del servicio",
      "Could not update language setting": "No se pudo cambiar el idioma del dictado",
      Interface: Interface$8,
      Mode: Mode$8,
      "Review transcription": "Revisar transcripción",
      "Transcription sending": "Envío de la transcripción",
      "Send immediately": "Enviar inmediatamente",
      "Review before sending": "Revisar antes de enviar",
      "Send after countdown": "Enviar tras la cuenta atrás",
      "Press Enter yourself": "Pulsar Enter manualmente",
      "Type into chat without submitting": "Escribir en el chat sin enviar",
      Send: Send$8,
      Cancel: Cancel$8,
      "Type into chat": "Escribir en el chat",
      "Review confirmation": "Confirmación de la revisión",
      "After typing, press Enter in the game": "Después de escribir, pulsa Enter en el juego",
      "Open Decktation to retry": "Abre Decktation para reintentar",
      "Could not approve draft": "No se pudo aprobar el borrador",
      "Could not cancel draft": "No se pudo cancelar el borrador",
      "Could not update sending mode": "No se pudo cambiar el modo de envío",
      "Transcription. Use Up and Down to scroll.": "Transcripción. Usa Arriba y Abajo para desplazarte.",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "Cierra este menú antes de escribir en el juego. Mantén el juego en primer plano.",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "La revisión permanece visible hasta que decidas. Pulsa {binding} para enviar; mantenlo pulsado para cancelar. Abre Decktation para revisar textos largos.",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — abre Decktation para revisar, enviar o cancelar",
      "Typing transcription…": "Escribiendo transcripción…",
      "Open Decktation to retry typing": "Abre Decktation para reintentar la escritura",
      "Open Decktation to review and send": "Abre Decktation para revisar y enviar",
      "Open Decktation to review all": "Abre Decktation para revisar todo",
      "Close Steam menus and return to your game": "Cierra los menús de Steam y vuelve al juego",
      "Open Decktation to confirm sending": "Abre Decktation para confirmar el envío",
      "Update available": "Actualización disponible",
      "Preparing update...": "Preparando actualización...",
      "Waiting for Decky confirmation...": "Esperando confirmación de Decky...",
      "Update to {version}": "Actualizar a {version}",
      Updates: Updates$8,
      "Version {version}": "Versión {version}",
      "Update available: {version}": "Actualización disponible: {version}",
      "Up to date": "Al día",
      "Checking for updates...": "Buscando actualizaciones...",
      "Check again": "Comprobar de nuevo",
      "Check for updates": "Buscar actualizaciones",
      "Decktation update available": "Actualización de Decktation disponible",
      "Could not check for updates.": "No se pudieron buscar actualizaciones.",
      "The update could not be verified, so it was not installed.": "No se pudo verificar la actualización, por lo que no se instaló.",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "El instalador de complementos de Decky no está disponible en esta versión. Actualiza manualmente con el ZIP de Decktation.",
      "An update is already being prepared.": "Ya se está preparando una actualización.",
      "Wait for the transcription model to finish loading.": "Espera a que termine de cargar el modelo de transcripción.",
      "Finish the current dictation before updating.": "Termina el dictado actual antes de actualizar.",
      "Binding saved: {binding}": "Asignación guardada: {binding}",
      "Binding cancelled. Your previous binding is unchanged.": "Asignación cancelada. Se mantiene la asignación anterior.",
      "Could not start binding capture": "No se pudo iniciar la captura de la asignación",
      "Release all buttons to start listening.": "Suelta todos los botones para empezar a escuchar.",
      "Hold your new combination together. Release to save.": "Mantén pulsada la nueva combinación. Suelta para guardarla.",
      "Detected:": "Detectado:",
      "Listening…": "Escuchando…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "De uno a cinco botones. Steam y acceso rápido están excluidos. La captura caduca a los 20 segundos.",
      "Cancel (touch)": "Cancelar (tocar)",
      "Change binding": "Cambiar asignación",
      "Spoken punctuation": "Puntuación hablada",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "Con inglés o detección automática, di comma, period o question mark para insertar signos de puntuación. Desactiva esta opción para escribir esas palabras literalmente.",
      "Could not set spoken punctuation": "No se pudo configurar la puntuación hablada",
      "Microphone troubleshooting": "Solucionar problemas del micrófono",
      "Microphone guide. Use Up and Down to scroll.": "Guía del micrófono. Usa Arriba y Abajo para desplazarte.",
      "Start with a dictation test": "Empieza con una prueba de dictado",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "Activa Decktation, espera a que indique Listo y ejecuta Probar dictado (3 s) en la página principal. Habla con claridad. El resultado se muestra en el panel y no se escribe en el juego.",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "Comprueba que el micrófono integrado o los auriculares funcionan en otra aplicación. Si en Steam se oye bien pero falla el dictado, comprueba el dispositivo de grabación predeterminado del sistema.",
      "If audio crackles, pops, or cuts out": "Si el audio cruje, chasquea o se corta",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "Un usuario de Steam Deck LCD informó de una mejora al desactivar el procesamiento de voz de Steam. Es una solución de la comunidad, sin garantías. No se ha determinado su efecto sobre la entrada de audio de Decktation.",
      "Open Steam → Power → Switch to Desktop.": "Abre Steam → Energía → Cambiar a Escritorio.",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "En Steam, abre Amigos y chat → icono de engranaje → Voz. Algunas versiones también tienen Steam → Parámetros → Voz.",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "Selecciona el dispositivo de entrada de voz. Inicia la prueba del micrófono, habla, escucha si hay chasquidos o faltan palabras y detén la prueba.",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "Anota los ajustes actuales. En Mostrar ajustes avanzados, prueba a desactivar la cancelación de ruido, la cancelación de eco y el control automático de volumen o ganancia.",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "Repite la prueba del micrófono. Si mejora, reactiva las opciones una a una para identificar qué ajuste ayuda.",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "Vuelve al modo Juego y repite la prueba de dictado de tres segundos de Decktation antes de probar en un juego.",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "Restaura los ajustes anteriores si no ayuda. Desactivar el procesamiento puede aumentar el ruido de fondo o el eco de los altavoces y afectar al chat de voz de Steam.",
      "If the problem persists": "Si el problema persiste",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "Al informar del problema, incluye el modelo de Deck (LCD u OLED), las versiones de SteamOS y del cliente de Steam, el micrófono o los auriculares y si la mejora se mantiene en modo Juego y tras reiniciar. Comprueba los errores en el último registro del plugin.",
      "Open full guide online": "Abrir la guía completa en línea",
      "Microphone help": "Ayuda del micrófono",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "¿No reconoce la voz, faltan palabras o el audio cruje? Consulta aquí la guía del micrófono.",
      "Having problems with your microphone?": "¿Problemas con el micrófono?",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "Envía a Sentry errores depurados de datos sensibles, recuentos de uso y métricas de rendimiento, incluido el motor de inferencia y datos generales del dispositivo y del sistema. El audio y las transcripciones permanecen en el dispositivo.",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "Di command gg para introducir /gg, o command ready para /ready. Usa inglés o detección automática. Los comandos respetan los ajustes de envío.",
      "Binding timed out. Your previous binding is unchanged.": "Se agotó el tiempo. Se mantiene la asignación anterior.",
      "Controller disconnected. Your previous binding is unchanged.": "Mando desconectado. Se mantiene la asignación anterior.",
      "Use at most five buttons.": "Usa un máximo de cinco botones.",
      "Finish recording before changing the binding.": "Termina la grabación antes de cambiar la asignación.",
      "Controller listener unavailable.": "El detector de mandos no está disponible.",
      "Binding session ended.": "La sesión de asignación ha terminado."
    };

    var Back$7 = "Назад";
    var Enable$7 = "Включить";
    var Language$7 = "Язык диктовки";
    var Binding$7 = "Сочетание кнопок";
    var Result$7 = "Результат";
    var Model$7 = "Модель";
    var Sending$7 = "Отправка";
    var Confirm$7 = "Подтверждение";
    var Manual$7 = "Отправлять вручную";
    var Feedback$7 = "Индикаторы";
    var Toast$7 = "Уведомление";
    var Overlay$7 = "Индикатор на экране";
    var None$7 = "Нет";
    var Diagnostics$7 = "Диагностика";
    var Controller$7 = "Контроллер";
    var Yes$7 = "Да";
    var No$7 = "Нет";
    var Backend$7 = "Служба плагина";
    var Ready$7 = "Готово";
    var Unavailable$7 = "Недоступно";
    var Loading$7 = "Загрузка";
    var Share$7 = "Отправлять";
    var Permissions$7 = "Разрешения";
    var Recording$7 = "Запись";
    var Generic$7 = "Обычный ввод текста";
    var Interface$7 = "Интерфейс";
    var Mode$7 = "Режим";
    var Send$7 = "Отправить";
    var Cancel$7 = "Отмена";
    var Updates$7 = "Обновления";
    var ru = {
      Back: Back$7,
      Enable: Enable$7,
      "Quick settings": "Быстрые настройки",
      Language: Language$7,
      Binding: Binding$7,
      "Edit Bindings": "Изменить кнопки",
      "Try it": "Проверка диктовки",
      "Recording...": "Идёт запись…",
      "Transcribing...": "Распознавание…",
      "Test Dictation (3s)": "Проверить диктовку (3 с)",
      "Shows a transcription here without sending text to your game.": "Текст появится здесь, но не будет отправлен в игру.",
      Result: Result$7,
      "No speech detected": "Речь не обнаружена",
      "Advanced settings": "Дополнительные настройки",
      "Transcription model": "Модель распознавания",
      Model: Model$7,
      "Recording binding": "Кнопки записи",
      Sending: Sending$7,
      Confirm: Confirm$7,
      "Delay before send": "Задержка перед отправкой",
      Manual: Manual$7,
      "You press Enter": "Нажмите Enter для отправки",
      "Remember channel": "Запоминать канал",
      "Reuse the last spoken channel": "Использовать последний названный канал",
      Feedback: Feedback$7,
      "Recording cue": "Индикатор записи",
      Toast: Toast$7,
      Overlay: Overlay$7,
      None: None$7,
      "Haptic feedback": "Вибрация",
      "Cues on the controller when recording starts and stops": "Вибрация в начале и конце записи",
      Diagnostics: Diagnostics$7,
      "Help & permissions": "Помощь и разрешения",
      "Input and service": "Ввод и служба",
      Controller: Controller$7,
      "Binding supported": "Сочетание поддерживается",
      Yes: Yes$7,
      No: No$7,
      "Held buttons": "Нажатые кнопки",
      "Keyboard helper": "Служба клавиатуры",
      Backend: Backend$7,
      Ready: Ready$7,
      Unavailable: Unavailable$7,
      Loading: Loading$7,
      "Diagnostics sharing": "Отправка диагностики",
      Share: Share$7,
      "Optional scrubbed diagnostics sent to Sentry": "Необязательная отправка очищенных диагностических данных в Sentry",
      "How to use": "Как пользоваться",
      Permissions: Permissions$7,
      "Auto Detect": "Определять автоматически",
      "Popular Steam languages": "Популярные языки Steam",
      "Other languages": "Другие языки",
      "Add Button": "Добавить кнопку",
      "Button {number}": "Кнопка {number}",
      "Remove button {number}": "Удалить кнопку {number}",
      "Hold {binding} to record": "Удерживайте {binding} для записи",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "Удерживайте {binding} {together}для записи. Отпустите кнопки, чтобы распознать речь и ввести текст в активную игру или приложение. Не сворачивайте его.",
      "together ": "одновременно ",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktation использует root-доступ Decky для чтения кнопок контроллера и создания событий клавиатуры для диктуемого текста. Текст передаётся службе клавиатуры как данные, а не как команда оболочки.",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Base работает быстрее всего. Small обеспечивает баланс скорости и точности. Medium точнее, но медленнее; при первом использовании может потребоваться загрузка.",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cpp использует GPU через Vulkan.",
      "whisper.cpp runs on the CPU.": "whisper.cpp использует CPU.",
      "Connecting to Decktation...": "Подключение к Decktation…",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "Служба клавиатуры недоступна. Перезагрузите или переустановите Decktation.",
      "Loading transcription model...": "Загрузка модели распознавания…",
      "Decktation is off": "Decktation выключен",
      "Model not ready": "Модель не готова",
      "Controller unavailable": "Контроллер недоступен",
      "Backend unavailable: {error}": "Служба недоступна: {error}",
      "Recording for 3 seconds...": "Запись в течение 3 секунд…",
      Recording: Recording$7,
      "Sending in {seconds}s": "Отправка через {seconds} с",
      "\"{text}\" — hold PTT to cancel": "«{text}» — удерживайте кнопки записи для отмены",
      "Interface language": "Язык интерфейса",
      "Automatic (system)": "Автоматически (Steam)",
      "Only changes the menu language, not the dictation language.": "Меняет только язык меню, а не язык диктовки.",
      Generic: Generic$7,
      "Base · Fast": "Base · Быстро",
      "Small · Balanced": "Small · Баланс",
      "Medium · More accurate": "Medium · Точнее",
      "Could not start test recording": "Не удалось начать проверку",
      "Could not transcribe test recording": "Не удалось распознать тестовую запись",
      "Could not read test transcription": "Не удалось прочитать результат проверки",
      "Could not update enabled state": "Не удалось включить или выключить Decktation",
      "Could not load Whisper model": "Не удалось загрузить модель Whisper",
      "Could not remove button": "Не удалось удалить кнопку",
      "Could not update channel setting": "Не удалось изменить настройку канала",
      "Could not update recording cue": "Не удалось изменить индикатор записи",
      "Could not update haptic feedback": "Не удалось изменить вибрацию",
      "Could not update diagnostics setting": "Не удалось изменить отправку диагностики",
      "Could not update game": "Не удалось изменить режим",
      "Could not update model size": "Не удалось изменить модель",
      "Could not update binding": "Не удалось изменить сочетание кнопок",
      "Could not update language": "Не удалось изменить язык",
      "L1 Bumper": "L1 (бампер)",
      "R1 Bumper": "R1 (бампер)",
      "L2 Trigger": "L2 (курок)",
      "R2 Trigger": "R2 (курок)",
      "L4 Grip": "L4 (задняя кнопка)",
      "R4 Grip": "R4 (задняя кнопка)",
      "L5 Grip": "L5 (задняя кнопка)",
      "R5 Grip": "R5 (задняя кнопка)",
      "Waiting for input": "Ожидание ввода",
      "Status unavailable": "Состояние недоступно",
      "Backend status request failed": "Не удалось запросить состояние службы",
      "Could not update language setting": "Не удалось изменить язык диктовки",
      Interface: Interface$7,
      Mode: Mode$7,
      "Review transcription": "Проверить расшифровку",
      "Transcription sending": "Отправка расшифровки",
      "Send immediately": "Отправить сразу",
      "Review before sending": "Проверить перед отправкой",
      "Send after countdown": "Отправить после отсчёта",
      "Press Enter yourself": "Нажать Enter самостоятельно",
      "Type into chat without submitting": "Ввести в чат без отправки",
      Send: Send$7,
      Cancel: Cancel$7,
      "Type into chat": "Ввести в чат",
      "Review confirmation": "Подтверждение проверки",
      "After typing, press Enter in the game": "После ввода нажмите Enter в игре",
      "Open Decktation to retry": "Откройте Decktation, чтобы повторить попытку",
      "Could not approve draft": "Не удалось подтвердить черновик",
      "Could not cancel draft": "Не удалось отменить черновик",
      "Could not update sending mode": "Не удалось изменить режим отправки",
      "Transcription. Use Up and Down to scroll.": "Расшифровка. Используйте кнопки вверх и вниз для прокрутки.",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "Закрывает это меню перед вводом в игру. Оставьте игру на переднем плане.",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "Текст остаётся видимым до вашего решения. Нажмите {binding}, чтобы отправить; удерживайте для отмены. Откройте Decktation для проверки длинного текста.",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — откройте Decktation, чтобы проверить, отправить или отменить",
      "Typing transcription…": "Ввод расшифровки…",
      "Open Decktation to retry typing": "Откройте Decktation для повторного ввода",
      "Open Decktation to review and send": "Откройте Decktation для проверки и отправки",
      "Open Decktation to review all": "Откройте Decktation для проверки всего текста",
      "Close Steam menus and return to your game": "Закройте меню Steam и вернитесь в игру",
      "Open Decktation to confirm sending": "Откройте Decktation для подтверждения отправки",
      "Update available": "Доступно обновление",
      "Preparing update...": "Подготовка обновления...",
      "Waiting for Decky confirmation...": "Ожидание подтверждения Decky...",
      "Update to {version}": "Обновить до {version}",
      Updates: Updates$7,
      "Version {version}": "Версия {version}",
      "Update available: {version}": "Доступно обновление: {version}",
      "Up to date": "Последняя версия",
      "Checking for updates...": "Проверка обновлений...",
      "Check again": "Проверить снова",
      "Check for updates": "Проверить обновления",
      "Decktation update available": "Доступно обновление Decktation",
      "Could not check for updates.": "Не удалось проверить обновления.",
      "The update could not be verified, so it was not installed.": "Не удалось проверить обновление, поэтому оно не было установлено.",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "Установщик плагинов Decky недоступен в этой версии. Обновите вручную с помощью ZIP-архива Decktation.",
      "An update is already being prepared.": "Обновление уже подготавливается.",
      "Wait for the transcription model to finish loading.": "Дождитесь завершения загрузки модели распознавания речи.",
      "Finish the current dictation before updating.": "Завершите текущее диктование перед обновлением.",
      "Binding saved: {binding}": "Сочетание сохранено: {binding}",
      "Binding cancelled. Your previous binding is unchanged.": "Изменение отменено. Предыдущее сочетание сохранено.",
      "Could not start binding capture": "Не удалось начать захват сочетания",
      "Release all buttons to start listening.": "Отпустите все кнопки, чтобы начать захват.",
      "Hold your new combination together. Release to save.": "Удерживайте новое сочетание. Отпустите, чтобы сохранить.",
      "Detected:": "Обнаружено:",
      "Listening…": "Ожидание…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "От одной до пяти кнопок. Steam и быстрый доступ исключены. Захват завершается через 20 секунд.",
      "Cancel (touch)": "Отмена (касанием)",
      "Change binding": "Изменить сочетание",
      "Spoken punctuation": "Голосовая пунктуация",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "При английском языке или автоопределении произнесите comma, period или question mark для вставки знаков препинания. Отключите, чтобы вводить эти слова буквально.",
      "Could not set spoken punctuation": "Не удалось настроить голосовую пунктуацию",
      "Microphone troubleshooting": "Устранение проблем с микрофоном",
      "Microphone guide. Use Up and Down to scroll.": "Руководство по микрофону. Прокручивайте кнопками Вверх и Вниз.",
      "Start with a dictation test": "Начните с проверки диктовки",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "Включите Decktation, дождитесь статуса «Готово» и запустите проверку диктовки (3 с) на главной странице. Говорите чётко. Результат останется в панели и не будет введён в игру.",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "Проверьте встроенный микрофон или гарнитуру в другом приложении. Если в Steam звук чистый, но диктовка не работает, проверьте устройство записи по умолчанию в системе.",
      "If audio crackles, pops, or cuts out": "Если звук трещит, щёлкает или прерывается",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "Пользователь Steam Deck LCD сообщил об улучшении после отключения обработки голоса Steam. Это совет сообщества без гарантии результата. Его влияние на аудиовход Decktation не установлено.",
      "Open Steam → Power → Switch to Desktop.": "Откройте Steam → Питание → Перейти на рабочий стол.",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "В Steam откройте «Друзья и чат» → шестерёнка → «Голос». В некоторых версиях также есть Steam → Настройки → Голос.",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "Выберите устройство голосового ввода. Запустите проверку микрофона, говорите, прислушайтесь к треску или пропущенным словам и остановите проверку.",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "Запишите текущие настройки. В дополнительных настройках попробуйте отключить шумоподавление, эхоподавление и автоматическую регулировку громкости или усиления.",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "Повторите проверку микрофона. Если стало лучше, включайте параметры по одному, чтобы определить полезную настройку.",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "Вернитесь в игровой режим и повторите трёхсекундную проверку диктовки Decktation перед проверкой в игре.",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "Если это не помогает, восстановите прежние настройки. Отключение обработки может усилить фоновый шум или эхо динамиков и повлиять на голосовой чат Steam.",
      "If the problem persists": "Если проблема остаётся",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "При сообщении о проблеме укажите модель Deck (LCD или OLED), версии SteamOS и клиента Steam, микрофон или гарнитуру, а также сохраняется ли улучшение в игровом режиме и после перезагрузки. Проверьте последний журнал плагина на ошибки.",
      "Open full guide online": "Открыть полное руководство онлайн",
      "Microphone help": "Помощь с микрофоном",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "Голос не распознаётся, пропадают слова или трещит звук? Прочтите руководство по микрофону.",
      "Having problems with your microphone?": "Проблемы с микрофоном?",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "Отправляет в Sentry ошибки без конфиденциальных данных, счётчики использования и показатели производительности, включая движок распознавания и общие сведения об устройстве и ОС. Аудио и расшифровки остаются на устройстве.",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "Скажите command gg для ввода /gg или command ready для /ready. Используйте английский язык или автоопределение. Команды учитывают настройки отправки.",
      "Binding timed out. Your previous binding is unchanged.": "Время истекло. Предыдущее сочетание сохранено.",
      "Controller disconnected. Your previous binding is unchanged.": "Контроллер отключён. Предыдущее сочетание сохранено.",
      "Use at most five buttons.": "Используйте не более пяти кнопок.",
      "Finish recording before changing the binding.": "Завершите запись перед изменением сочетания.",
      "Controller listener unavailable.": "Служба ввода контроллера недоступна.",
      "Binding session ended.": "Сеанс настройки сочетания завершён."
    };

    var Back$6 = "Voltar";
    var Enable$6 = "Ativar";
    var Language$6 = "Idioma do ditado";
    var Binding$6 = "Combinação";
    var Result$6 = "Resultado";
    var Model$6 = "Modelo";
    var Sending$6 = "Envio";
    var Confirm$6 = "Confirmar";
    var Manual$6 = "Envio manual";
    var Feedback$6 = "Indicadores";
    var Toast$6 = "Notificação";
    var Overlay$6 = "Indicador na tela";
    var None$6 = "Nenhum";
    var Diagnostics$6 = "Diagnóstico";
    var Controller$6 = "Controle";
    var Yes$6 = "Sim";
    var No$6 = "Não";
    var Backend$6 = "Serviço do plugin";
    var Ready$6 = "Pronto";
    var Unavailable$6 = "Indisponível";
    var Loading$6 = "Carregando";
    var Share$6 = "Compartilhar";
    var Permissions$6 = "Permissões";
    var Recording$6 = "Gravação";
    var Generic$6 = "Entrada de texto geral";
    var Interface$6 = "Interface";
    var Mode$6 = "Modo";
    var Send$6 = "Enviar";
    var Cancel$6 = "Cancelar";
    var Updates$6 = "Atualizações";
    var pt = {
      Back: Back$6,
      Enable: Enable$6,
      "Quick settings": "Configurações rápidas",
      Language: Language$6,
      Binding: Binding$6,
      "Edit Bindings": "Editar botões",
      "Try it": "Experimentar o ditado",
      "Recording...": "Gravando…",
      "Transcribing...": "Transcrevendo…",
      "Test Dictation (3s)": "Testar ditado (3 s)",
      "Shows a transcription here without sending text to your game.": "Mostra a transcrição aqui sem enviar texto ao jogo.",
      Result: Result$6,
      "No speech detected": "Nenhuma fala detectada",
      "Advanced settings": "Configurações avançadas",
      "Transcription model": "Modelo de transcrição",
      Model: Model$6,
      "Recording binding": "Botões de gravação",
      Sending: Sending$6,
      Confirm: Confirm$6,
      "Delay before send": "Aguardar antes de enviar",
      Manual: Manual$6,
      "You press Enter": "Pressione Enter para enviar",
      "Remember channel": "Lembrar canal",
      "Reuse the last spoken channel": "Reutilizar o último canal mencionado",
      Feedback: Feedback$6,
      "Recording cue": "Indicador de gravação",
      Toast: Toast$6,
      Overlay: Overlay$6,
      None: None$6,
      "Haptic feedback": "Vibração",
      "Cues on the controller when recording starts and stops": "Vibração ao iniciar e terminar a gravação",
      Diagnostics: Diagnostics$6,
      "Help & permissions": "Ajuda e permissões",
      "Input and service": "Entrada e serviço",
      Controller: Controller$6,
      "Binding supported": "Combinação compatível",
      Yes: Yes$6,
      No: No$6,
      "Held buttons": "Botões pressionados",
      "Keyboard helper": "Serviço de teclado",
      Backend: Backend$6,
      Ready: Ready$6,
      Unavailable: Unavailable$6,
      Loading: Loading$6,
      "Diagnostics sharing": "Compartilhar diagnóstico",
      Share: Share$6,
      "Optional scrubbed diagnostics sent to Sentry": "Envio opcional de dados de diagnóstico filtrados ao Sentry",
      "How to use": "Como usar",
      Permissions: Permissions$6,
      "Auto Detect": "Detecção automática",
      "Popular Steam languages": "Idiomas comuns no Steam",
      "Other languages": "Outros idiomas",
      "Add Button": "Adicionar botão",
      "Button {number}": "Botão {number}",
      "Remove button {number}": "Remover botão {number}",
      "Hold {binding} to record": "Segure {binding} para gravar",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "Segure {binding} {together}para gravar. Solte para transcrever e inserir o texto no jogo ou aplicativo ativo. Mantenha-o em primeiro plano.",
      "together ": "ao mesmo tempo ",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktation usa o acesso root do Decky para ler os botões do controle e gerar entradas de teclado para o texto ditado. A transcrição é enviada como texto, nunca como um comando de terminal.",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Base é o mais rápido. Small equilibra velocidade e precisão. Medium é mais preciso, mas mais lento e pode ser baixado no primeiro uso.",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cpp usa a GPU via Vulkan.",
      "whisper.cpp runs on the CPU.": "whisper.cpp usa a CPU.",
      "Connecting to Decktation...": "Conectando ao Decktation…",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "Serviço de teclado indisponível. Recarregue ou reinstale o Decktation.",
      "Loading transcription model...": "Carregando o modelo de transcrição…",
      "Decktation is off": "Decktation está desativado",
      "Model not ready": "O modelo não está pronto",
      "Controller unavailable": "Controle indisponível",
      "Backend unavailable: {error}": "Serviço indisponível: {error}",
      "Recording for 3 seconds...": "Gravando por 3 segundos…",
      Recording: Recording$6,
      "Sending in {seconds}s": "Envio em {seconds} s",
      "\"{text}\" — hold PTT to cancel": "“{text}” — segure os botões de gravação para cancelar",
      "Interface language": "Idioma da interface",
      "Automatic (system)": "Automático (Steam)",
      "Only changes the menu language, not the dictation language.": "Altera apenas o idioma dos menus, não o do ditado.",
      Generic: Generic$6,
      "Base · Fast": "Base · Rápido",
      "Small · Balanced": "Small · Equilibrado",
      "Medium · More accurate": "Medium · Mais preciso",
      "Could not start test recording": "Não foi possível iniciar o teste",
      "Could not transcribe test recording": "Não foi possível transcrever o teste",
      "Could not read test transcription": "Não foi possível ler o resultado do teste",
      "Could not update enabled state": "Não foi possível ativar ou desativar o Decktation",
      "Could not load Whisper model": "Não foi possível carregar o modelo Whisper",
      "Could not remove button": "Não foi possível remover o botão",
      "Could not update channel setting": "Não foi possível alterar o canal",
      "Could not update recording cue": "Não foi possível alterar o indicador de gravação",
      "Could not update haptic feedback": "Não foi possível alterar a vibração",
      "Could not update diagnostics setting": "Não foi possível alterar o compartilhamento de diagnóstico",
      "Could not update game": "Não foi possível alterar o modo",
      "Could not update model size": "Não foi possível alterar o modelo",
      "Could not update binding": "Não foi possível alterar a combinação de botões",
      "Could not update language": "Não foi possível alterar o idioma",
      "L1 Bumper": "L1 (botão superior)",
      "R1 Bumper": "R1 (botão superior)",
      "L2 Trigger": "L2 (gatilho)",
      "R2 Trigger": "R2 (gatilho)",
      "L4 Grip": "L4 (botão traseiro)",
      "R4 Grip": "R4 (botão traseiro)",
      "L5 Grip": "L5 (botão traseiro)",
      "R5 Grip": "R5 (botão traseiro)",
      "Waiting for input": "Aguardando entrada",
      "Status unavailable": "Estado indisponível",
      "Backend status request failed": "Não foi possível consultar o serviço",
      "Could not update language setting": "Não foi possível alterar o idioma do ditado",
      Interface: Interface$6,
      Mode: Mode$6,
      "Review transcription": "Rever transcrição",
      "Transcription sending": "Envio da transcrição",
      "Send immediately": "Enviar imediatamente",
      "Review before sending": "Rever antes de enviar",
      "Send after countdown": "Enviar após a contagem decrescente",
      "Press Enter yourself": "Premir Enter manualmente",
      "Type into chat without submitting": "Escrever no chat sem enviar",
      Send: Send$6,
      Cancel: Cancel$6,
      "Type into chat": "Escrever no chat",
      "Review confirmation": "Confirmação da revisão",
      "After typing, press Enter in the game": "Depois de escrever, prime Enter no jogo",
      "Open Decktation to retry": "Abre Decktation para tentar novamente",
      "Could not approve draft": "Não foi possível aprovar o rascunho",
      "Could not cancel draft": "Não foi possível cancelar o rascunho",
      "Could not update sending mode": "Não foi possível alterar o modo de envio",
      "Transcription. Use Up and Down to scroll.": "Transcrição. Usa Cima e Baixo para percorrer.",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "Fecha este menu antes de escrever no jogo. Mantém o jogo em primeiro plano.",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "A revisão fica visível até decidires. Prime {binding} para enviar; mantém premido para cancelar. Abre Decktation para rever textos longos.",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — abre Decktation para rever, enviar ou cancelar",
      "Typing transcription…": "A escrever a transcrição…",
      "Open Decktation to retry typing": "Abre Decktation para tentar escrever novamente",
      "Open Decktation to review and send": "Abre Decktation para rever e enviar",
      "Open Decktation to review all": "Abre Decktation para rever tudo",
      "Close Steam menus and return to your game": "Fecha os menus do Steam e volta ao jogo",
      "Open Decktation to confirm sending": "Abre Decktation para confirmar o envio",
      "Update available": "Atualização disponível",
      "Preparing update...": "Preparando atualização...",
      "Waiting for Decky confirmation...": "Aguardando confirmação do Decky...",
      "Update to {version}": "Atualizar para {version}",
      Updates: Updates$6,
      "Version {version}": "Versão {version}",
      "Update available: {version}": "Atualização disponível: {version}",
      "Up to date": "Atualizado",
      "Checking for updates...": "Verificando atualizações...",
      "Check again": "Verificar novamente",
      "Check for updates": "Verificar atualizações",
      "Decktation update available": "Atualização do Decktation disponível",
      "Could not check for updates.": "Não foi possível verificar atualizações.",
      "The update could not be verified, so it was not installed.": "Não foi possível verificar a atualização, por isso não foi instalada.",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "O instalador de plugins do Decky não está disponível nesta versão. Atualize manualmente com o arquivo ZIP do Decktation.",
      "An update is already being prepared.": "Uma atualização já está sendo preparada.",
      "Wait for the transcription model to finish loading.": "Aguarde o carregamento do modelo de transcrição terminar.",
      "Finish the current dictation before updating.": "Conclua o ditado atual antes de atualizar.",
      "Binding saved: {binding}": "Atalho guardado: {binding}",
      "Binding cancelled. Your previous binding is unchanged.": "Alteração cancelada. O atalho anterior mantém-se.",
      "Could not start binding capture": "Não foi possível iniciar a captura do atalho",
      "Release all buttons to start listening.": "Solta todos os botões para iniciar a captura.",
      "Hold your new combination together. Release to save.": "Mantém a nova combinação premida. Solta para guardar.",
      "Detected:": "Detetado:",
      "Listening…": "À espera…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "Um a cinco botões. Steam e Acesso rápido estão excluídos. A captura termina após 20 segundos.",
      "Cancel (touch)": "Cancelar (tocar)",
      "Change binding": "Alterar atalho",
      "Spoken punctuation": "Pontuação falada",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "Com inglês ou deteção automática, diz comma, period ou question mark para inserir pontuação. Desativa para escrever estas palavras literalmente.",
      "Could not set spoken punctuation": "Não foi possível definir a pontuação falada",
      "Microphone troubleshooting": "Resolver problemas do microfone",
      "Microphone guide. Use Up and Down to scroll.": "Guia do microfone. Usa Cima e Baixo para percorrer.",
      "Start with a dictation test": "Começa com um teste de ditado",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "Ativa o Decktation, espera por Pronto e executa Testar ditado (3 s) na página principal. Fala com clareza. O resultado fica no painel e não é escrito no jogo.",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "Verifica se o microfone integrado ou os auscultadores funcionam noutra aplicação. Se o som no Steam for claro mas o ditado falhar, verifica o dispositivo de gravação predefinido do sistema.",
      "If audio crackles, pops, or cuts out": "Se o áudio estalar, crepitar ou falhar",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "Um utilizador de Steam Deck LCD relatou melhorias após desativar o processamento de voz do Steam. É uma solução da comunidade, sem garantia. O seu efeito na entrada de áudio do Decktation não foi estabelecido.",
      "Open Steam → Power → Switch to Desktop.": "Abre Steam → Energia → Mudar para o ambiente de trabalho.",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "No Steam, abre Amigos e chat → engrenagem → Voz. Algumas versões também têm Steam → Definições → Voz.",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "Seleciona o dispositivo de entrada de voz. Inicia o teste do microfone, fala, ouve se há estalos ou palavras em falta e termina o teste.",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "Anota as definições atuais. Nas definições avançadas, tenta desativar a redução de ruído, o cancelamento de eco e o controlo automático de volume ou ganho.",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "Repete o teste do microfone. Se melhorar, reativa as opções uma a uma para identificar a definição que ajuda.",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "Volta ao modo de jogo e repete o teste de ditado de três segundos do Decktation antes de experimentar num jogo.",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "Repõe as definições anteriores se não ajudar. Desativar o processamento pode aumentar o ruído de fundo ou o eco dos altifalantes e afetar o chat de voz do Steam.",
      "If the problem persists": "Se o problema persistir",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "Ao comunicar o problema, inclui o modelo da Deck (LCD ou OLED), as versões do SteamOS e do cliente Steam, o microfone ou auscultadores e se a melhoria se mantém no modo de jogo e após reiniciar. Procura erros no registo mais recente do plugin.",
      "Open full guide online": "Abrir o guia completo online",
      "Microphone help": "Ajuda do microfone",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "Voz não reconhecida, palavras em falta ou áudio a estalar? Lê aqui o guia do microfone.",
      "Having problems with your microphone?": "Problemas com o microfone?",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "Envia ao Sentry erros sem dados sensíveis, contagens de utilização e métricas de desempenho, incluindo o motor de inferência e informações gerais do dispositivo e sistema. O áudio e as transcrições permanecem locais.",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "Diz command gg para inserir /gg, ou command ready para /ready. Usa inglês ou deteção automática. Os comandos respeitam as definições de envio.",
      "Binding timed out. Your previous binding is unchanged.": "O tempo terminou. O atalho anterior mantém-se.",
      "Controller disconnected. Your previous binding is unchanged.": "Comando desligado. O atalho anterior mantém-se.",
      "Use at most five buttons.": "Usa no máximo cinco botões.",
      "Finish recording before changing the binding.": "Termina a gravação antes de alterar o atalho.",
      "Controller listener unavailable.": "O serviço de deteção de comandos está indisponível.",
      "Binding session ended.": "A sessão de configuração do atalho terminou."
    };

    var Back$5 = "Wstecz";
    var Enable$5 = "Włącz";
    var Language$5 = "Język dyktowania";
    var Binding$5 = "Kombinacja";
    var Result$5 = "Wynik";
    var Model$5 = "Model";
    var Sending$5 = "Wysyłanie";
    var Confirm$5 = "Potwierdzanie";
    var Manual$5 = "Wysyłanie ręczne";
    var Feedback$5 = "Wskaźniki";
    var Toast$5 = "Powiadomienie";
    var Overlay$5 = "Wskaźnik na ekranie";
    var None$5 = "Brak";
    var Diagnostics$5 = "Diagnostyka";
    var Controller$5 = "Kontroler";
    var Yes$5 = "Tak";
    var No$5 = "Nie";
    var Backend$5 = "Usługa wtyczki";
    var Ready$5 = "Gotowe";
    var Unavailable$5 = "Niedostępne";
    var Loading$5 = "Ładowanie";
    var Share$5 = "Udostępniaj";
    var Permissions$5 = "Uprawnienia";
    var Recording$5 = "Nagrywanie";
    var Generic$5 = "Ogólne wprowadzanie tekstu";
    var Interface$5 = "Interfejs";
    var Mode$5 = "Tryb";
    var Send$5 = "Wyślij";
    var Cancel$5 = "Anuluj";
    var Updates$5 = "Aktualizacje";
    var pl = {
      Back: Back$5,
      Enable: Enable$5,
      "Quick settings": "Szybkie ustawienia",
      Language: Language$5,
      Binding: Binding$5,
      "Edit Bindings": "Edytuj przyciski",
      "Try it": "Wypróbuj dyktowanie",
      "Recording...": "Nagrywanie…",
      "Transcribing...": "Transkrypcja…",
      "Test Dictation (3s)": "Test dyktowania (3 s)",
      "Shows a transcription here without sending text to your game.": "Wyświetla tekst tutaj, bez wysyłania go do gry.",
      Result: Result$5,
      "No speech detected": "Nie wykryto mowy",
      "Advanced settings": "Ustawienia zaawansowane",
      "Transcription model": "Model transkrypcji",
      Model: Model$5,
      "Recording binding": "Przyciski nagrywania",
      Sending: Sending$5,
      Confirm: Confirm$5,
      "Delay before send": "Opóźnienie przed wysłaniem",
      Manual: Manual$5,
      "You press Enter": "Naciśnij Enter, aby wysłać",
      "Remember channel": "Zapamiętaj kanał",
      "Reuse the last spoken channel": "Używaj ostatnio wskazanego kanału",
      Feedback: Feedback$5,
      "Recording cue": "Wskaźnik nagrywania",
      Toast: Toast$5,
      Overlay: Overlay$5,
      None: None$5,
      "Haptic feedback": "Wibracje",
      "Cues on the controller when recording starts and stops": "Wibracje na początku i końcu nagrywania",
      Diagnostics: Diagnostics$5,
      "Help & permissions": "Pomoc i uprawnienia",
      "Input and service": "Wejście i usługa",
      Controller: Controller$5,
      "Binding supported": "Obsługiwana kombinacja",
      Yes: Yes$5,
      No: No$5,
      "Held buttons": "Wciśnięte przyciski",
      "Keyboard helper": "Usługa klawiatury",
      Backend: Backend$5,
      Ready: Ready$5,
      Unavailable: Unavailable$5,
      Loading: Loading$5,
      "Diagnostics sharing": "Udostępnianie diagnostyki",
      Share: Share$5,
      "Optional scrubbed diagnostics sent to Sentry": "Opcjonalne wysyłanie przefiltrowanych danych diagnostycznych do Sentry",
      "How to use": "Jak używać",
      Permissions: Permissions$5,
      "Auto Detect": "Wykryj automatycznie",
      "Popular Steam languages": "Popularne języki Steam",
      "Other languages": "Pozostałe języki",
      "Add Button": "Dodaj przycisk",
      "Button {number}": "Przycisk {number}",
      "Remove button {number}": "Usuń przycisk {number}",
      "Hold {binding} to record": "Przytrzymaj {binding}, aby nagrywać",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "Przytrzymaj {binding} {together}, aby nagrywać. Puść, aby przepisać mowę i wprowadzić tekst do aktywnej gry lub aplikacji. Musi ona pozostać na pierwszym planie.",
      "together ": "jednocześnie",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktation używa dostępu root Decky do odczytu przycisków kontrolera i generowania zdarzeń klawiatury dla dyktowanego tekstu. Transkrypcja jest przekazywana jako tekst, nigdy jako polecenie powłoki.",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Base jest najszybszy. Small równoważy szybkość i dokładność. Medium jest dokładniejszy, ale wolniejszy i może zostać pobrany przy pierwszym użyciu.",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cpp korzysta z GPU przez Vulkan.",
      "whisper.cpp runs on the CPU.": "whisper.cpp korzysta z CPU.",
      "Connecting to Decktation...": "Łączenie z Decktation…",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "Usługa klawiatury jest niedostępna. Przeładuj lub zainstaluj ponownie Decktation.",
      "Loading transcription model...": "Ładowanie modelu transkrypcji…",
      "Decktation is off": "Decktation jest wyłączony",
      "Model not ready": "Model nie jest gotowy",
      "Controller unavailable": "Kontroler jest niedostępny",
      "Backend unavailable: {error}": "Usługa niedostępna: {error}",
      "Recording for 3 seconds...": "Nagrywanie przez 3 sekundy…",
      Recording: Recording$5,
      "Sending in {seconds}s": "Wysyłanie za {seconds} s",
      "\"{text}\" — hold PTT to cancel": "„{text}” — przytrzymaj przyciski nagrywania, aby anulować",
      "Interface language": "Język interfejsu",
      "Automatic (system)": "Automatycznie (Steam)",
      "Only changes the menu language, not the dictation language.": "Zmienia tylko język menu, nie język dyktowania.",
      Generic: Generic$5,
      "Base · Fast": "Base · Szybki",
      "Small · Balanced": "Small · Zrównoważony",
      "Medium · More accurate": "Medium · Dokładniejszy",
      "Could not start test recording": "Nie można rozpocząć testu",
      "Could not transcribe test recording": "Nie można wykonać transkrypcji testu",
      "Could not read test transcription": "Nie można odczytać wyniku testu",
      "Could not update enabled state": "Nie można włączyć lub wyłączyć Decktation",
      "Could not load Whisper model": "Nie można załadować modelu Whisper",
      "Could not remove button": "Nie można usunąć przycisku",
      "Could not update channel setting": "Nie można zmienić ustawienia kanału",
      "Could not update recording cue": "Nie można zmienić wskaźnika nagrywania",
      "Could not update haptic feedback": "Nie można zmienić wibracji",
      "Could not update diagnostics setting": "Nie można zmienić ustawienia diagnostyki",
      "Could not update game": "Nie można zmienić trybu",
      "Could not update model size": "Nie można zmienić modelu",
      "Could not update binding": "Nie można zmienić kombinacji przycisków",
      "Could not update language": "Nie można zmienić języka",
      "L1 Bumper": "L1 (przycisk górny)",
      "R1 Bumper": "R1 (przycisk górny)",
      "L2 Trigger": "L2 (spust)",
      "R2 Trigger": "R2 (spust)",
      "L4 Grip": "L4 (przycisk tylny)",
      "R4 Grip": "R4 (przycisk tylny)",
      "L5 Grip": "L5 (przycisk tylny)",
      "R5 Grip": "R5 (przycisk tylny)",
      "Waiting for input": "Oczekiwanie na wejście",
      "Status unavailable": "Stan niedostępny",
      "Backend status request failed": "Nie można odczytać stanu usługi",
      "Could not update language setting": "Nie można zmienić języka dyktowania",
      Interface: Interface$5,
      Mode: Mode$5,
      "Review transcription": "Sprawdź transkrypcję",
      "Transcription sending": "Wysyłanie transkrypcji",
      "Send immediately": "Wyślij od razu",
      "Review before sending": "Sprawdź przed wysłaniem",
      "Send after countdown": "Wyślij po odliczaniu",
      "Press Enter yourself": "Naciśnij Enter samodzielnie",
      "Type into chat without submitting": "Wpisz na czacie bez wysyłania",
      Send: Send$5,
      Cancel: Cancel$5,
      "Type into chat": "Wpisz na czacie",
      "Review confirmation": "Potwierdzenie przeglądu",
      "After typing, press Enter in the game": "Po wpisaniu tekstu naciśnij Enter w grze",
      "Open Decktation to retry": "Otwórz Decktation, aby spróbować ponownie",
      "Could not approve draft": "Nie udało się zatwierdzić wersji roboczej",
      "Could not cancel draft": "Nie udało się anulować wersji roboczej",
      "Could not update sending mode": "Nie udało się zmienić trybu wysyłania",
      "Transcription. Use Up and Down to scroll.": "Transkrypcja. Użyj przycisków w górę i w dół, aby przewijać.",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "Zamyka to menu przed wpisaniem tekstu w grze. Pozostaw grę na pierwszym planie.",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "Podgląd pozostaje widoczny do podjęcia decyzji. Naciśnij {binding}, aby wysłać; przytrzymaj, aby anulować. Otwórz Decktation, aby sprawdzić dłuższy tekst.",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — otwórz Decktation, aby sprawdzić, wysłać lub anulować",
      "Typing transcription…": "Wpisywanie transkrypcji…",
      "Open Decktation to retry typing": "Otwórz Decktation, aby ponowić wpisywanie",
      "Open Decktation to review and send": "Otwórz Decktation, aby sprawdzić i wysłać",
      "Open Decktation to review all": "Otwórz Decktation, aby sprawdzić całość",
      "Close Steam menus and return to your game": "Zamknij menu Steam i wróć do gry",
      "Open Decktation to confirm sending": "Otwórz Decktation, aby potwierdzić wysłanie",
      "Update available": "Dostępna aktualizacja",
      "Preparing update...": "Przygotowywanie aktualizacji...",
      "Waiting for Decky confirmation...": "Oczekiwanie na potwierdzenie Decky...",
      "Update to {version}": "Aktualizuj do {version}",
      Updates: Updates$5,
      "Version {version}": "Wersja {version}",
      "Update available: {version}": "Dostępna aktualizacja: {version}",
      "Up to date": "Aktualna wersja",
      "Checking for updates...": "Sprawdzanie aktualizacji...",
      "Check again": "Sprawdź ponownie",
      "Check for updates": "Sprawdź aktualizacje",
      "Decktation update available": "Dostępna aktualizacja Decktation",
      "Could not check for updates.": "Nie udało się sprawdzić aktualizacji.",
      "The update could not be verified, so it was not installed.": "Nie udało się zweryfikować aktualizacji, więc nie została zainstalowana.",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "Instalator wtyczek Decky jest niedostępny w tej wersji. Zaktualizuj ręcznie za pomocą pliku ZIP Decktation.",
      "An update is already being prepared.": "Aktualizacja jest już przygotowywana.",
      "Wait for the transcription model to finish loading.": "Poczekaj na zakończenie ładowania modelu transkrypcji.",
      "Finish the current dictation before updating.": "Zakończ bieżące dyktowanie przed aktualizacją.",
      "Binding saved: {binding}": "Zapisano skrót: {binding}",
      "Binding cancelled. Your previous binding is unchanged.": "Anulowano zmianę. Poprzedni skrót pozostaje bez zmian.",
      "Could not start binding capture": "Nie udało się rozpocząć przechwytywania skrótu",
      "Release all buttons to start listening.": "Zwolnij wszystkie przyciski, aby rozpocząć przechwytywanie.",
      "Hold your new combination together. Release to save.": "Przytrzymaj nową kombinację. Zwolnij, aby zapisać.",
      "Detected:": "Wykryto:",
      "Listening…": "Oczekiwanie…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "Od jednego do pięciu przycisków. Steam i Szybki dostęp są wykluczone. Przechwytywanie kończy się po 20 sekundach.",
      "Cancel (touch)": "Anuluj (dotknij)",
      "Change binding": "Zmień skrót",
      "Spoken punctuation": "Dyktowana interpunkcja",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "Przy języku angielskim lub automatycznym wykrywaniu powiedz comma, period lub question mark, aby wstawić znak interpunkcyjny. Wyłącz, aby wpisywać te słowa dosłownie.",
      "Could not set spoken punctuation": "Nie udało się ustawić dyktowanej interpunkcji",
      "Microphone troubleshooting": "Rozwiązywanie problemów z mikrofonem",
      "Microphone guide. Use Up and Down to scroll.": "Poradnik mikrofonu. Przewijaj przyciskami Góra i Dół.",
      "Start with a dictation test": "Zacznij od testu dyktowania",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "Włącz Decktation, poczekaj na Gotowe i uruchom Test dyktowania (3 s) na stronie głównej. Mów wyraźnie. Wynik pozostaje w panelu i nie jest wpisywany do gry.",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "Sprawdź, czy wbudowany mikrofon lub zestaw słuchawkowy działa w innej aplikacji. Jeśli w Steam dźwięk jest wyraźny, ale dyktowanie nie działa, sprawdź domyślne urządzenie nagrywające systemu.",
      "If audio crackles, pops, or cuts out": "Gdy dźwięk trzeszczy, strzela lub zanika",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "Użytkownik Steam Deck LCD zgłosił poprawę po wyłączeniu przetwarzania głosu w Steam. To wskazówka społeczności, a nie gwarantowane rozwiązanie. Nie ustalono jej wpływu na wejście audio Decktation.",
      "Open Steam → Power → Switch to Desktop.": "Otwórz Steam → Zasilanie → Przełącz na pulpit.",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "W Steam otwórz Znajomi i czat → koło zębate → Głos. Niektóre wersje mają też Steam → Ustawienia → Głos.",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "Wybierz urządzenie wejścia głosowego. Uruchom test mikrofonu, mów i sprawdź, czy słychać trzaski lub brakuje słów, a następnie zatrzymaj test.",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "Zanotuj bieżące ustawienia. W ustawieniach zaawansowanych spróbuj wyłączyć redukcję szumów, usuwanie echa i automatyczną regulację głośności lub wzmocnienia.",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "Powtórz test mikrofonu. Jeśli jest lepiej, włączaj opcje pojedynczo, aby znaleźć pomocne ustawienie.",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "Wróć do trybu gry i powtórz trzysekundowy test dyktowania Decktation przed próbą w grze.",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "Przywróć poprzednie ustawienia, jeśli to nie pomaga. Wyłączenie przetwarzania może zwiększyć szum tła lub echo głośników i wpłynąć na czat głosowy Steam.",
      "If the problem persists": "Jeśli problem nadal występuje",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "Zgłaszając problem, podaj model Decka (LCD lub OLED), wersje SteamOS i klienta Steam, mikrofon lub zestaw słuchawkowy oraz czy poprawa utrzymuje się w trybie gry i po ponownym uruchomieniu. Sprawdź błędy w najnowszym dzienniku wtyczki.",
      "Open full guide online": "Otwórz pełny poradnik online",
      "Microphone help": "Pomoc dotycząca mikrofonu",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "Głos nierozpoznawany, brakujące słowa lub trzaski? Przeczytaj poradnik mikrofonu.",
      "Having problems with your microphone?": "Problemy z mikrofonem?",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "Wysyła do Sentry błędy oczyszczone z danych wrażliwych, liczniki użycia i pomiary wydajności, w tym silnik inferencji oraz ogólne informacje o urządzeniu i systemie. Audio i transkrypcje pozostają lokalnie.",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "Powiedz command gg, aby wpisać /gg, lub command ready dla /ready. Użyj angielskiego lub automatycznego wykrywania. Polecenia respektują ustawienia wysyłania.",
      "Binding timed out. Your previous binding is unchanged.": "Upłynął limit czasu. Poprzedni skrót pozostaje bez zmian.",
      "Controller disconnected. Your previous binding is unchanged.": "Kontroler został odłączony. Poprzedni skrót pozostaje bez zmian.",
      "Use at most five buttons.": "Użyj najwyżej pięciu przycisków.",
      "Finish recording before changing the binding.": "Zakończ nagrywanie przed zmianą skrótu.",
      "Controller listener unavailable.": "Usługa wykrywania kontrolerów jest niedostępna.",
      "Binding session ended.": "Sesja przypisywania skrótu została zakończona."
    };

    var Back$4 = "뒤로";
    var Enable$4 = "사용";
    var Language$4 = "받아쓰기 언어";
    var Binding$4 = "버튼 조합";
    var Result$4 = "결과";
    var Model$4 = "모델";
    var Sending$4 = "전송";
    var Confirm$4 = "전송 확인";
    var Manual$4 = "수동 전송";
    var Feedback$4 = "알림";
    var Toast$4 = "알림 메시지";
    var Overlay$4 = "화면 표시";
    var None$4 = "없음";
    var Diagnostics$4 = "진단";
    var Controller$4 = "컨트롤러";
    var Yes$4 = "예";
    var No$4 = "아니요";
    var Backend$4 = "플러그인 서비스";
    var Ready$4 = "준비됨";
    var Unavailable$4 = "사용할 수 없음";
    var Loading$4 = "불러오는 중";
    var Share$4 = "공유";
    var Permissions$4 = "권한";
    var Recording$4 = "녹음";
    var Generic$4 = "일반 텍스트 입력";
    var Interface$4 = "인터페이스";
    var Mode$4 = "모드";
    var Send$4 = "전송";
    var Cancel$4 = "취소";
    var Updates$4 = "업데이트";
    var ko = {
      Back: Back$4,
      Enable: Enable$4,
      "Quick settings": "빠른 설정",
      Language: Language$4,
      Binding: Binding$4,
      "Edit Bindings": "버튼 편집",
      "Try it": "받아쓰기 테스트",
      "Recording...": "녹음 중…",
      "Transcribing...": "음성 인식 중…",
      "Test Dictation (3s)": "받아쓰기 테스트 (3초)",
      "Shows a transcription here without sending text to your game.": "인식된 텍스트를 여기에 표시하며 게임으로 전송하지 않습니다.",
      Result: Result$4,
      "No speech detected": "음성이 감지되지 않았습니다",
      "Advanced settings": "고급 설정",
      "Transcription model": "음성 인식 모델",
      Model: Model$4,
      "Recording binding": "녹음 버튼",
      Sending: Sending$4,
      Confirm: Confirm$4,
      "Delay before send": "전송 전 대기",
      Manual: Manual$4,
      "You press Enter": "Enter 키를 눌러 전송",
      "Remember channel": "채널 기억",
      "Reuse the last spoken channel": "마지막으로 말한 채널 사용",
      Feedback: Feedback$4,
      "Recording cue": "녹음 표시",
      Toast: Toast$4,
      Overlay: Overlay$4,
      None: None$4,
      "Haptic feedback": "진동 피드백",
      "Cues on the controller when recording starts and stops": "녹음을 시작하고 끝낼 때 컨트롤러 진동",
      Diagnostics: Diagnostics$4,
      "Help & permissions": "도움말 및 권한",
      "Input and service": "입력 및 서비스",
      Controller: Controller$4,
      "Binding supported": "버튼 조합 지원",
      Yes: Yes$4,
      No: No$4,
      "Held buttons": "누르고 있는 버튼",
      "Keyboard helper": "키보드 서비스",
      Backend: Backend$4,
      Ready: Ready$4,
      Unavailable: Unavailable$4,
      Loading: Loading$4,
      "Diagnostics sharing": "진단 정보 공유",
      Share: Share$4,
      "Optional scrubbed diagnostics sent to Sentry": "개인정보를 필터링한 진단 정보를 Sentry로 전송합니다 (선택 사항)",
      "How to use": "사용 방법",
      Permissions: Permissions$4,
      "Auto Detect": "자동 감지",
      "Popular Steam languages": "Steam에서 자주 쓰는 언어",
      "Other languages": "기타 언어",
      "Add Button": "버튼 추가",
      "Button {number}": "버튼 {number}",
      "Remove button {number}": "버튼 {number} 삭제",
      "Hold {binding} to record": "{binding} 버튼을 길게 눌러 녹음하세요",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "{binding} 버튼을 {together}길게 눌러 녹음하세요. 버튼을 놓으면 음성을 인식해 현재 게임이나 앱에 텍스트를 입력합니다. 해당 창을 앞에 열어 두세요.",
      "together ": "동시에 ",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktation은 컨트롤러 입력을 읽고 받아쓴 텍스트의 키보드 입력을 생성하기 위해 Decky의 root 권한을 사용합니다. 텍스트는 키보드 서비스에 데이터로 전달되며 셸 명령으로 실행되지 않습니다.",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Base는 가장 빠릅니다. Small은 속도와 정확도의 균형이 좋습니다. Medium은 더 정확하지만 느리며 처음 사용할 때 다운로드가 필요할 수 있습니다.",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cpp가 Vulkan을 통해 GPU를 사용합니다.",
      "whisper.cpp runs on the CPU.": "whisper.cpp가 CPU를 사용합니다.",
      "Connecting to Decktation...": "Decktation에 연결 중…",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "키보드 서비스를 사용할 수 없습니다. Decktation을 다시 불러오거나 재설치하세요.",
      "Loading transcription model...": "음성 인식 모델을 불러오는 중…",
      "Decktation is off": "Decktation이 꺼져 있습니다",
      "Model not ready": "모델이 준비되지 않았습니다",
      "Controller unavailable": "컨트롤러를 사용할 수 없습니다",
      "Backend unavailable: {error}": "서비스를 사용할 수 없음: {error}",
      "Recording for 3 seconds...": "3초 동안 녹음 중…",
      Recording: Recording$4,
      "Sending in {seconds}s": "{seconds}초 후 전송",
      "\"{text}\" — hold PTT to cancel": "“{text}” — 취소하려면 녹음 버튼을 길게 누르세요",
      "Interface language": "인터페이스 언어",
      "Automatic (system)": "자동 (Steam)",
      "Only changes the menu language, not the dictation language.": "메뉴 언어만 바뀌며 받아쓰기 언어는 바뀌지 않습니다.",
      Generic: Generic$4,
      "Base · Fast": "Base · 빠름",
      "Small · Balanced": "Small · 균형",
      "Medium · More accurate": "Medium · 높은 정확도",
      "Could not start test recording": "테스트 녹음을 시작할 수 없습니다",
      "Could not transcribe test recording": "테스트 녹음을 인식할 수 없습니다",
      "Could not read test transcription": "테스트 결과를 읽을 수 없습니다",
      "Could not update enabled state": "Decktation 사용 설정을 변경할 수 없습니다",
      "Could not load Whisper model": "Whisper 모델을 불러올 수 없습니다",
      "Could not remove button": "버튼을 삭제할 수 없습니다",
      "Could not update channel setting": "채널 설정을 변경할 수 없습니다",
      "Could not update recording cue": "녹음 표시를 변경할 수 없습니다",
      "Could not update haptic feedback": "진동 설정을 변경할 수 없습니다",
      "Could not update diagnostics setting": "진단 설정을 변경할 수 없습니다",
      "Could not update game": "모드를 변경할 수 없습니다",
      "Could not update model size": "모델을 변경할 수 없습니다",
      "Could not update binding": "버튼 조합을 변경할 수 없습니다",
      "Could not update language": "언어를 변경할 수 없습니다",
      "L1 Bumper": "L1 (범퍼)",
      "R1 Bumper": "R1 (범퍼)",
      "L2 Trigger": "L2 (트리거)",
      "R2 Trigger": "R2 (트리거)",
      "L4 Grip": "L4 (후면 버튼)",
      "R4 Grip": "R4 (후면 버튼)",
      "L5 Grip": "L5 (후면 버튼)",
      "R5 Grip": "R5 (후면 버튼)",
      "Waiting for input": "입력 대기 중",
      "Status unavailable": "상태를 확인할 수 없음",
      "Backend status request failed": "서비스 상태를 확인할 수 없습니다",
      "Could not update language setting": "받아쓰기 언어를 변경할 수 없습니다",
      Interface: Interface$4,
      Mode: Mode$4,
      "Review transcription": "받아쓰기 확인",
      "Transcription sending": "받아쓰기 전송",
      "Send immediately": "즉시 전송",
      "Review before sending": "전송 전에 확인",
      "Send after countdown": "카운트다운 후 전송",
      "Press Enter yourself": "Enter 직접 누르기",
      "Type into chat without submitting": "전송하지 않고 채팅에 입력",
      Send: Send$4,
      Cancel: Cancel$4,
      "Type into chat": "채팅에 입력",
      "Review confirmation": "검토 확인 상태",
      "After typing, press Enter in the game": "입력 후 게임에서 Enter를 누르세요",
      "Open Decktation to retry": "Decktation을 열어 다시 시도하세요",
      "Could not approve draft": "초안을 승인하지 못했습니다",
      "Could not cancel draft": "초안을 취소하지 못했습니다",
      "Could not update sending mode": "전송 모드를 변경하지 못했습니다",
      "Transcription. Use Up and Down to scroll.": "받아쓰기. 위아래 버튼으로 스크롤하세요.",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "이 메뉴를 닫은 후 게임에 입력합니다. 게임을 맨 앞에 두세요.",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "결정할 때까지 검토 화면이 유지됩니다. {binding}을 짧게 누르면 전송하고 길게 누르면 취소합니다. 긴 글은 Decktation을 열어 확인하세요.",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — Decktation을 열어 확인, 전송 또는 취소하세요",
      "Typing transcription…": "받아쓰기 입력 중…",
      "Open Decktation to retry typing": "Decktation을 열어 입력을 다시 시도하세요",
      "Open Decktation to review and send": "Decktation을 열어 확인하고 전송하세요",
      "Open Decktation to review all": "Decktation을 열어 전체 내용을 확인하세요",
      "Close Steam menus and return to your game": "Steam 메뉴를 닫고 게임으로 돌아가세요",
      "Open Decktation to confirm sending": "Decktation을 열어 전송을 확인하세요",
      "Update available": "업데이트 가능",
      "Preparing update...": "업데이트 준비 중...",
      "Waiting for Decky confirmation...": "Decky 확인 대기 중...",
      "Update to {version}": "{version}(으)로 업데이트",
      Updates: Updates$4,
      "Version {version}": "버전 {version}",
      "Update available: {version}": "업데이트 가능: {version}",
      "Up to date": "최신 버전",
      "Checking for updates...": "업데이트 확인 중...",
      "Check again": "다시 확인",
      "Check for updates": "업데이트 확인",
      "Decktation update available": "Decktation 업데이트 사용 가능",
      "Could not check for updates.": "업데이트를 확인할 수 없습니다.",
      "The update could not be verified, so it was not installed.": "업데이트를 검증할 수 없어 설치하지 않았습니다.",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "이 버전에서는 Decky 플러그인 설치 프로그램을 사용할 수 없습니다. Decktation ZIP 파일로 수동 업데이트하세요.",
      "An update is already being prepared.": "이미 업데이트를 준비하고 있습니다.",
      "Wait for the transcription model to finish loading.": "음성 인식 모델이 로드될 때까지 기다려 주세요.",
      "Finish the current dictation before updating.": "업데이트하기 전에 현재 음성 입력을 완료하세요.",
      "Binding saved: {binding}": "버튼 조합 저장됨: {binding}",
      "Binding cancelled. Your previous binding is unchanged.": "변경을 취소했습니다. 이전 버튼 조합은 유지됩니다.",
      "Could not start binding capture": "버튼 조합 감지를 시작하지 못했습니다",
      "Release all buttons to start listening.": "모든 버튼을 놓으면 감지를 시작합니다.",
      "Hold your new combination together. Release to save.": "새 조합을 함께 누른 뒤 놓으면 저장됩니다.",
      "Detected:": "감지됨:",
      "Listening…": "입력 대기 중…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "버튼 1~5개를 사용할 수 있습니다. Steam과 빠른 액세스는 제외됩니다. 감지는 20초 후 종료됩니다.",
      "Cancel (touch)": "취소 (터치)",
      "Change binding": "버튼 조합 변경",
      "Spoken punctuation": "음성 문장 부호",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "영어 또는 자동 감지에서 comma, period, question mark라고 말하면 문장 부호를 입력합니다. 해당 단어를 그대로 입력하려면 끄세요.",
      "Could not set spoken punctuation": "음성 문장 부호를 설정하지 못했습니다",
      "Microphone troubleshooting": "마이크 문제 해결",
      "Microphone guide. Use Up and Down to scroll.": "마이크 안내. 위아래로 스크롤하세요.",
      "Start with a dictation test": "받아쓰기 테스트부터 시작하세요",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "Decktation을 켜고 준비됨을 기다린 다음 메인 화면에서 받아쓰기 테스트 (3초)를 실행하세요. 또렷하게 말하세요. 결과는 패널에 남으며 게임에 입력되지 않습니다.",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "내장 마이크나 헤드셋이 다른 앱에서 작동하는지 확인하세요. Steam에서는 소리가 깨끗하지만 받아쓰기가 실패하면 시스템 기본 녹음 장치를 확인하세요.",
      "If audio crackles, pops, or cuts out": "소리가 지직거리거나 튀거나 끊기는 경우",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "Steam Deck LCD 사용자가 Steam 음성 처리를 끈 후 개선되었다고 보고했습니다. 커뮤니티의 임시 해결책이며 효과를 보장하지 않습니다. Decktation 오디오 입력에 미치는 영향은 확인되지 않았습니다.",
      "Open Steam → Power → Switch to Desktop.": "Steam → 전원 → 데스크톱으로 전환을 여세요.",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "Steam에서 친구 및 채팅 → 톱니바퀴 → 음성을 여세요. 일부 버전에는 Steam → 설정 → 음성도 있습니다.",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "음성 입력 장치를 선택하세요. 마이크 테스트를 시작하고 말하면서 잡음이나 빠진 단어가 있는지 들은 뒤 테스트를 중지하세요.",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "현재 설정을 기록하세요. 고급 설정에서 소음 제거, 에코 제거, 자동 음량·게인 조절을 꺼 보세요.",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "마이크 테스트를 반복하세요. 개선되면 옵션을 하나씩 다시 켜서 어떤 설정이 도움이 되는지 확인하세요.",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "게임 모드로 돌아와 게임에서 시도하기 전에 Decktation의 3초 받아쓰기 테스트를 반복하세요.",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "도움이 되지 않으면 이전 설정으로 복원하세요. 처리를 끄면 배경 소음이나 스피커 에코가 늘어나 Steam 음성 채팅에 영향을 줄 수 있습니다.",
      "If the problem persists": "문제가 계속되는 경우",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "문제를 보고할 때 Deck 모델(LCD 또는 OLED), SteamOS와 Steam 클라이언트 버전, 마이크나 헤드셋, 게임 모드와 재부팅 후에도 개선 상태가 유지되는지 알려 주세요. 최신 플러그인 로그에서 오류를 확인하세요.",
      "Open full guide online": "온라인에서 전체 안내 열기",
      "Microphone help": "마이크 도움말",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "음성이 인식되지 않거나 단어가 빠지거나 잡음이 들리나요? 여기서 마이크 안내를 확인하세요.",
      "Having problems with your microphone?": "마이크에 문제가 있나요?",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "민감한 정보를 제거한 오류, 사용 횟수 및 성능 지표를 Sentry로 보냅니다. 추론 백엔드와 대략적인 기기·OS 정보를 포함합니다. 오디오와 받아쓴 텍스트는 기기에만 남습니다.",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "command gg라고 말하면 /gg를, command ready라고 말하면 /ready를 입력합니다. 영어 또는 자동 감지를 사용하세요. 명령은 보내기 설정을 따릅니다.",
      "Binding timed out. Your previous binding is unchanged.": "시간이 초과되었습니다. 이전 버튼 조합은 유지됩니다.",
      "Controller disconnected. Your previous binding is unchanged.": "컨트롤러가 연결 해제되었습니다. 이전 버튼 조합은 유지됩니다.",
      "Use at most five buttons.": "버튼은 최대 5개까지 사용할 수 있습니다.",
      "Finish recording before changing the binding.": "버튼 조합을 변경하기 전에 녹음을 마치세요.",
      "Controller listener unavailable.": "컨트롤러 입력 서비스를 사용할 수 없습니다.",
      "Binding session ended.": "버튼 조합 설정 세션이 종료되었습니다."
    };

    var Back$3 = "戻る";
    var Enable$3 = "有効にする";
    var Language$3 = "音声入力の言語";
    var Binding$3 = "ボタンの組み合わせ";
    var Result$3 = "結果";
    var Model$3 = "モデル";
    var Sending$3 = "送信";
    var Confirm$3 = "送信前に確認";
    var Manual$3 = "手動送信";
    var Feedback$3 = "通知";
    var Toast$3 = "通知メッセージ";
    var Overlay$3 = "画面上の表示";
    var None$3 = "なし";
    var Diagnostics$3 = "診断";
    var Controller$3 = "コントローラー";
    var Yes$3 = "はい";
    var No$3 = "いいえ";
    var Backend$3 = "プラグインサービス";
    var Ready$3 = "準備完了";
    var Unavailable$3 = "利用できません";
    var Loading$3 = "読み込み中";
    var Share$3 = "共有する";
    var Permissions$3 = "権限";
    var Recording$3 = "録音";
    var Generic$3 = "通常のテキスト入力";
    var Interface$3 = "インターフェース";
    var Mode$3 = "モード";
    var Send$3 = "送信";
    var Cancel$3 = "キャンセル";
    var Updates$3 = "更新";
    var ja = {
      Back: Back$3,
      Enable: Enable$3,
      "Quick settings": "クイック設定",
      Language: Language$3,
      Binding: Binding$3,
      "Edit Bindings": "ボタンを編集",
      "Try it": "音声入力を試す",
      "Recording...": "録音中…",
      "Transcribing...": "音声認識中…",
      "Test Dictation (3s)": "音声入力テスト（3秒）",
      "Shows a transcription here without sending text to your game.": "認識したテキストをここに表示します。ゲームには送信しません。",
      Result: Result$3,
      "No speech detected": "音声が検出されませんでした",
      "Advanced settings": "詳細設定",
      "Transcription model": "音声認識モデル",
      Model: Model$3,
      "Recording binding": "録音ボタン",
      Sending: Sending$3,
      Confirm: Confirm$3,
      "Delay before send": "送信まで待機",
      Manual: Manual$3,
      "You press Enter": "Enterキーで送信",
      "Remember channel": "チャンネルを記憶",
      "Reuse the last spoken channel": "最後に指定したチャンネルを使う",
      Feedback: Feedback$3,
      "Recording cue": "録音表示",
      Toast: Toast$3,
      Overlay: Overlay$3,
      None: None$3,
      "Haptic feedback": "振動フィードバック",
      "Cues on the controller when recording starts and stops": "録音の開始時と終了時にコントローラーを振動させます",
      Diagnostics: Diagnostics$3,
      "Help & permissions": "ヘルプと権限",
      "Input and service": "入力とサービス",
      Controller: Controller$3,
      "Binding supported": "ボタンの組み合わせに対応",
      Yes: Yes$3,
      No: No$3,
      "Held buttons": "押しているボタン",
      "Keyboard helper": "キーボードサービス",
      Backend: Backend$3,
      Ready: Ready$3,
      Unavailable: Unavailable$3,
      Loading: Loading$3,
      "Diagnostics sharing": "診断情報の共有",
      Share: Share$3,
      "Optional scrubbed diagnostics sent to Sentry": "個人情報を除去した診断データをSentryに送信します（任意）",
      "How to use": "使い方",
      Permissions: Permissions$3,
      "Auto Detect": "自動検出",
      "Popular Steam languages": "Steamでよく使われる言語",
      "Other languages": "その他の言語",
      "Add Button": "ボタンを追加",
      "Button {number}": "ボタン {number}",
      "Remove button {number}": "ボタン {number} を削除",
      "Hold {binding} to record": "{binding}を長押しして録音",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "{binding}を{together}長押しして録音します。ボタンを離すと、音声を認識して現在のゲームやアプリにテキストを入力します。その画面を前面に表示してください。",
      "together ": "同時に",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktationは、コントローラーの入力を読み取り、音声入力のテキストをキーボード入力として送るためにDeckyのroot権限を使用します。テキストはデータとして渡され、シェルコマンドとして実行されることはありません。",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Baseは最も高速です。Smallは速度と精度のバランスが良いモデルです。Mediumはより高精度ですが低速で、初回使用時にダウンロードが必要な場合があります。",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cppはVulkan経由でGPUを使用します。",
      "whisper.cpp runs on the CPU.": "whisper.cppはCPUを使用します。",
      "Connecting to Decktation...": "Decktationに接続中…",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "キーボードサービスを利用できません。Decktationを再読み込みするか再インストールしてください。",
      "Loading transcription model...": "音声認識モデルを読み込み中…",
      "Decktation is off": "Decktationは無効です",
      "Model not ready": "モデルの準備ができていません",
      "Controller unavailable": "コントローラーを利用できません",
      "Backend unavailable: {error}": "サービスを利用できません: {error}",
      "Recording for 3 seconds...": "3秒間録音中…",
      Recording: Recording$3,
      "Sending in {seconds}s": "{seconds}秒後に送信",
      "\"{text}\" — hold PTT to cancel": "「{text}」— キャンセルするには録音ボタンを長押ししてください",
      "Interface language": "表示言語",
      "Automatic (system)": "自動（Steam）",
      "Only changes the menu language, not the dictation language.": "メニューの言語だけを変更します。音声入力の言語は変わりません。",
      Generic: Generic$3,
      "Base · Fast": "Base · 高速",
      "Small · Balanced": "Small · バランス",
      "Medium · More accurate": "Medium · 高精度",
      "Could not start test recording": "テスト録音を開始できません",
      "Could not transcribe test recording": "テスト録音を認識できません",
      "Could not read test transcription": "テスト結果を読み取れません",
      "Could not update enabled state": "Decktationの有効・無効を変更できません",
      "Could not load Whisper model": "Whisperモデルを読み込めません",
      "Could not remove button": "ボタンを削除できません",
      "Could not update channel setting": "チャンネル設定を変更できません",
      "Could not update recording cue": "録音表示を変更できません",
      "Could not update haptic feedback": "振動設定を変更できません",
      "Could not update diagnostics setting": "診断設定を変更できません",
      "Could not update game": "モードを変更できません",
      "Could not update model size": "モデルを変更できません",
      "Could not update binding": "ボタンの組み合わせを変更できません",
      "Could not update language": "言語を変更できません",
      "L1 Bumper": "L1 (バンパー)",
      "R1 Bumper": "R1 (バンパー)",
      "L2 Trigger": "L2 (トリガー)",
      "R2 Trigger": "R2 (トリガー)",
      "L4 Grip": "L4 (背面ボタン)",
      "R4 Grip": "R4 (背面ボタン)",
      "L5 Grip": "L5 (背面ボタン)",
      "R5 Grip": "R5 (背面ボタン)",
      "Waiting for input": "入力待ち",
      "Status unavailable": "状態を取得できません",
      "Backend status request failed": "サービスの状態を取得できません",
      "Could not update language setting": "音声入力の言語を変更できません",
      Interface: Interface$3,
      Mode: Mode$3,
      "Review transcription": "文字起こしを確認",
      "Transcription sending": "文字起こしの送信",
      "Send immediately": "すぐに送信",
      "Review before sending": "送信前に確認",
      "Send after countdown": "カウントダウン後に送信",
      "Press Enter yourself": "Enterを自分で押す",
      "Type into chat without submitting": "送信せずにチャットへ入力",
      Send: Send$3,
      Cancel: Cancel$3,
      "Type into chat": "チャットへ入力",
      "Review confirmation": "確認操作の状態",
      "After typing, press Enter in the game": "入力後、ゲーム内でEnterを押してください",
      "Open Decktation to retry": "Decktationを開いて再試行してください",
      "Could not approve draft": "下書きを承認できませんでした",
      "Could not cancel draft": "下書きをキャンセルできませんでした",
      "Could not update sending mode": "送信モードを変更できませんでした",
      "Transcription. Use Up and Down to scroll.": "文字起こし。上下ボタンでスクロールします。",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "このメニューを閉じてからゲームに入力します。ゲームを最前面にしてください。",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "確認画面は操作するまで表示されます。{binding}を短く押すと送信、長押しでキャンセルします。長い文章はDecktationを開いて確認してください。",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — Decktationを開いて確認、送信、またはキャンセルしてください",
      "Typing transcription…": "文字起こしを入力中…",
      "Open Decktation to retry typing": "Decktationを開いて入力を再試行してください",
      "Open Decktation to review and send": "Decktationを開いて確認し、送信してください",
      "Open Decktation to review all": "Decktationを開いて全文を確認してください",
      "Close Steam menus and return to your game": "Steamのメニューを閉じてゲームに戻ってください",
      "Open Decktation to confirm sending": "Decktationを開いて送信を確認してください",
      "Update available": "更新があります",
      "Preparing update...": "更新を準備中...",
      "Waiting for Decky confirmation...": "Decky の確認待ち...",
      "Update to {version}": "{version} に更新",
      Updates: Updates$3,
      "Version {version}": "バージョン {version}",
      "Update available: {version}": "更新があります: {version}",
      "Up to date": "最新です",
      "Checking for updates...": "更新を確認中...",
      "Check again": "再確認",
      "Check for updates": "更新を確認",
      "Decktation update available": "Decktationの更新が利用可能",
      "Could not check for updates.": "更新を確認できませんでした。",
      "The update could not be verified, so it was not installed.": "更新を検証できなかったため、インストールされませんでした。",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "このバージョンではDeckyのプラグインインストーラーを利用できません。DecktationのZIPファイルを使って手動で更新してください。",
      "An update is already being prepared.": "すでに更新を準備しています。",
      "Wait for the transcription model to finish loading.": "文字起こしモデルの読み込みが完了するまでお待ちください。",
      "Finish the current dictation before updating.": "更新する前に現在の音声入力を終了してください。",
      "Binding saved: {binding}": "割り当てを保存しました: {binding}",
      "Binding cancelled. Your previous binding is unchanged.": "変更をキャンセルしました。以前の割り当ては変更されません。",
      "Could not start binding capture": "割り当ての検出を開始できませんでした",
      "Release all buttons to start listening.": "すべてのボタンを離すと検出を開始します。",
      "Hold your new combination together. Release to save.": "新しい組み合わせを押し続け、離して保存します。",
      "Detected:": "検出:",
      "Listening…": "入力待ち…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "1～5個のボタンを使用できます。Steamとクイックアクセスは対象外です。検出は20秒で終了します。",
      "Cancel (touch)": "キャンセル（タッチ）",
      "Change binding": "割り当てを変更",
      "Spoken punctuation": "音声による句読点入力",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "英語または自動検出では、comma、period、question markと発音して句読点を入力できます。これらの単語をそのまま入力するにはオフにしてください。",
      "Could not set spoken punctuation": "音声による句読点入力を設定できませんでした",
      "Microphone troubleshooting": "マイクのトラブルシューティング",
      "Microphone guide. Use Up and Down to scroll.": "マイクのガイド。上下でスクロールします。",
      "Start with a dictation test": "まず音声入力をテスト",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "Decktationを有効にし、準備完了を待ってメイン画面の音声入力テスト（3秒）を実行してください。はっきり話してください。結果はパネルに表示され、ゲームには入力されません。",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "内蔵マイクやヘッドセットが別のアプリで動作するか確認してください。Steamでは正常でも音声入力に失敗する場合は、システムの既定の録音デバイスを確認してください。",
      "If audio crackles, pops, or cuts out": "音が割れる、ノイズが入る、途切れる場合",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "Steam Deck LCDの利用者から、Steamの音声処理を無効にすると改善したとの報告があります。これはコミュニティの回避策で、効果は保証されません。Decktationの音声入力への影響は確認されていません。",
      "Open Steam → Power → Switch to Desktop.": "Steam → 電源 → デスクトップに切り替えを開きます。",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "Steamのフレンド＆チャット → 歯車 → ボイスを開きます。バージョンによってはSteam → 設定 → ボイスからも開けます。",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "音声入力デバイスを選択します。マイクテストを開始して話し、ノイズや言葉の欠落がないか聞いた後、テストを停止します。",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "現在の設定を控えてください。詳細設定でノイズキャンセリング、エコーキャンセリング、音量・ゲインの自動調整をオフにしてみてください。",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "マイクテストを繰り返します。改善したら、項目を1つずつ有効に戻して、効果のある設定を確認してください。",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "ゲーミングモードに戻り、ゲームで試す前にDecktationの3秒間の音声入力テストを繰り返してください。",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "改善しなければ元の設定に戻してください。音声処理を無効にすると、背景ノイズやスピーカーのエコーが増え、Steamのボイスチャットに影響する場合があります。",
      "If the problem persists": "問題が解決しない場合",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "問題を報告する際は、Deckのモデル（LCDまたはOLED）、SteamOSとSteamクライアントのバージョン、マイクやヘッドセット、ゲーミングモードや再起動後も改善が続くかを記載してください。最新のプラグインログでエラーを確認してください。",
      "Open full guide online": "完全なガイドをオンラインで開く",
      "Microphone help": "マイクのヘルプ",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "音声が認識されない、言葉が抜ける、ノイズが入る場合は、こちらのマイクガイドをご覧ください。",
      "Having problems with your microphone?": "マイクに問題がありますか？",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "機密情報を除去したエラー、利用回数、性能指標をSentryへ送信します。推論バックエンドや大まかなデバイス・OS情報を含みます。音声と文字起こしは端末内に保持されます。",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "command ggと発音すると/gg、command readyで/readyを入力します。英語または自動検出を使用してください。コマンドは送信設定に従います。",
      "Binding timed out. Your previous binding is unchanged.": "時間切れです。以前の割り当ては変更されません。",
      "Controller disconnected. Your previous binding is unchanged.": "コントローラーが切断されました。以前の割り当ては変更されません。",
      "Use at most five buttons.": "ボタンは5個まで使用できます。",
      "Finish recording before changing the binding.": "割り当てを変更する前に録音を終了してください。",
      "Controller listener unavailable.": "コントローラー入力サービスを利用できません。",
      "Binding session ended.": "割り当て設定のセッションが終了しました。"
    };

    var Back$2 = "Zurück";
    var Enable$2 = "Aktivieren";
    var Language$2 = "Diktiersprache";
    var Binding$2 = "Tastenkombination";
    var Result$2 = "Ergebnis";
    var Model$2 = "Modell";
    var Sending$2 = "Senden";
    var Confirm$2 = "Bestätigen";
    var Manual$2 = "Manuell senden";
    var Feedback$2 = "Rückmeldung";
    var Toast$2 = "Benachrichtigung";
    var Overlay$2 = "Bildschirmanzeige";
    var None$2 = "Keine";
    var Diagnostics$2 = "Diagnose";
    var Controller$2 = "Controller";
    var Yes$2 = "Ja";
    var No$2 = "Nein";
    var Backend$2 = "Plugin-Dienst";
    var Ready$2 = "Bereit";
    var Unavailable$2 = "Nicht verfügbar";
    var Loading$2 = "Wird geladen";
    var Share$2 = "Teilen";
    var Permissions$2 = "Berechtigungen";
    var Recording$2 = "Aufnahme";
    var Generic$2 = "Allgemeine Texteingabe";
    var Interface$2 = "Oberfläche";
    var Mode$2 = "Modus";
    var Send$2 = "Senden";
    var Cancel$2 = "Abbrechen";
    var Updates$2 = "Updates";
    var de = {
      Back: Back$2,
      Enable: Enable$2,
      "Quick settings": "Schnelleinstellungen",
      Language: Language$2,
      Binding: Binding$2,
      "Edit Bindings": "Tasten bearbeiten",
      "Try it": "Diktat ausprobieren",
      "Recording...": "Aufnahme läuft…",
      "Transcribing...": "Transkription läuft…",
      "Test Dictation (3s)": "Diktat testen (3 s)",
      "Shows a transcription here without sending text to your game.": "Zeigt den erkannten Text hier an, ohne ihn an das Spiel zu senden.",
      Result: Result$2,
      "No speech detected": "Keine Sprache erkannt",
      "Advanced settings": "Erweiterte Einstellungen",
      "Transcription model": "Transkriptionsmodell",
      Model: Model$2,
      "Recording binding": "Aufnahmetasten",
      Sending: Sending$2,
      Confirm: Confirm$2,
      "Delay before send": "Verzögerung vor dem Senden",
      Manual: Manual$2,
      "You press Enter": "Zum Senden die Eingabetaste drücken",
      "Remember channel": "Kanal merken",
      "Reuse the last spoken channel": "Zuletzt genannten Kanal wiederverwenden",
      Feedback: Feedback$2,
      "Recording cue": "Aufnahmeanzeige",
      Toast: Toast$2,
      Overlay: Overlay$2,
      None: None$2,
      "Haptic feedback": "Vibration",
      "Cues on the controller when recording starts and stops": "Vibration beim Start und Ende der Aufnahme",
      Diagnostics: Diagnostics$2,
      "Help & permissions": "Hilfe und Berechtigungen",
      "Input and service": "Eingabe und Dienst",
      Controller: Controller$2,
      "Binding supported": "Tastenkombination unterstützt",
      Yes: Yes$2,
      No: No$2,
      "Held buttons": "Gedrückte Tasten",
      "Keyboard helper": "Tastaturdienst",
      Backend: Backend$2,
      Ready: Ready$2,
      Unavailable: Unavailable$2,
      Loading: Loading$2,
      "Diagnostics sharing": "Diagnosedaten teilen",
      Share: Share$2,
      "Optional scrubbed diagnostics sent to Sentry": "Optional bereinigte Diagnosedaten an Sentry senden",
      "How to use": "Bedienung",
      Permissions: Permissions$2,
      "Auto Detect": "Automatisch erkennen",
      "Popular Steam languages": "Häufige Steam-Sprachen",
      "Other languages": "Weitere Sprachen",
      "Add Button": "Taste hinzufügen",
      "Button {number}": "Taste {number}",
      "Remove button {number}": "Taste {number} entfernen",
      "Hold {binding} to record": "Zum Aufnehmen {binding} gedrückt halten",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "Zum Aufnehmen {binding} {together}gedrückt halten. Loslassen, um den Text zu erkennen und im aktiven Spiel oder Programm einzugeben. Dieses muss im Vordergrund bleiben.",
      "together ": "gleichzeitig ",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktation nutzt Deckys Root-Zugriff, um Controller-Eingaben zu lesen und Tastatureingaben für den diktierten Text zu erzeugen. Der Text wird als Daten an den Tastaturdienst übergeben, niemals als Shell-Befehl.",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Base ist am schnellsten. Small bietet einen Kompromiss zwischen Tempo und Genauigkeit. Medium ist genauer, aber langsamer und wird eventuell bei der ersten Nutzung heruntergeladen.",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cpp nutzt die GPU über Vulkan.",
      "whisper.cpp runs on the CPU.": "whisper.cpp nutzt die CPU.",
      "Connecting to Decktation...": "Verbindung mit Decktation wird hergestellt…",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "Tastaturdienst nicht verfügbar. Decktation neu laden oder neu installieren.",
      "Loading transcription model...": "Transkriptionsmodell wird geladen…",
      "Decktation is off": "Decktation ist deaktiviert",
      "Model not ready": "Modell ist nicht bereit",
      "Controller unavailable": "Controller nicht verfügbar",
      "Backend unavailable: {error}": "Dienst nicht verfügbar: {error}",
      "Recording for 3 seconds...": "Aufnahme für 3 Sekunden…",
      Recording: Recording$2,
      "Sending in {seconds}s": "Senden in {seconds} s",
      "\"{text}\" — hold PTT to cancel": "„{text}“ — Aufnahmetasten zum Abbrechen gedrückt halten",
      "Interface language": "Sprache der Oberfläche",
      "Automatic (system)": "Automatisch (Steam)",
      "Only changes the menu language, not the dictation language.": "Ändert nur die Menüsprache, nicht die Diktiersprache.",
      Generic: Generic$2,
      "Base · Fast": "Base · Schnell",
      "Small · Balanced": "Small · Ausgewogen",
      "Medium · More accurate": "Medium · Genauer",
      "Could not start test recording": "Testaufnahme konnte nicht gestartet werden",
      "Could not transcribe test recording": "Testaufnahme konnte nicht transkribiert werden",
      "Could not read test transcription": "Testergebnis konnte nicht gelesen werden",
      "Could not update enabled state": "Decktation konnte nicht aktiviert oder deaktiviert werden",
      "Could not load Whisper model": "Whisper-Modell konnte nicht geladen werden",
      "Could not remove button": "Taste konnte nicht entfernt werden",
      "Could not update channel setting": "Kanaleinstellung konnte nicht geändert werden",
      "Could not update recording cue": "Aufnahmeanzeige konnte nicht geändert werden",
      "Could not update haptic feedback": "Vibration konnte nicht geändert werden",
      "Could not update diagnostics setting": "Diagnoseeinstellung konnte nicht geändert werden",
      "Could not update game": "Modus konnte nicht geändert werden",
      "Could not update model size": "Modell konnte nicht geändert werden",
      "Could not update binding": "Tastenkombination konnte nicht geändert werden",
      "Could not update language": "Sprache konnte nicht geändert werden",
      "L1 Bumper": "L1 (Schultertaste)",
      "R1 Bumper": "R1 (Schultertaste)",
      "L2 Trigger": "L2 (Trigger)",
      "R2 Trigger": "R2 (Trigger)",
      "L4 Grip": "L4 (Rücktaste)",
      "R4 Grip": "R4 (Rücktaste)",
      "L5 Grip": "L5 (Rücktaste)",
      "R5 Grip": "R5 (Rücktaste)",
      "Waiting for input": "Warten auf Eingabe",
      "Status unavailable": "Status nicht verfügbar",
      "Backend status request failed": "Dienststatus konnte nicht abgefragt werden",
      "Could not update language setting": "Diktiersprache konnte nicht geändert werden",
      Interface: Interface$2,
      Mode: Mode$2,
      "Review transcription": "Transkription prüfen",
      "Transcription sending": "Transkription senden",
      "Send immediately": "Sofort senden",
      "Review before sending": "Vor dem Senden prüfen",
      "Send after countdown": "Nach Countdown senden",
      "Press Enter yourself": "Enter selbst drücken",
      "Type into chat without submitting": "In den Chat schreiben, ohne zu senden",
      Send: Send$2,
      Cancel: Cancel$2,
      "Type into chat": "In den Chat schreiben",
      "Review confirmation": "Prüfbestätigung",
      "After typing, press Enter in the game": "Nach der Texteingabe im Spiel Enter drücken",
      "Open Decktation to retry": "Decktation öffnen, um es erneut zu versuchen",
      "Could not approve draft": "Entwurf konnte nicht bestätigt werden",
      "Could not cancel draft": "Entwurf konnte nicht verworfen werden",
      "Could not update sending mode": "Sendemodus konnte nicht geändert werden",
      "Transcription. Use Up and Down to scroll.": "Transkription. Mit Oben und Unten scrollen.",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "Schließt dieses Menü vor der Texteingabe im Spiel. Das Spiel im Vordergrund lassen.",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "Die Vorschau bleibt sichtbar, bis du entscheidest. {binding} kurz drücken zum Senden; gedrückt halten zum Abbrechen. Decktation öffnen, um längere Texte zu prüfen.",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — Decktation öffnen zum Prüfen, Senden oder Abbrechen",
      "Typing transcription…": "Transkription wird eingegeben…",
      "Open Decktation to retry typing": "Decktation öffnen, um die Eingabe erneut zu versuchen",
      "Open Decktation to review and send": "Decktation öffnen zum Prüfen und Senden",
      "Open Decktation to review all": "Decktation öffnen, um alles zu prüfen",
      "Close Steam menus and return to your game": "Steam-Menüs schließen und zum Spiel zurückkehren",
      "Open Decktation to confirm sending": "Decktation öffnen, um das Senden zu bestätigen",
      "Update available": "Update verfügbar",
      "Preparing update...": "Update wird vorbereitet...",
      "Waiting for Decky confirmation...": "Warten auf Decky-Bestätigung...",
      "Update to {version}": "Auf {version} aktualisieren",
      Updates: Updates$2,
      "Version {version}": "Version {version}",
      "Update available: {version}": "Update verfügbar: {version}",
      "Up to date": "Aktuell",
      "Checking for updates...": "Updates werden gesucht...",
      "Check again": "Erneut prüfen",
      "Check for updates": "Nach Updates suchen",
      "Decktation update available": "Decktation-Update verfügbar",
      "Could not check for updates.": "Updates konnten nicht geprüft werden.",
      "The update could not be verified, so it was not installed.": "Das Update konnte nicht überprüft werden und wurde daher nicht installiert.",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "Der Plugin-Installer von Decky ist in dieser Version nicht verfügbar. Aktualisiere manuell mit der Decktation-ZIP-Datei.",
      "An update is already being prepared.": "Ein Update wird bereits vorbereitet.",
      "Wait for the transcription model to finish loading.": "Warte, bis das Transkriptionsmodell vollständig geladen ist.",
      "Finish the current dictation before updating.": "Beende das aktuelle Diktat vor dem Update.",
      "Binding saved: {binding}": "Belegung gespeichert: {binding}",
      "Binding cancelled. Your previous binding is unchanged.": "Belegung abgebrochen. Die bisherige Belegung bleibt unverändert.",
      "Could not start binding capture": "Erfassung der Belegung konnte nicht gestartet werden",
      "Release all buttons to start listening.": "Lasse alle Tasten los, um die Erfassung zu starten.",
      "Hold your new combination together. Release to save.": "Halte die neue Tastenkombination gedrückt. Zum Speichern loslassen.",
      "Detected:": "Erkannt:",
      "Listening…": "Warte auf Eingabe…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "Eine bis fünf Tasten. Steam und Schnellzugriff sind ausgeschlossen. Die Erfassung endet nach 20 Sekunden.",
      "Cancel (touch)": "Abbrechen (antippen)",
      "Change binding": "Belegung ändern",
      "Spoken punctuation": "Gesprochene Satzzeichen",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "Sage bei Englisch oder automatischer Erkennung comma, period oder question mark, um Satzzeichen einzufügen. Deaktiviere die Option, um diese Wörter wörtlich zu schreiben.",
      "Could not set spoken punctuation": "Gesprochene Satzzeichen konnten nicht eingestellt werden",
      "Microphone troubleshooting": "Mikrofonprobleme beheben",
      "Microphone guide. Use Up and Down to scroll.": "Mikrofonanleitung. Mit Auf und Ab scrollen.",
      "Start with a dictation test": "Mit einem Diktattest beginnen",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "Aktiviere Decktation, warte auf Bereit und starte Diktat testen (3 s) auf der Hauptseite. Sprich deutlich. Das Ergebnis bleibt im Menü und wird nicht ins Spiel eingegeben.",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "Prüfe, ob das eingebaute Mikrofon oder Headset in einer anderen App funktioniert. Wenn Steam klar klingt, das Diktat aber fehlschlägt, prüfe das Standardaufnahmegerät des Systems.",
      "If audio crackles, pops, or cuts out": "Bei Knistern, Knacken oder Audioaussetzern",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "Ein Nutzer eines Steam Deck LCD berichtete von einer Verbesserung nach dem Abschalten der Steam-Sprachverarbeitung. Dies ist ein Community-Tipp ohne Erfolgsgarantie. Die Wirkung auf Decktations Audioeingang ist nicht geklärt.",
      "Open Steam → Power → Switch to Desktop.": "Öffne Steam → Ein/Aus → Zum Desktop wechseln.",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "Öffne in Steam Freunde & Chat → Zahnrad → Sprache. Manche Versionen bieten auch Steam → Einstellungen → Spracheingabe.",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "Wähle dein Spracheingabegerät. Starte den Mikrofontest, sprich und achte auf Knacken oder fehlende Wörter. Beende dann den Test.",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "Notiere die aktuellen Einstellungen. Versuche unter Erweiterte Einstellungen anzeigen, Rauschunterdrückung, Echounterdrückung und automatische Lautstärke-/Verstärkungsregelung abzuschalten.",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "Wiederhole den Mikrofontest. Wenn es besser wird, aktiviere die Optionen einzeln wieder, um die hilfreiche Einstellung zu finden.",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "Kehre zum Gaming-Modus zurück und wiederhole Decktations dreisekündigen Diktattest, bevor du es im Spiel versuchst.",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "Stelle die bisherigen Einstellungen wieder her, wenn dies nicht hilft. Ohne Verarbeitung können Hintergrundgeräusche oder Lautsprecherechos zunehmen und den Steam-Sprachchat beeinträchtigen.",
      "If the problem persists": "Wenn das Problem weiterhin besteht",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "Nenne beim Melden des Problems dein Deck-Modell (LCD oder OLED), die SteamOS- und Steam-Client-Versionen, Mikrofon oder Headset und ob die Verbesserung im Gaming-Modus und nach einem Neustart bestehen bleibt. Prüfe das neueste Plugin-Protokoll auf Fehler.",
      "Open full guide online": "Vollständige Anleitung online öffnen",
      "Microphone help": "Mikrofonhilfe",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "Stimme nicht erkannt, fehlende Wörter oder knisterndes Audio? Lies hier die Mikrofonanleitung.",
      "Having problems with your microphone?": "Probleme mit dem Mikrofon?",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "Sendet um sensible Daten bereinigte Fehler, Nutzungszahlen und Leistungswerte an Sentry, einschließlich Inferenz-Backend und allgemeiner Geräte-/Betriebssystemdaten. Audio und Transkripte bleiben lokal.",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "Sage command gg für /gg oder command ready für /ready. Verwende Englisch oder automatische Erkennung. Befehle beachten deine Sendeeinstellungen.",
      "Binding timed out. Your previous binding is unchanged.": "Zeit abgelaufen. Die bisherige Belegung bleibt unverändert.",
      "Controller disconnected. Your previous binding is unchanged.": "Controller getrennt. Die bisherige Belegung bleibt unverändert.",
      "Use at most five buttons.": "Verwende höchstens fünf Tasten.",
      "Finish recording before changing the binding.": "Beende die Aufnahme, bevor du die Belegung änderst.",
      "Controller listener unavailable.": "Controller-Erkennung nicht verfügbar.",
      "Binding session ended.": "Die Belegungssitzung wurde beendet."
    };

    var Back$1 = "Retour";
    var Enable$1 = "Activer";
    var Language$1 = "Langue de dictée";
    var Binding$1 = "Combinaison";
    var Result$1 = "Résultat";
    var Model$1 = "Modèle";
    var Sending$1 = "Envoi";
    var Confirm$1 = "Confirmer";
    var Manual$1 = "Envoi manuel";
    var Feedback$1 = "Indicateurs";
    var Toast$1 = "Notification";
    var Overlay$1 = "Indicateur à l’écran";
    var None$1 = "Aucun";
    var Diagnostics$1 = "Diagnostic";
    var Controller$1 = "Manette";
    var Yes$1 = "Oui";
    var No$1 = "Non";
    var Backend$1 = "Service du plugin";
    var Ready$1 = "Prêt";
    var Unavailable$1 = "Indisponible";
    var Loading$1 = "Chargement";
    var Share$1 = "Partager";
    var Permissions$1 = "Autorisations";
    var Recording$1 = "Enregistrement";
    var Generic$1 = "Saisie générale";
    var Interface$1 = "Interface";
    var Mode$1 = "Mode";
    var Send$1 = "Envoyer";
    var Cancel$1 = "Annuler";
    var Updates$1 = "Mises à jour";
    var fr = {
      Back: Back$1,
      Enable: Enable$1,
      "Quick settings": "Réglages rapides",
      Language: Language$1,
      Binding: Binding$1,
      "Edit Bindings": "Modifier les boutons",
      "Try it": "Essayer la dictée",
      "Recording...": "Enregistrement…",
      "Transcribing...": "Transcription…",
      "Test Dictation (3s)": "Tester la dictée (3 s)",
      "Shows a transcription here without sending text to your game.": "Affiche la transcription ici sans envoyer de texte au jeu.",
      Result: Result$1,
      "No speech detected": "Aucune parole détectée",
      "Advanced settings": "Réglages avancés",
      "Transcription model": "Modèle de transcription",
      Model: Model$1,
      "Recording binding": "Boutons d’enregistrement",
      Sending: Sending$1,
      Confirm: Confirm$1,
      "Delay before send": "Délai avant l’envoi",
      Manual: Manual$1,
      "You press Enter": "Appuyez sur Entrée pour envoyer",
      "Remember channel": "Mémoriser le canal",
      "Reuse the last spoken channel": "Réutiliser le dernier canal indiqué",
      Feedback: Feedback$1,
      "Recording cue": "Indicateur d’enregistrement",
      Toast: Toast$1,
      Overlay: Overlay$1,
      None: None$1,
      "Haptic feedback": "Vibrations",
      "Cues on the controller when recording starts and stops": "Vibrations au début et à la fin de l’enregistrement",
      Diagnostics: Diagnostics$1,
      "Help & permissions": "Aide et autorisations",
      "Input and service": "Entrée et service",
      Controller: Controller$1,
      "Binding supported": "Combinaison compatible",
      Yes: Yes$1,
      No: No$1,
      "Held buttons": "Boutons maintenus",
      "Keyboard helper": "Service de saisie",
      Backend: Backend$1,
      Ready: Ready$1,
      Unavailable: Unavailable$1,
      Loading: Loading$1,
      "Diagnostics sharing": "Partage du diagnostic",
      Share: Share$1,
      "Optional scrubbed diagnostics sent to Sentry": "Envoi facultatif de données de diagnostic filtrées à Sentry",
      "How to use": "Utilisation",
      Permissions: Permissions$1,
      "Auto Detect": "Détection automatique",
      "Popular Steam languages": "Langues courantes sur Steam",
      "Other languages": "Autres langues",
      "Add Button": "Ajouter un bouton",
      "Button {number}": "Bouton {number}",
      "Remove button {number}": "Supprimer le bouton {number}",
      "Hold {binding} to record": "Maintenez {binding} pour enregistrer",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "Maintenez {binding} {together}pour enregistrer. Relâchez pour transcrire et saisir le texte dans le jeu ou l’application au premier plan.",
      "together ": "simultanément ",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktation utilise l’accès root de Decky pour lire les boutons de la manette et générer les frappes du texte dicté. La transcription est transmise comme du texte, jamais comme une commande shell.",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Base est le plus rapide. Small équilibre vitesse et précision. Medium est plus précis, mais plus lent et peut être téléchargé à la première utilisation.",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cpp utilise le GPU via Vulkan.",
      "whisper.cpp runs on the CPU.": "whisper.cpp utilise le CPU.",
      "Connecting to Decktation...": "Connexion à Decktation…",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "Service de saisie indisponible. Rechargez ou réinstallez Decktation.",
      "Loading transcription model...": "Chargement du modèle de transcription…",
      "Decktation is off": "Decktation est désactivé",
      "Model not ready": "Modèle non prêt",
      "Controller unavailable": "Manette indisponible",
      "Backend unavailable: {error}": "Service indisponible : {error}",
      "Recording for 3 seconds...": "Enregistrement pendant 3 secondes…",
      Recording: Recording$1,
      "Sending in {seconds}s": "Envoi dans {seconds} s",
      "\"{text}\" — hold PTT to cancel": "« {text} » — maintenez les boutons de dictée pour annuler",
      "Interface language": "Langue de l’interface",
      "Automatic (system)": "Automatique (Steam)",
      "Only changes the menu language, not the dictation language.": "Modifie uniquement la langue des menus, pas celle de la dictée.",
      Generic: Generic$1,
      "Base · Fast": "Base · Rapide",
      "Small · Balanced": "Small · Équilibré",
      "Medium · More accurate": "Medium · Plus précis",
      "Could not start test recording": "Impossible de démarrer le test",
      "Could not transcribe test recording": "Impossible de transcrire le test",
      "Could not read test transcription": "Impossible de lire le résultat du test",
      "Could not update enabled state": "Impossible d’activer ou de désactiver Decktation",
      "Could not load Whisper model": "Impossible de charger le modèle Whisper",
      "Could not remove button": "Impossible de supprimer le bouton",
      "Could not update channel setting": "Impossible de modifier le canal",
      "Could not update recording cue": "Impossible de modifier l’indicateur d’enregistrement",
      "Could not update haptic feedback": "Impossible de modifier les vibrations",
      "Could not update diagnostics setting": "Impossible de modifier le partage du diagnostic",
      "Could not update game": "Impossible de changer de mode",
      "Could not update model size": "Impossible de changer de modèle",
      "Could not update binding": "Impossible de modifier les boutons",
      "Could not update language": "Impossible de modifier la langue",
      "L1 Bumper": "L1 (bouton supérieur)",
      "R1 Bumper": "R1 (bouton supérieur)",
      "L2 Trigger": "L2 (gâchette)",
      "R2 Trigger": "R2 (gâchette)",
      "L4 Grip": "L4 (bouton arrière)",
      "R4 Grip": "R4 (bouton arrière)",
      "L5 Grip": "L5 (bouton arrière)",
      "R5 Grip": "R5 (bouton arrière)",
      "Waiting for input": "En attente d’une entrée",
      "Status unavailable": "État indisponible",
      "Backend status request failed": "Impossible de lire l’état du service",
      "Could not update language setting": "Impossible de modifier la langue de dictée",
      Interface: Interface$1,
      Mode: Mode$1,
      "Review transcription": "Relire la transcription",
      "Transcription sending": "Envoi de la transcription",
      "Send immediately": "Envoyer immédiatement",
      "Review before sending": "Relire avant d’envoyer",
      "Send after countdown": "Envoyer après le compte à rebours",
      "Press Enter yourself": "Appuyer sur Entrée soi-même",
      "Type into chat without submitting": "Écrire dans le chat sans envoyer",
      Send: Send$1,
      Cancel: Cancel$1,
      "Type into chat": "Écrire dans le chat",
      "Review confirmation": "Confirmation de la relecture",
      "After typing, press Enter in the game": "Après la saisie, appuyez sur Entrée dans le jeu",
      "Open Decktation to retry": "Ouvrez Decktation pour réessayer",
      "Could not approve draft": "Impossible de valider le brouillon",
      "Could not cancel draft": "Impossible d’annuler le brouillon",
      "Could not update sending mode": "Impossible de modifier le mode d’envoi",
      "Transcription. Use Up and Down to scroll.": "Transcription. Utilisez Haut et Bas pour faire défiler.",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "Ferme ce menu avant de saisir dans le jeu. Gardez le jeu au premier plan.",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "La transcription reste visible jusqu’à votre décision. Appuyez sur {binding} pour envoyer ; maintenez pour annuler. Ouvrez Decktation pour relire les textes longs.",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — ouvrez Decktation pour relire, envoyer ou annuler",
      "Typing transcription…": "Saisie de la transcription…",
      "Open Decktation to retry typing": "Ouvrez Decktation pour réessayer la saisie",
      "Open Decktation to review and send": "Ouvrez Decktation pour relire et envoyer",
      "Open Decktation to review all": "Ouvrez Decktation pour tout relire",
      "Close Steam menus and return to your game": "Fermez les menus Steam et revenez au jeu",
      "Open Decktation to confirm sending": "Ouvrez Decktation pour confirmer l’envoi",
      "Update available": "Mise à jour disponible",
      "Preparing update...": "Préparation de la mise à jour...",
      "Waiting for Decky confirmation...": "En attente de confirmation Decky...",
      "Update to {version}": "Mettre à jour vers {version}",
      Updates: Updates$1,
      "Version {version}": "Version {version}",
      "Update available: {version}": "Mise à jour disponible : {version}",
      "Up to date": "À jour",
      "Checking for updates...": "Recherche de mises à jour...",
      "Check again": "Vérifier à nouveau",
      "Check for updates": "Rechercher des mises à jour",
      "Decktation update available": "Mise à jour de Decktation disponible",
      "Could not check for updates.": "Impossible de rechercher des mises à jour.",
      "The update could not be verified, so it was not installed.": "La mise à jour n’a pas pu être vérifiée et n’a donc pas été installée.",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "L’installateur de plugins de Decky n’est pas disponible dans cette version. Effectuez une mise à jour manuelle avec le fichier ZIP de Decktation.",
      "An update is already being prepared.": "Une mise à jour est déjà en cours de préparation.",
      "Wait for the transcription model to finish loading.": "Attendez la fin du chargement du modèle de transcription.",
      "Finish the current dictation before updating.": "Terminez la dictée en cours avant de mettre à jour.",
      "Binding saved: {binding}": "Raccourci enregistré : {binding}",
      "Binding cancelled. Your previous binding is unchanged.": "Modification annulée. Le raccourci précédent est conservé.",
      "Could not start binding capture": "Impossible de démarrer la capture du raccourci",
      "Release all buttons to start listening.": "Relâchez tous les boutons pour commencer la capture.",
      "Hold your new combination together. Release to save.": "Maintenez la nouvelle combinaison. Relâchez pour enregistrer.",
      "Detected:": "Détecté :",
      "Listening…": "En attente…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "Un à cinq boutons. Steam et Accès rapide sont exclus. La capture expire après 20 secondes.",
      "Cancel (touch)": "Annuler (toucher)",
      "Change binding": "Modifier le raccourci",
      "Spoken punctuation": "Ponctuation dictée",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "En anglais ou en détection automatique, dites comma, period ou question mark pour insérer la ponctuation. Désactivez cette option pour écrire ces mots littéralement.",
      "Could not set spoken punctuation": "Impossible de configurer la ponctuation dictée",
      "Microphone troubleshooting": "Dépannage du microphone",
      "Microphone guide. Use Up and Down to scroll.": "Guide du microphone. Utilisez Haut et Bas pour faire défiler.",
      "Start with a dictation test": "Commencez par un test de dictée",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "Activez Decktation, attendez Prêt, puis lancez Tester la dictée (3 s) sur la page principale. Parlez clairement. Le résultat reste dans le panneau et n’est pas saisi dans le jeu.",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "Vérifiez que le microphone intégré ou le casque fonctionne dans une autre application. Si le son est clair dans Steam mais que la dictée échoue, vérifiez le périphérique d’enregistrement par défaut du système.",
      "If audio crackles, pops, or cuts out": "Si le son grésille, craque ou se coupe",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "Un utilisateur de Steam Deck LCD a constaté une amélioration après avoir désactivé le traitement vocal de Steam. Cette astuce communautaire n’est pas une solution garantie. Son effet sur l’entrée audio de Decktation n’a pas été établi.",
      "Open Steam → Power → Switch to Desktop.": "Ouvrez Steam → Marche/arrêt → Basculer vers le bureau.",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "Dans Steam, ouvrez Amis et chat → engrenage → Voix. Certaines versions proposent aussi Steam → Paramètres → Voix.",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "Sélectionnez votre périphérique d’entrée vocale. Lancez le test du microphone, parlez et écoutez les grésillements ou les mots manquants, puis arrêtez le test.",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "Notez vos réglages actuels. Dans les paramètres avancés, essayez de désactiver la réduction du bruit, l’annulation de l’écho et le contrôle automatique du volume ou du gain.",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "Répétez le test du microphone. Si le résultat s’améliore, réactivez les options une par une pour identifier le réglage utile.",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "Revenez au mode Jeu et répétez le test de dictée de trois secondes de Decktation avant de l’essayer dans un jeu.",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "Rétablissez les réglages précédents si cela n’aide pas. Désactiver le traitement peut augmenter le bruit de fond ou l’écho des haut-parleurs et affecter le chat vocal Steam.",
      "If the problem persists": "Si le problème persiste",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "Dans votre signalement, précisez le modèle de Deck (LCD ou OLED), les versions de SteamOS et du client Steam, le microphone ou le casque, et si l’amélioration persiste en mode Jeu et après un redémarrage. Consultez les erreurs du dernier journal du plugin.",
      "Open full guide online": "Ouvrir le guide complet en ligne",
      "Microphone help": "Aide du microphone",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "Voix non reconnue, mots manquants ou grésillements ? Consultez le guide du microphone ici.",
      "Having problems with your microphone?": "Des problèmes avec le microphone ?",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "Envoie à Sentry des erreurs expurgées des données sensibles, des compteurs d’utilisation et des mesures de performances, dont le moteur d’inférence et des informations générales sur l’appareil et le système. L’audio et les transcriptions restent en local.",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "Dites command gg pour saisir /gg, ou command ready pour /ready. Utilisez l’anglais ou la détection automatique. Les commandes respectent vos paramètres d’envoi.",
      "Binding timed out. Your previous binding is unchanged.": "Délai expiré. Le raccourci précédent est conservé.",
      "Controller disconnected. Your previous binding is unchanged.": "Manette déconnectée. Le raccourci précédent est conservé.",
      "Use at most five buttons.": "Utilisez cinq boutons au maximum.",
      "Finish recording before changing the binding.": "Terminez l’enregistrement avant de modifier le raccourci.",
      "Controller listener unavailable.": "Le service de détection des manettes est indisponible.",
      "Binding session ended.": "La session de configuration du raccourci est terminée."
    };

    var Back = "返回";
    var Enable = "启用";
    var Language = "听写语言";
    var Binding = "按键组合";
    var Result = "结果";
    var Model = "模型";
    var Sending = "发送";
    var Confirm = "发送前确认";
    var Manual = "手动发送";
    var Feedback = "提示";
    var Toast = "通知消息";
    var Overlay = "屏幕指示器";
    var None = "无";
    var Diagnostics = "诊断";
    var Controller = "控制器";
    var Yes = "是";
    var No = "否";
    var Backend = "插件服务";
    var Ready = "就绪";
    var Unavailable = "不可用";
    var Loading = "正在加载";
    var Share = "分享";
    var Permissions = "权限";
    var Recording = "录音";
    var Generic = "通用文本输入";
    var Interface = "界面";
    var Mode = "模式";
    var Send = "发送";
    var Cancel = "取消";
    var Updates = "更新";
    var zh = {
      Back: Back,
      Enable: Enable,
      "Quick settings": "快捷设置",
      Language: Language,
      Binding: Binding,
      "Edit Bindings": "编辑按键",
      "Try it": "试用听写",
      "Recording...": "正在录音…",
      "Transcribing...": "正在识别…",
      "Test Dictation (3s)": "测试听写（3 秒）",
      "Shows a transcription here without sending text to your game.": "在此显示识别结果，不会向游戏发送文本。",
      Result: Result,
      "No speech detected": "未检测到语音",
      "Advanced settings": "高级设置",
      "Transcription model": "语音识别模型",
      Model: Model,
      "Recording binding": "录音按键",
      Sending: Sending,
      Confirm: Confirm,
      "Delay before send": "发送前等待",
      Manual: Manual,
      "You press Enter": "按 Enter 键发送",
      "Remember channel": "记住频道",
      "Reuse the last spoken channel": "使用上次指定的频道",
      Feedback: Feedback,
      "Recording cue": "录音提示",
      Toast: Toast,
      Overlay: Overlay,
      None: None,
      "Haptic feedback": "振动反馈",
      "Cues on the controller when recording starts and stops": "录音开始和结束时让控制器振动",
      Diagnostics: Diagnostics,
      "Help & permissions": "帮助与权限",
      "Input and service": "输入与服务",
      Controller: Controller,
      "Binding supported": "支持此按键组合",
      Yes: Yes,
      No: No,
      "Held buttons": "正在按下的按键",
      "Keyboard helper": "键盘服务",
      Backend: Backend,
      Ready: Ready,
      Unavailable: Unavailable,
      Loading: Loading,
      "Diagnostics sharing": "分享诊断信息",
      Share: Share,
      "Optional scrubbed diagnostics sent to Sentry": "可选择将过滤后的诊断数据发送至 Sentry",
      "How to use": "使用方法",
      Permissions: Permissions,
      "Auto Detect": "自动检测",
      "Popular Steam languages": "Steam 常用语言",
      "Other languages": "其他语言",
      "Add Button": "添加按键",
      "Button {number}": "按键 {number}",
      "Remove button {number}": "删除按键 {number}",
      "Hold {binding} to record": "按住 {binding} 录音",
      "Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.": "{together}按住 {binding} 录音。松开后，识别结果会输入到当前游戏或应用中。请保持该窗口在前台。",
      "together ": "同时",
      "Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command.": "Decktation 使用 Decky 的 root 权限读取控制器按键，并为听写文本生成键盘输入事件。文本作为数据传给键盘服务，绝不会作为 shell 命令执行。",
      "Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.": "Base 速度最快。Small 兼顾速度与准确度。Medium 更准确，但速度较慢，首次使用时可能需要下载。",
      "whisper.cpp runs on the GPU via Vulkan.": "whisper.cpp 通过 Vulkan 使用 GPU。",
      "whisper.cpp runs on the CPU.": "whisper.cpp 使用 CPU。",
      "Connecting to Decktation...": "正在连接 Decktation…",
      "Keyboard helper unavailable. Reload or reinstall Decktation.": "键盘服务不可用。请重新加载或重新安装 Decktation。",
      "Loading transcription model...": "正在加载语音识别模型…",
      "Decktation is off": "Decktation 已关闭",
      "Model not ready": "模型尚未就绪",
      "Controller unavailable": "控制器不可用",
      "Backend unavailable: {error}": "服务不可用：{error}",
      "Recording for 3 seconds...": "正在录音，持续 3 秒…",
      Recording: Recording,
      "Sending in {seconds}s": "{seconds} 秒后发送",
      "\"{text}\" — hold PTT to cancel": "“{text}” — 按住录音按键取消",
      "Interface language": "界面语言",
      "Automatic (system)": "自动（Steam）",
      "Only changes the menu language, not the dictation language.": "仅更改菜单语言，不会更改听写语言。",
      Generic: Generic,
      "Base · Fast": "Base · 快速",
      "Small · Balanced": "Small · 均衡",
      "Medium · More accurate": "Medium · 更准确",
      "Could not start test recording": "无法开始测试录音",
      "Could not transcribe test recording": "无法识别测试录音",
      "Could not read test transcription": "无法读取测试结果",
      "Could not update enabled state": "无法更改 Decktation 的启用状态",
      "Could not load Whisper model": "无法加载 Whisper 模型",
      "Could not remove button": "无法删除按键",
      "Could not update channel setting": "无法更改频道设置",
      "Could not update recording cue": "无法更改录音提示",
      "Could not update haptic feedback": "无法更改振动设置",
      "Could not update diagnostics setting": "无法更改诊断设置",
      "Could not update game": "无法更改模式",
      "Could not update model size": "无法更改模型",
      "Could not update binding": "无法更改按键组合",
      "Could not update language": "无法更改语言",
      "L1 Bumper": "L1 (肩键)",
      "R1 Bumper": "R1 (肩键)",
      "L2 Trigger": "L2 (扳机)",
      "R2 Trigger": "R2 (扳机)",
      "L4 Grip": "L4 (背键)",
      "R4 Grip": "R4 (背键)",
      "L5 Grip": "L5 (背键)",
      "R5 Grip": "R5 (背键)",
      "Waiting for input": "等待输入",
      "Status unavailable": "状态不可用",
      "Backend status request failed": "无法获取服务状态",
      "Could not update language setting": "无法更改听写语言",
      Interface: Interface,
      Mode: Mode,
      "Review transcription": "检查转录文本",
      "Transcription sending": "转录文本发送方式",
      "Send immediately": "立即发送",
      "Review before sending": "发送前检查",
      "Send after countdown": "倒计时后发送",
      "Press Enter yourself": "自行按 Enter",
      "Type into chat without submitting": "输入到聊天框但不发送",
      Send: Send,
      Cancel: Cancel,
      "Type into chat": "输入到聊天框",
      "Review confirmation": "检查确认状态",
      "After typing, press Enter in the game": "输入后，请在游戏中按 Enter",
      "Open Decktation to retry": "打开 Decktation 重试",
      "Could not approve draft": "无法确认草稿",
      "Could not cancel draft": "无法取消草稿",
      "Could not update sending mode": "无法更改发送方式",
      "Transcription. Use Up and Down to scroll.": "转录文本。使用上、下按钮滚动。",
      "Closes this menu before typing into your game. Keep your game in the foreground.": "先关闭此菜单，再向游戏输入文本。请保持游戏位于前台。",
      "Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.": "预览会一直显示，直到你做出决定。短按 {binding} 发送，长按取消。打开 Decktation 检查较长的文本。",
      "“{text}” — open Decktation to review, send or cancel": "“{text}” — 打开 Decktation 进行检查、发送或取消",
      "Typing transcription…": "正在输入转录文本…",
      "Open Decktation to retry typing": "打开 Decktation 重试输入",
      "Open Decktation to review and send": "打开 Decktation 检查并发送",
      "Open Decktation to review all": "打开 Decktation 检查全部文本",
      "Close Steam menus and return to your game": "关闭 Steam 菜单并返回游戏",
      "Open Decktation to confirm sending": "打开 Decktation 确认发送",
      "Update available": "有可用更新",
      "Preparing update...": "正在准备更新...",
      "Waiting for Decky confirmation...": "等待 Decky 确认...",
      "Update to {version}": "更新到 {version}",
      Updates: Updates,
      "Version {version}": "版本 {version}",
      "Update available: {version}": "有可用更新：{version}",
      "Up to date": "已是最新版本",
      "Checking for updates...": "正在检查更新...",
      "Check again": "再次检查",
      "Check for updates": "检查更新",
      "Decktation update available": "Decktation 有可用更新",
      "Could not check for updates.": "无法检查更新。",
      "The update could not be verified, so it was not installed.": "无法验证更新，因此未安装。",
      "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.": "此版本无法使用 Decky 插件安装程序。请使用 Decktation ZIP 文件手动更新。",
      "An update is already being prepared.": "正在准备更新。",
      "Wait for the transcription model to finish loading.": "请等待转录模型加载完成。",
      "Finish the current dictation before updating.": "请先完成当前听写再更新。",
      "Binding saved: {binding}": "已保存按键组合：{binding}",
      "Binding cancelled. Your previous binding is unchanged.": "已取消更改，原按键组合保持不变。",
      "Could not start binding capture": "无法开始检测按键组合",
      "Release all buttons to start listening.": "松开所有按键以开始检测。",
      "Hold your new combination together. Release to save.": "按住新的组合，松开即可保存。",
      "Detected:": "已检测到：",
      "Listening…": "等待输入…",
      "One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds.": "可使用一至五个按键，不包括 Steam 和快捷访问键。检测将在 20 秒后结束。",
      "Cancel (touch)": "取消（触摸）",
      "Change binding": "更改按键组合",
      "Spoken punctuation": "语音标点",
      "With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.": "使用英语或自动检测时，说出 comma、period 或 question mark 可插入标点。关闭后将按字面输入这些单词。",
      "Could not set spoken punctuation": "无法设置语音标点",
      "Microphone troubleshooting": "麦克风故障排查",
      "Microphone guide. Use Up and Down to scroll.": "麦克风指南。使用上、下键滚动。",
      "Start with a dictation test": "先进行听写测试",
      "Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.": "启用 Decktation，等待显示就绪，然后在主页面运行听写测试（3 秒）。请清晰说话。结果保留在面板中，不会输入到游戏。",
      "Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.": "检查内置麦克风或耳麦在其他应用中是否正常。如果 Steam 中声音清晰但听写失败，请检查系统默认录音设备。",
      "If audio crackles, pops, or cuts out": "如果声音有杂音、爆音或中断",
      "A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.": "一位 Steam Deck LCD 用户反馈，关闭 Steam 语音处理后有所改善。这是社区提供的临时办法，不保证有效。其对 Decktation 音频输入的影响尚未确定。",
      "Open Steam → Power → Switch to Desktop.": "打开 Steam → 电源 → 切换到桌面。",
      "In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.": "在 Steam 中打开好友与聊天 → 齿轮图标 → 语音。部分版本也可通过 Steam → 设置 → 语音打开。",
      "Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.": "选择语音输入设备。启动麦克风测试，说话并听是否有杂音或漏词，然后停止测试。",
      "Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.": "记下当前设置。在高级设置中，尝试关闭噪声消除、回声消除和自动音量或增益控制。",
      "Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.": "再次测试麦克风。如果有改善，逐一重新启用选项以确定有效的设置。",
      "Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game.": "返回游戏模式，在游戏中尝试之前再次运行 Decktation 的三秒听写测试。",
      "Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.": "如果无效，请恢复之前的设置。关闭处理可能增加背景噪声或扬声器回声，并影响 Steam 语音聊天。",
      "If the problem persists": "如果问题仍然存在",
      "Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.": "报告问题时，请提供 Deck 型号（LCD 或 OLED）、SteamOS 和 Steam 客户端版本、麦克风或耳麦，以及改善是否在游戏模式和重启后仍然有效。检查最新插件日志中的错误。",
      "Open full guide online": "在线打开完整指南",
      "Microphone help": "麦克风帮助",
      "Voice not recognized, missing words, or crackling audio? Read the microphone guide here.": "无法识别语音、漏词或声音有杂音？请查看这里的麦克风指南。",
      "Having problems with your microphone?": "麦克风有问题？",
      "Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local.": "向 Sentry 发送已清除敏感信息的错误、使用次数和性能指标，包括推理后端及大致的设备和系统信息。音频和转录文本保留在本地。",
      "Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.": "说出 command gg 可输入 /gg，说出 command ready 可输入 /ready。请使用英语或自动检测。命令遵循您的发送设置。",
      "Binding timed out. Your previous binding is unchanged.": "检测已超时，原按键组合保持不变。",
      "Controller disconnected. Your previous binding is unchanged.": "控制器已断开，原按键组合保持不变。",
      "Use at most five buttons.": "最多可使用五个按键。",
      "Finish recording before changing the binding.": "更改按键组合前请先结束录音。",
      "Controller listener unavailable.": "控制器输入服务不可用。",
      "Binding session ended.": "按键组合设置会话已结束。"
    };

    const catalogs = { en: en$1, es, ru, pt, pl, ko, ja, de, fr, zh };
    const INTERFACE_LANGUAGE_OPTIONS = [
        { data: "en", label: "English" }, { data: "es", label: "Español" },
        { data: "ru", label: "Русский" }, { data: "pt", label: "Português" },
        { data: "pl", label: "Polski" }, { data: "ko", label: "한국어" },
        { data: "ja", label: "日本語" }, { data: "de", label: "Deutsch" },
        { data: "fr", label: "Français" }, { data: "zh", label: "中文（简体）" },
    ];
    function isLocale(value) {
        return typeof value === "string" && Object.prototype.hasOwnProperty.call(catalogs, value);
    }
    const STORAGE_KEY = "decktation.interfaceLanguage";
    let preference = "auto";
    let steamLanguage;
    try {
        const saved = window.localStorage.getItem(STORAGE_KEY);
        if (isLocale(saved))
            preference = saved;
    }
    catch (_) { /* Storage may be unavailable in the Steam renderer. */ }
    function getInterfacePreference() { return preference; }
    function setInterfacePreference(value) {
        if (value !== "auto" && !isLocale(value))
            return;
        preference = value;
        try {
            window.localStorage.setItem(STORAGE_KEY, value);
        }
        catch (_) { }
    }
    function resolveLocale(value, systemLanguage) {
        if (value !== "auto")
            return value;
        const steamNames = {
            english: "en", spanish: "es", latam: "es", russian: "ru",
            portuguese: "pt", brazilian: "pt", polish: "pl", koreana: "ko", korean: "ko",
            japanese: "ja", german: "de", french: "fr", schinese: "zh", tchinese: "zh",
        };
        const name = systemLanguage.toLowerCase();
        const code = name.split(/[-_]/)[0];
        return steamNames[name] || (isLocale(code) ? code : "en");
    }
    async function initializeSteamLanguage() {
        let timer;
        try {
            const settings = window.SteamClient?.Settings;
            if (typeof settings?.GetCurrentLanguage !== "function")
                return;
            const value = await Promise.race([
                settings.GetCurrentLanguage(),
                new Promise(resolve => { timer = setTimeout(() => resolve(undefined), 1500); }),
            ]);
            if (typeof value === "string" && value)
                steamLanguage = value;
        }
        catch (_) { /* Use navigator.language if Steam cannot provide its locale. */ }
        finally {
            if (timer !== undefined)
                clearTimeout(timer);
        }
    }
    function locale() {
        return resolveLocale(preference, steamLanguage || (typeof navigator === "undefined" ? "en" : navigator.language));
    }
    function t(key, values = {}) {
        const english = en$1;
        const translated = catalogs[locale()];
        const text = translated[key] || english[key] || key;
        return text.replace(/\{(\w+)\}/g, (match, name) => values[name] === undefined ? match : String(values[name]));
    }
    function languageName(code, fallback) {
        if (code === "auto")
            return t("Auto Detect");
        // Autonyms are independent of the interface locale and ICU/browser data.
        // Keep Whisper codes untouched; only change the displayed names.
        return nativeLanguageNames[code] || fallback;
    }

    const setOverlayLabel = callable("set_overlay_transcribing_label");
    const syncOverlayLanguage = () => setOverlayLabel(t("Transcribing...")).catch(() => { });
    const getPluginUpdate = callable("get_plugin_update");
    const preparePluginUpdate = callable("prepare_plugin_update");
    const getStatus = callable("get_status");
    const startBindingCapture = callable("start_binding_capture");
    const getBindingCapture = callable("get_binding_capture");
    const cancelBindingCapture = callable("cancel_binding_capture");
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
    const setSpokenPunctuationRpc = callable("set_spoken_punctuation");
    const setTranscriptionOptionsRpc = callable("set_transcription_options");
    class DecktationLogic {
        constructor() {
            this.updateAvailable = false;
            this.updateListeners = new Set();
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
                        this.notify("Decktation", 1000, t("Recording for 3 seconds..."));
                    const started = await startRecording();
                    if (!started.success)
                        throw new Error(started.error || t("Could not start test recording"));
                    await new Promise(resolve => setTimeout(resolve, 3000));
                    // Keep the no-send argument: test text must never reach the active game.
                    onPhase("transcribing");
                    const transcription = stopRecording(false);
                    if (this.recordingIndicator === "toast")
                        this.notify("Decktation", 1500, t("Transcribing..."));
                    const stopped = await transcription;
                    if (!stopped.success)
                        throw new Error(stopped.error || t("Could not transcribe test recording"));
                    const result = await getLastTranscription();
                    if (!result.success)
                        throw new Error(result.error || t("Could not read test transcription"));
                    const data = result.transcription;
                    onComplete(data?.text || "", data?.timestamp ? new Date(data.timestamp * 1000).toLocaleTimeString() : "");
                }
                finally {
                    onPhase("idle");
                }
            };
        }
        setUpdateAvailable(available) {
            this.updateAvailable = available;
            this.updateListeners.forEach(listener => listener(available));
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
        const [interfaceLanguage, updateInterfaceLanguage] = React.useState(getInterfacePreference);
        const [, refreshLocale] = React.useState(0);
        React.useEffect(() => {
            let mounted = true;
            void initializeSteamLanguage().then(() => { if (mounted) {
                refreshLocale(value => value + 1);
                void syncOverlayLanguage();
            } });
            return () => { mounted = false; };
        }, []);
        const [page, setPage] = React.useState("main");
        const panelRef = React.useRef(null);
        const languageMenuAnchorRef = React.useRef(null);
        const advancedModelRowRef = React.useRef(null);
        const updateActionRowRef = React.useRef(null);
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
        const [controllerStatus, setControllerStatus] = React.useState("Waiting for input");
        const [controllerComboSupported, setControllerComboSupported] = React.useState(true);
        const [buttons, setButtons] = React.useState(["L1", "R1"]);
        const [recordingIndicator, setRecordingIndicator] = React.useState("toast");
        const [hapticFeedback, setHapticFeedback] = React.useState(false);
        const [activePreset, setActivePreset] = React.useState("wow");
        const [presets, setPresets] = React.useState([]);
        const [sendingMode, setSendingMode] = React.useState("immediate");
        const [pendingDraft, setPendingDraft] = React.useState(null);
        const microphoneHelpRef = React.useRef(null);
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
        const [spokenPunctuation, setSpokenPunctuation] = React.useState(false);
        const [lastTranscription, setLastTranscription] = React.useState("");
        const [lastTranscriptionTime, setLastTranscriptionTime] = React.useState("");
        const [rpcError, setRpcError] = React.useState("");
        const [reviewBlockReason, setReviewBlockReason] = React.useState("");
        const [statusError, setStatusError] = React.useState("");
        const [testPhase, setTestPhase] = React.useState("idle");
        const [hasTestResult, setHasTestResult] = React.useState(false);
        const [transcribing, setTranscribing] = React.useState(false);
        const [updateInfo, setUpdateInfo] = React.useState(null);
        const [updateError, setUpdateError] = React.useState("");
        const [updatePhase, setUpdatePhase] = React.useState("idle");
        const [checkingUpdate, setCheckingUpdate] = React.useState(false);
        const updateChecked = React.useRef(false);
        const updateMounted = React.useRef(true);
        const updateInFlight = React.useRef(false);
        const updateTimer = React.useRef();
        const checkUpdate = async (force = false) => {
            setCheckingUpdate(true);
            try {
                const result = await getPluginUpdate(force);
                if (!updateMounted.current)
                    return;
                setUpdateInfo(result);
                logic.setUpdateAvailable(result.success && result.update_available === true);
                setUpdateError(result.success ? "" : t("Could not check for updates."));
            }
            catch (_error) {
                if (updateMounted.current) {
                    setUpdateInfo(null);
                    logic.setUpdateAvailable(false);
                    setUpdateError(t("Could not check for updates."));
                }
            }
            finally {
                if (updateMounted.current)
                    setCheckingUpdate(false);
            }
        };
        React.useEffect(() => {
            updateMounted.current = true;
            return () => {
                updateMounted.current = false;
                if (updateTimer.current)
                    clearTimeout(updateTimer.current);
            };
        }, []);
        React.useEffect(() => {
            if (qamVisible && !updateChecked.current) {
                updateChecked.current = true;
                void checkUpdate();
            }
        }, [qamVisible]);
        const updateBusy = recording || transcribing || modelLoading || testPhase !== "idle" ||
            !!pendingDraft || !!capture || draftBusy || updatePhase !== "idle";
        const startUpdate = async () => {
            if (updateBusy || updateInFlight.current || !updateInfo?.update_available || logic.readQamVisibility?.() !== true)
                return;
            updateInFlight.current = true;
            setUpdatePhase("preparing");
            setUpdateError("");
            try {
                const prepared = await preparePluginUpdate(updateInfo.version);
                if (!updateMounted.current || logic.readQamVisibility?.() !== true)
                    return;
                if (!prepared.success) {
                    setUpdateError(t(prepared.error || "The update could not be verified, so it was not installed."));
                    return;
                }
                const result = await requestPluginUpdate({ artifact: prepared.artifact, version: prepared.version, hash: prepared.hash });
                if (!updateMounted.current)
                    return;
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
            }
            catch (_error) {
                if (updateMounted.current)
                    setUpdateError(t("The update could not be verified, so it was not installed."));
            }
            finally {
                if (!updateTimer.current) {
                    updateInFlight.current = false;
                    if (updateMounted.current)
                        setUpdatePhase("idle");
                }
            }
        };
        React.useEffect(() => {
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
                        setTranscribing(result.transcribing === true);
                        setInputReady(result.input_ready !== false);
                        if (logic.enabled) {
                            setRecording(result.recording);
                        }
                    }
                    else {
                        setControllerReady(false);
                        setControllerStatus("Status unavailable");
                        setStatusError(result.error || t("Backend status request failed"));
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
                if (page === "microphone-help") {
                    if (microphoneHelpRef.current) {
                        microphoneHelpRef.current.scrollTop = 0;
                        microphoneHelpRef.current.focus();
                    }
                }
                if (page === "advanced" || page === "updates") {
                    (page === "updates" ? updateActionRowRef.current : advancedModelRowRef.current)?.querySelector('[role="button"], button')?.focus();
                }
            });
            return () => cancelAnimationFrame(frame);
        }, [page, pendingDraft?.id]);
        React.useEffect(() => {
            if (!qamVisible || !pendingDraft)
                return;
            const frame = requestAnimationFrame(() => {
                if (reviewTextRef.current) {
                    reviewTextRef.current.scrollTop = 0;
                    reviewTextRef.current.focus();
                }
            });
            return () => cancelAnimationFrame(frame);
        }, [qamVisible, pendingDraft?.id]);
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
                            setBindingMessage(t("Binding saved: {binding}", { binding: result.buttons.join(" + ") }));
                        }
                        else
                            setRpcError(t(result.error || "Binding cancelled. Your previous binding is unchanged."));
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
                    setRpcError(t(result.error || "Could not start binding capture"));
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
        const scrollMicrophoneHelp = (direction) => {
            const node = microphoneHelpRef.current;
            if (!node || (direction < 0 ? node.scrollTop <= 0 : node.scrollTop + node.clientHeight >= node.scrollHeight - 1))
                return false;
            node.scrollTop += direction * 96;
            return true;
        };
        const goBack = () => setPage(page === "microphone-help" ? "diagnostics" : page === "updates" || page === "diagnostics" || page === "help" || page === "model" ? "advanced" : "main");
        const chooseLanguage = async (language) => {
            const result = await setTranscriptionOptionsRpc(language);
            if (result.success) {
                setTranscriptionLanguage(language);
                setRpcError("");
            }
            else {
                setRpcError(result.error || t("Could not update language setting"));
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
        const statusMessage = statusError ? t("Backend unavailable: {error}", { error: statusError })
            : rpcError ? rpcError
                : !serviceReady ? t("Connecting to Decktation...")
                    : !inputReady ? t("Keyboard helper unavailable. Reload or reinstall Decktation.")
                        : recording ? t("Recording...")
                            : modelLoading ? t("Loading transcription model...")
                                : !enabled ? t("Decktation is off")
                                    : !modelReady ? t("Model not ready")
                                        : !controllerReady ? t("Controller unavailable")
                                            : t("Ready");
        const statusProblem = !!(statusError || rpcError || (serviceReady && !inputReady) || (enabled && serviceReady && !controllerReady));
        if (capture) {
            const swallow = (event) => { event.preventDefault(); event.stopPropagation(); };
            return React__default["default"].createElement(deckyFrontendLib.Focusable, { ref: captureFocusRef, tabIndex: 0, onButtonDown: swallow, onButtonUp: swallow, onOKButton: swallow, onCancelButton: swallow, onGamepadDirection: swallow, onActivate: swallow, onCancel: swallow },
                React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Recording binding") },
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { role: "status" }, capture.phase === "release"
                            ? t("Release all buttons to start listening.")
                            : t("Hold your new combination together. Release to save."))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", null,
                            t("Detected:"),
                            " ",
                            React__default["default"].createElement("strong", null, capture.buttons.join(" + ") || t("Listening…")))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { style: { fontSize: "12px", opacity: 0.85 } }, t("One to five buttons. Steam and Quick Access are excluded. Capture times out after 20 seconds."))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("button", { tabIndex: -1, onClick: () => { void cancelCapture(); }, style: { padding: "10px 20px", color: "white", background: "#3b4252", border: 0, borderRadius: "4px" } }, t("Cancel (touch)")))));
        }
        return (React__default["default"].createElement(deckyFrontendLib.Focusable, { onCancel: page === "main" ? undefined : (event) => {
                event.stopPropagation();
                goBack();
            }, onCancelActionDescription: page === "main" ? undefined : t("Back") },
            React__default["default"].createElement("div", { ref: panelRef },
                React__default["default"].createElement("style", null, `.decktation-trash-focused { outline: 3px solid #66c0f4 !important; outline-offset: 2px; background-color: #456b90 !important; box-shadow: 0 0 0 2px rgba(102, 192, 244, 0.38) !important; }`),
                pendingDraft && React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Review transcription") },
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.Focusable, { ref: reviewTextRef, tabIndex: 0, "aria-label": t("Transcription. Use Up and Down to scroll."), style: { fontSize: '16px', lineHeight: '1.5', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: '260px', overflowY: 'auto', padding: '4px' }, onGamepadDirection: (event) => {
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
                            t(pendingDraft.destination),
                            pendingDraft.manual ? " · " + t("After typing, press Enter in the game") : "")),
                    pendingDraft.error && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { role: "alert" }, t(pendingDraft.error))),
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
                                        setRpcError(result.error || t("Could not approve draft"));
                                }
                                catch (error) {
                                    setRpcError(String(error));
                                }
                                finally {
                                    setDraftBusy(false);
                                }
                            } }, t(pendingDraft.action))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement("div", { style: { fontSize: '12px' } }, t("Closes this menu before typing into your game. Keep your game in the foreground."))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", disabled: draftBusy || pendingDraft.sending, onClick: async () => {
                                setDraftBusy(true);
                                try {
                                    const result = await cancelDraftRpc(pendingDraft.id);
                                    if (result.success)
                                        setPendingDraft(null);
                                    else
                                        setRpcError(result.error || t("Could not cancel draft"));
                                }
                                catch (error) {
                                    setRpcError(String(error));
                                }
                                finally {
                                    setDraftBusy(false);
                                }
                            } }, t("Cancel")))),
                page !== "main" && (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                    React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: goBack }, t("Back")))),
                page === "main" && React__default["default"].createElement(React__default["default"].Fragment, null,
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Decktation" },
                        updateInfo?.success && updateInfo.update_available && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("updates") },
                                React__default["default"].createElement("span", { style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" } },
                                    React__default["default"].createElement(FaArrowCircleUp, { "aria-hidden": "true", style: { color: "#7cdb98", flexShrink: 0 } }),
                                    React__default["default"].createElement("span", null, t("Update available: {version}", { version: updateInfo.version }))))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: t("Enable"), checked: enabled, disabled: !serviceReady || modelLoading || isToggling, onChange: async (next) => {
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
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Quick settings") },
                        presets.length > 0 && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("game") },
                                t("Mode"),
                                ": ",
                                t(String(presets.find(option => option.data === activePreset)?.label || activePreset)))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { position: 'relative', width: '100%' } },
                                React__default["default"].createElement("span", { ref: languageMenuAnchorRef, "aria-hidden": "true", style: { position: 'absolute', left: 0, top: 0, width: '1px', height: '1px', pointerEvents: 'none' } }),
                                React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: (event) => {
                                        deckyFrontendLib.showContextMenu(React__default["default"].createElement(deckyFrontendLib.Menu, { label: t("Language") },
                                            React__default["default"].createElement(deckyFrontendLib.MenuItem, { selected: transcriptionLanguage === "auto", onSelected: () => { void chooseLanguage("auto"); } }, t("Auto Detect")),
                                            React__default["default"].createElement("div", { className: deckyFrontendLib.gamepadContextMenuClasses.ContextMenuSeparator }),
                                            React__default["default"].createElement("div", { className: deckyFrontendLib.gamepadContextMenuClasses.MenuSectionHeader }, t("Popular Steam languages")),
                                            POPULAR_LANGUAGE_OPTIONS.map(option => React__default["default"].createElement(deckyFrontendLib.MenuItem, { key: String(option.data), selected: option.data === transcriptionLanguage, onSelected: () => { void chooseLanguage(String(option.data)); } }, languageName(String(option.data), String(option.label)))),
                                            React__default["default"].createElement("div", { className: deckyFrontendLib.gamepadContextMenuClasses.ContextMenuSeparator }),
                                            React__default["default"].createElement("div", { className: deckyFrontendLib.gamepadContextMenuClasses.MenuSectionHeader }, t("Other languages")),
                                            OTHER_LANGUAGE_OPTIONS.map(option => React__default["default"].createElement(deckyFrontendLib.MenuItem, { key: String(option.data), selected: option.data === transcriptionLanguage, onSelected: () => { void chooseLanguage(String(option.data)); } }, languageName(String(option.data), String(option.label))))), languageMenuAnchorRef.current || event.currentTarget || undefined);
                                    } },
                                    t("Language"),
                                    ": ",
                                    languageName(transcriptionLanguage, String(WHISPER_LANGUAGE_OPTIONS.find(option => option.data === transcriptionLanguage)?.label || transcriptionLanguage))))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                t("Binding"),
                                ": ",
                                React__default["default"].createElement("strong", null, buttons.join(' + ')))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", disabled: !controllerReady || recording || !!pendingDraft || testPhase !== "idle", onClick: beginCapture }, t("Change binding"))),
                        bindingMessage && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { role: "status" }, bindingMessage))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Try it") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: runTest, disabled: !enabled || !modelReady || modelLoading || recording || testPhase !== "idle" },
                                React__default["default"].createElement(FaMicrophone, { size: 14 }),
                                " ",
                                testPhase === "recording" ? t("Recording...") : testPhase === "transcribing" ? t("Transcribing...") : t("Test Dictation (3s)"))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '12px', opacity: 0.85 } }, t("Shows a transcription here without sending text to your game."))),
                        hasTestResult && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { role: "status", style: { padding: '10px', backgroundColor: '#233829', borderRadius: '6px', overflowWrap: 'anywhere' } },
                                React__default["default"].createElement("strong", null, t("Result")),
                                React__default["default"].createElement("div", null, lastTranscription || t("No speech detected")),
                                React__default["default"].createElement("small", null, lastTranscriptionTime)))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("advanced") }, t("Advanced settings")))),
                page === "updates" && React__default["default"].createElement(React__default["default"].Fragment, null,
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Updates") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null, t("Version {version}", { version: updateInfo?.current || version }))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { role: "status" }, updateError || (updateInfo?.success ?
                                updateInfo.update_available ? t("Update available: {version}", { version: updateInfo.version }) : t("Up to date") : t("Checking for updates...")))),
                        updateInfo?.success && updateInfo.update_available && React__default["default"].createElement(React__default["default"].Fragment, null,
                            React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                                React__default["default"].createElement("div", null,
                                    updateInfo.current,
                                    " \u2192 ",
                                    updateInfo.version)),
                            React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                                React__default["default"].createElement("div", { ref: updateActionRowRef },
                                    React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", disabled: updateBusy, onClick: startUpdate }, updatePhase === "preparing" ? t("Preparing update...") : updatePhase === "waiting" ? t("Waiting for Decky confirmation...") : t("Update to {version}", { version: updateInfo.version }))))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { ref: updateInfo?.update_available ? undefined : updateActionRowRef },
                                React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", disabled: checkingUpdate || updatePhase !== "idle", onClick: () => { void checkUpdate(true); } }, t("Check again")))))),
                page === "advanced" && React__default["default"].createElement(React__default["default"].Fragment, null,
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Interface") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: t("Interface language"), menuLabel: t("Interface language"), rgOptions: [{ data: "auto", label: t("Automatic (system)") }, ...INTERFACE_LANGUAGE_OPTIONS], selectedOption: interfaceLanguage, onChange: (option) => {
                                    const next = option.data;
                                    setInterfacePreference(next);
                                    updateInterfaceLanguage(next);
                                    refreshLocale(value => value + 1);
                                    void syncOverlayLanguage();
                                } }))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Transcription model") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { ref: advancedModelRowRef },
                                React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("model") },
                                    t("Model"),
                                    ": ",
                                    t(String(MODEL_SIZE_OPTIONS.find(option => option.data === modelSize)?.label || modelSize))))),
                        modelReady && !modelLoading && inferenceDevice && (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null, inferenceDevice === "gpu"
                                ? t("whisper.cpp runs on the GPU via Vulkan.")
                                : t("whisper.cpp runs on the CPU.")))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '12px' } }, t("Base is fastest. Small balances speed and accuracy. Medium is more accurate but slower and may download on first use.")))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Sending") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: t("Transcription sending"), menuLabel: t("Transcription sending"), rgOptions: [{ data: "immediate", label: t("Send immediately") }, { data: "review", label: t("Review before sending") }, { data: "countdown", label: t("Send after countdown") }], selectedOption: sendingMode, onChange: async (option) => {
                                    const next = option.data;
                                    const result = await setSendingModeRpc(next);
                                    if (result.success) {
                                        setSendingMode(next);
                                        setRpcError("");
                                    }
                                    else
                                        setRpcError(result.error || t("Could not update sending mode"));
                                } })),
                        sendingMode === "review" && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '13px', lineHeight: '1.5' } }, t("Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.", { binding: buttons.join("+") }))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: t("Press Enter yourself"), description: t("Type into chat without submitting"), checked: manualSend, onChange: async (next) => { setManualSend(next); await setManualSendRpc(next); } })),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: t("Remember channel"), description: t("Reuse the last spoken channel"), checked: rememberLastChannel, onChange: async (next) => {
                                    setRememberLastChannel(next);
                                    const result = await setRememberLastChannelRpc(next);
                                    if (!result.success) {
                                        setRememberLastChannel(!next);
                                        setRpcError(result.error || t("Could not update channel setting"));
                                    }
                                } })),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: t("Spoken punctuation"), checked: spokenPunctuation, description: t("With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally."), onChange: async (next) => {
                                    try {
                                        const result = await setSpokenPunctuationRpc(next);
                                        if (result.success) {
                                            setSpokenPunctuation(next);
                                            setRpcError("");
                                        }
                                        else
                                            setRpcError(result.error || t("Could not set spoken punctuation"));
                                    }
                                    catch (error) {
                                        setRpcError(String(error));
                                    }
                                } }))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Feedback") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: t("Recording cue"), menuLabel: t("Recording cue"), rgOptions: [{ data: "toast", label: t("Toast") }, { data: "overlay", label: t("Overlay") }, { data: "none", label: t("None") }], selectedOption: recordingIndicator, onChange: async (option) => { const mode = option.data; setRecordingIndicator(mode); logic.recordingIndicator = mode; const result = await setRecordingIndicatorRpc(mode); if (!result.success)
                                    setRpcError(result.error || t("Could not update recording cue")); } })),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: t("Haptic feedback"), description: t("Cues on the controller when recording starts and stops"), checked: hapticFeedback, onChange: async (next) => {
                                    const result = await setHapticFeedbackRpc(next);
                                    if (result.success)
                                        setHapticFeedback(next);
                                    else
                                        setRpcError(result.error || t("Could not update haptic feedback"));
                                } }))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => { setPage("updates"); void checkUpdate(true); } }, t("Check for updates"))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("diagnostics") }, t("Diagnostics"))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("help") }, t("Help & permissions")))),
                page === "microphone-help" && React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Microphone troubleshooting") },
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.Focusable, { ref: microphoneHelpRef, tabIndex: 0, "aria-label": t("Microphone guide. Use Up and Down to scroll."), style: { maxHeight: '300px', overflowY: 'auto', overflowWrap: 'anywhere', fontSize: '15px', lineHeight: '1.5', padding: '8px' }, onGamepadDirection: (event) => {
                                const direction = event.detail.button === deckyFrontendLib.GamepadButton.DIR_UP ? -1 : event.detail.button === deckyFrontendLib.GamepadButton.DIR_DOWN ? 1 : 0;
                                if (direction && scrollMicrophoneHelp(direction)) {
                                    event.preventDefault();
                                    event.stopPropagation();
                                }
                            }, onKeyDown: (event) => {
                                const direction = event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0;
                                if (direction && scrollMicrophoneHelp(direction)) {
                                    event.preventDefault();
                                    event.stopPropagation();
                                }
                            } },
                            React__default["default"].createElement("p", null,
                                React__default["default"].createElement("strong", null, t("Start with a dictation test"))),
                            React__default["default"].createElement("p", null, t("Enable Decktation, wait for Ready, then run Test Dictation (3s) on the main page. Speak clearly. The result stays in the panel and is not typed into your game.")),
                            React__default["default"].createElement("p", null, t("Check that your built-in microphone or headset works in another app. If Steam sounds clear but dictation fails, check the system default recording device.")),
                            React__default["default"].createElement("p", null,
                                React__default["default"].createElement("strong", null, t("If audio crackles, pops, or cuts out"))),
                            React__default["default"].createElement("p", null, t("A Steam Deck LCD user reported improvement after disabling Steam voice processing. This is a community workaround, not a guaranteed fix. Its effect on Decktation’s audio input has not been established.")),
                            React__default["default"].createElement("ol", { style: { paddingLeft: '24px' } },
                                React__default["default"].createElement("li", null, t("Open Steam → Power → Switch to Desktop.")),
                                React__default["default"].createElement("li", null, t("In Steam, open Friends & Chat → gear icon → Voice. Some versions also have Steam → Settings → Voice.")),
                                React__default["default"].createElement("li", null, t("Select your Voice Input Device. Run Start Microphone Test, speak, listen for crackling or missing words, then stop the test.")),
                                React__default["default"].createElement("li", null, t("Note your current settings. Under Show Advanced Settings, try turning off Noise Cancellation, Echo Cancellation and Automatic Volume/Gain Control.")),
                                React__default["default"].createElement("li", null, t("Repeat the microphone test. If it improves, re-enable the options one at a time to identify which setting helps.")),
                                React__default["default"].createElement("li", null, t("Return to Gaming Mode and repeat Decktation’s three-second dictation test before trying it in a game."))),
                            React__default["default"].createElement("p", null, t("Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and affect Steam voice chat.")),
                            React__default["default"].createElement("p", null,
                                React__default["default"].createElement("strong", null, t("If the problem persists"))),
                            React__default["default"].createElement("p", null, t("Include your Deck model (LCD or OLED), SteamOS and Steam client versions, microphone or headset, and whether any improvement survives Gaming Mode and a reboot when reporting the problem. Check the latest plugin log for errors.")))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                        React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => deckyFrontendLib.Router.NavigateToExternalWeb("https://github.com/silverfoxy/decktation/blob/master/doc/TROUBLESHOOTING.md#microphone-crackles-pops-or-cuts-out") }, t("Open full guide online")))),
                page === "diagnostics" && React__default["default"].createElement(React__default["default"].Fragment, null,
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Microphone help") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null, t("Voice not recognized, missing words, or crackling audio? Read the microphone guide here."))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setPage("microphone-help") }, t("Having problems with your microphone?")))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Input and service") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                t("Controller"),
                                ": ",
                                t(controllerStatus))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                t("Binding supported"),
                                ": ",
                                controllerComboSupported ? t("Yes") : t("No"))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                t("Held buttons"),
                                ": ",
                                React__default["default"].createElement("strong", null, t(buttonState)))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                t("Keyboard helper"),
                                ": ",
                                inputReady ? t("Ready") : t("Unavailable"))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                t("Backend"),
                                ": ",
                                serviceReady ? t("Ready") : t("Unavailable"))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                t("Model"),
                                ": ",
                                modelLoading ? t("Loading") : modelReady ? t("Ready") : t("Unavailable"))),
                        pendingDraft && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", null,
                                t("Review confirmation"),
                                ": ",
                                t(reviewBlockReason || "Ready"))),
                        (statusError || rpcError) && React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { role: "alert" }, statusError || rpcError))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Diagnostics sharing") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: t("Share"), description: t("Sends scrubbed errors, usage counts, and performance metrics to Sentry, including inference backend and coarse device/OS details. Audio and transcripts stay local."), checked: shareDiagnostics, onChange: async (next) => {
                                    setShareDiagnostics(next);
                                    const result = await setShareDiagnosticsRpc(next);
                                    if (!result.success) {
                                        setShareDiagnostics(!next);
                                        setRpcError(result.error || t("Could not update diagnostics setting"));
                                    }
                                } })))),
                page === "game" && React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Mode") },
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
                                    setRpcError(result.error || t("Could not update game"));
                            } },
                            option.data === activePreset ? "✓ " : "",
                            t(String(option.label)))))),
                page === "model" && React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Model") },
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
                                    setRpcError(result.error || t("Could not update model size"));
                                }
                            } },
                            option.data === modelSize ? "✓ " : "",
                            t(String(option.label)))))),
                page === "help" && React__default["default"].createElement(React__default["default"].Fragment, null,
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("How to use") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '13px', lineHeight: '1.6' } }, t("Hold {binding} {together}to record. Release to transcribe and type into the active game or app. Keep it in the foreground.", { binding: buttons.join("+"), together: buttons.length > 1 ? t("together ") : "" }))),
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '13px', lineHeight: '1.6' } }, t("Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.")))),
                    React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: t("Permissions") },
                        React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                            React__default["default"].createElement("div", { style: { fontSize: '13px', lineHeight: '1.5' } }, t("Decktation uses Decky root access only to read raw Steam Deck controller input and to create virtual keyboard events for dictated text. Your transcription is passed to the bundled keyboard helper as data, never as a shell command."))))))));
    };
    const DecktationIcon = ({ logic }) => {
        const [available, setAvailable] = React.useState(logic.updateAvailable);
        React.useEffect(() => {
            logic.updateListeners.add(setAvailable);
            setAvailable(logic.updateAvailable);
            return () => { logic.updateListeners.delete(setAvailable); };
        }, [logic]);
        return React__default["default"].createElement("span", { style: { position: "relative", display: "inline-flex" }, "aria-label": available ? t("Decktation update available") : "Decktation" },
            React__default["default"].createElement(FaMicrophone, null),
            available && React__default["default"].createElement("span", { "aria-hidden": "true", style: { position: "absolute", right: "-3px", top: "-3px", width: "7px", height: "7px", borderRadius: "50%", background: "#7cdb98" } }));
    };
    var index = deckyFrontendLib.definePlugin(() => {
        let logic = new DecktationLogic();
        let disposed = false;
        // One cached discovery check per plugin lifecycle, even before opening its panel.
        void getPluginUpdate(false).then(result => {
            if (!disposed)
                logic.setUpdateAvailable(result.success && result.update_available === true);
        }).catch(() => { });
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
                        void logic.notify(t("Review transcription"), 5000, sent.error || t("Open Decktation to retry"));
                }
                const result = await getStatus();
                if (result.success) {
                    const startCount = result.recording_start_count || 0;
                    if (logic.recordingIndicator === "toast" && startCount > logic.prevRecordingStartCount) {
                        logic.notify(t("Recording"), 1500, "🎤 " + t("Recording..."));
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
                        logic.lastPendingToastId = await logic.notify(t("Review transcription"), 6000, t("“{text}” — open Decktation to review, send or cancel", { text: draft.text }));
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
            icon: React__default["default"].createElement(DecktationIcon, { logic: logic }),
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

    return index;

})(DFL, SP_REACT);
