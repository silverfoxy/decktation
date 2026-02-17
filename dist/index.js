(function (deckyFrontendLib, React) {
  'use strict';

  function _interopDefaultLegacy (e) { return e && typeof e === 'object' && 'default' in e ? e : { 'default': e }; }

  var React__default = /*#__PURE__*/_interopDefaultLegacy(React);

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
  function FaCircle (props) {
    return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M256 8C119 8 8 119 8 256s111 248 248 248 248-111 248-248S393 8 256 8z"}}]})(props);
  }function FaMicrophone (props) {
    return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 352 512"},"child":[{"tag":"path","attr":{"d":"M176 352c53.02 0 96-42.98 96-96V96c0-53.02-42.98-96-96-96S80 42.98 80 96v160c0 53.02 42.98 96 96 96zm160-160h-16c-8.84 0-16 7.16-16 16v48c0 74.8-64.49 134.82-140.79 127.38C96.71 376.89 48 317.11 48 250.3V208c0-8.84-7.16-16-16-16H16c-8.84 0-16 7.16-16 16v40.16c0 89.64 63.97 169.55 152 181.69V464H96c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16h-56v-33.77C285.71 418.47 352 344.9 352 256v-48c0-8.84-7.16-16-16-16z"}}]})(props);
  }function FaTrash (props) {
    return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 448 512"},"child":[{"tag":"path","attr":{"d":"M432 32H312l-9.4-18.7A24 24 0 0 0 281.1 0H166.8a23.72 23.72 0 0 0-21.4 13.3L136 32H16A16 16 0 0 0 0 48v32a16 16 0 0 0 16 16h416a16 16 0 0 0 16-16V48a16 16 0 0 0-16-16zM53.2 467a48 48 0 0 0 47.9 45h245.8a48 48 0 0 0 47.9-45L416 128H32z"}}]})(props);
  }

  // L5 = bit 15, R5 = bit 16 in ulButtons (same as antiquitte/decky-dictation)
  const L5_MASK = 1 << 15;
  class DectationLogic {
      constructor(serverAPI) {
          this.enabled = false;
          this.recording = false;
          this.lastButtonState = "None";
          this.inputRegistered = false;
          this.inputError = "";
          this.onButtonChange = null;
          this.l5Held = false;
          this.showNotifications = true;
          this.prevRecordingStartCount = 0;
          this.prevPendingText = "";
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
                  this.serverAPI.toaster.toast({ title: message, body: toast.body, duration: duration, critical: false });
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
          // Handler for RegisterForControllerStateChanges (antiquitte style)
          this.handleControllerState = (val) => {
              if (!val || val.length === 0)
                  return;
              const inputs = val[0];
              if (!inputs)
                  return;
              const ulButtons = inputs.ulButtons || 0;
              const l5Pressed = (ulButtons & L5_MASK) !== 0;
              // Debug: show button state
              this.lastButtonState = l5Pressed ? "L5" : "None";
              if (this.onButtonChange)
                  this.onButtonChange();
              if (!this.enabled) {
                  return;
              }
              // Push-to-talk: L5 held = recording
              if (l5Pressed && !this.l5Held) {
                  this.l5Held = true;
                  this.recording = true;
                  // Disable system buttons temporarily
                  deckyFrontendLib.Router.DisableHomeAndQuickAccessButtons();
                  setTimeout(() => {
                      deckyFrontendLib.Router.EnableHomeAndQuickAccessButtons();
                  }, 1000);
                  this.serverAPI.callPluginMethod('start_recording', {});
                  this.notify("Decktation", 1500, "Recording...");
              }
              else if (!l5Pressed && this.l5Held) {
                  this.l5Held = false;
                  this.recording = false;
                  this.serverAPI.callPluginMethod('stop_recording', {});
                  this.notify("Decktation", 1500, "Transcribing...");
              }
          };
          // Fallback handler for RegisterForControllerInputMessages
          this.handleButtonInput = (controllerIndex, gamepadButton, isButtonPressed) => {
              // L5 = 44 in this API
              const buttonName = gamepadButton === 44 ? "L5" : `btn${gamepadButton}`;
              this.lastButtonState = isButtonPressed ? buttonName : "None";
              if (this.onButtonChange)
                  this.onButtonChange();
              if (!this.enabled) {
                  return;
              }
              if (gamepadButton === 44) { // L5
                  if (isButtonPressed && !this.recording) {
                      this.recording = true;
                      deckyFrontendLib.Router.DisableHomeAndQuickAccessButtons();
                      setTimeout(() => {
                          deckyFrontendLib.Router.EnableHomeAndQuickAccessButtons();
                      }, 1000);
                      this.serverAPI.callPluginMethod('start_recording', {});
                      this.notify("Decktation", 1500, "Recording...");
                  }
                  else if (!isButtonPressed && this.recording) {
                      this.recording = false;
                      this.serverAPI.callPluginMethod('stop_recording', {});
                      this.notify("Decktation", 1500, "Transcribing...");
                  }
              }
          };
          this.testRecording = async (onComplete) => {
              this.notify("Decktation", 1000, "Recording for 3 seconds...");
              await this.serverAPI.callPluginMethod('start_recording', {});
              // Wait 3 seconds
              await new Promise(resolve => setTimeout(resolve, 3000));
              await this.serverAPI.callPluginMethod('stop_recording', {});
              this.notify("Decktation", 1500, "Transcribing...");
              // Wait a bit for transcription to complete, then fetch result
              await new Promise(resolve => setTimeout(resolve, 1000));
              if (onComplete) {
                  const transcriptionResult = await this.serverAPI.callPluginMethod('get_last_transcription', {});
                  if (transcriptionResult.success && transcriptionResult.result) {
                      const data = transcriptionResult.result.transcription;
                      const text = data.text || "";
                      const time = data.timestamp ? new Date(data.timestamp * 1000).toLocaleTimeString() : "";
                      onComplete(text, time);
                  }
              }
          };
          this.serverAPI = serverAPI;
      }
  }
  // Available button options
  const BUTTON_OPTIONS = [
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
  const DectationPanel = ({ logic }) => {
      const [enabled, setEnabled] = React.useState(false);
      const [recording, setRecording] = React.useState(false);
      const [serviceReady, setServiceReady] = React.useState(false);
      const [modelReady, setModelReady] = React.useState(false);
      const [modelLoading, setModelLoading] = React.useState(false);
      const [buttonState, setButtonState] = React.useState("None");
      const [buttons, setButtons] = React.useState(["L1", "R1"]);
      const [showNotifications, setShowNotifications] = React.useState(true);
      const [activePreset, setActivePreset] = React.useState("wow");
      const [presets, setPresets] = React.useState([]);
      const [confirmMode, setConfirmMode] = React.useState(false);
      const [lastTranscription, setLastTranscription] = React.useState("");
      const [lastTranscriptionTime, setLastTranscriptionTime] = React.useState("");
      React.useEffect(() => {
          setEnabled(logic.enabled);
          setRecording(logic.recording);
          logic.onButtonChange = () => {
              setButtonState(logic.lastButtonState);
          };
          // Load button configuration, settings, and active game preset
          logic.serverAPI.callPluginMethod('get_button_config', {}).then(async (result) => {
              if (result.success && result.result) {
                  const config = result.result.config;
                  if (config) {
                      if (config.buttons) {
                          setButtons(config.buttons);
                      }
                      if (config.showNotifications !== undefined) {
                          setShowNotifications(config.showNotifications);
                          logic.showNotifications = config.showNotifications;
                      }
                      if (config.game) {
                          setActivePreset(config.game);
                      }
                      if (config.confirmMode !== undefined) {
                          setConfirmMode(config.confirmMode);
                      }
                      // Restore enabled state
                      if (config.enabled) {
                          setEnabled(true);
                          logic.enabled = true;
                          setModelLoading(true);
                          await logic.serverAPI.callPluginMethod('load_model', {});
                      }
                  }
              }
          });
          // Load available game presets
          logic.serverAPI.callPluginMethod('get_presets', {}).then((result) => {
              if (result.success && result.result) {
                  const opts = result.result.presets.map((p) => ({
                      data: p.id,
                      label: p.name,
                  }));
                  setPresets(opts);
              }
          });
          return () => {
              logic.onButtonChange = null;
          };
      }, []);
      React.useEffect(() => {
          const interval = setInterval(async () => {
              try {
                  const result = await logic.serverAPI.callPluginMethod('get_status', {});
                  if (result.success && result.result) {
                      setServiceReady(result.result.service_ready);
                      setModelReady(result.result.model_ready);
                      setModelLoading(result.result.model_loading);
                      if (logic.enabled) {
                          setRecording(result.result.recording);
                      }
                  }
              }
              catch (e) {
                  // Ignore transient WebSocket errors; next tick will retry
              }
          }, 100);
          return () => clearInterval(interval);
      }, [logic.enabled]);
      return (React__default["default"].createElement("div", null,
          React__default["default"].createElement(deckyFrontendLib.PanelSection, null,
              !serviceReady && (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: {
                          padding: '10px',
                          backgroundColor: '#2196f3',
                          borderRadius: '8px',
                          textAlign: 'center',
                          fontWeight: 'bold'
                      } }, "Initializing service..."))),
              serviceReady && modelLoading && (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: {
                          padding: '10px',
                          backgroundColor: '#2196f3',
                          borderRadius: '8px',
                          textAlign: 'center',
                          fontWeight: 'bold'
                      } }, "Loading Whisper model..."))),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Enable Dictation", checked: enabled, disabled: !serviceReady || modelLoading, onChange: async (e) => {
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
                      } })),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Show Notifications", description: "Show toast when recording starts/stops", checked: showNotifications, onChange: async (e) => {
                          setShowNotifications(e);
                          logic.showNotifications = e;
                          if (!e && confirmMode) {
                              setConfirmMode(false);
                              await logic.serverAPI.callPluginMethod('set_confirm_mode', { enabled: false });
                          }
                          await logic.serverAPI.callPluginMethod('set_button_config', {
                              buttons: buttons,
                              showNotifications: e
                          });
                      } })),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Confirm Before Sending", description: "Waits before typing (longer for more words) \u2014 hold the buttons again to cancel", checked: confirmMode, onChange: async (e) => {
                          setConfirmMode(e);
                          await logic.serverAPI.callPluginMethod('set_confirm_mode', { enabled: e });
                      } })),
              presets.length > 0 && (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: "Game", menuLabel: "Select Game", rgOptions: presets, selectedOption: activePreset, onChange: async (option) => {
                          const game = option.data;
                          setActivePreset(game);
                          await logic.serverAPI.callPluginMethod('set_active_preset', { game });
                      } }))),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: {
                          padding: '10px',
                          backgroundColor: '#2a2a2a',
                          borderRadius: '6px',
                          fontSize: '13px',
                          textAlign: 'center',
                          border: '1px solid #444',
                          marginBottom: '8px'
                      } },
                      "Hold ",
                      React__default["default"].createElement("strong", null, buttons.join('+')),
                      " to record")),
              buttons.map((button, index) => (React__default["default"].createElement("div", { key: index },
                  React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                      React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: `Button ${index + 1}`, menuLabel: `Select Button ${index + 1}`, rgOptions: BUTTON_OPTIONS, selectedOption: button, onChange: async (option) => {
                              const newButtons = [...buttons];
                              newButtons[index] = option.data;
                              setButtons(newButtons);
                              await logic.serverAPI.callPluginMethod('set_button_config', {
                                  buttons: newButtons,
                                  showNotifications: showNotifications
                              });
                          } })),
                  buttons.length > 1 && (React__default["default"].createElement("div", { style: { display: 'flex', justifyContent: 'flex-end', paddingRight: '16px' } },
                      React__default["default"].createElement("div", { onClick: async () => {
                              const newButtons = buttons.filter((_, i) => i !== index);
                              setButtons(newButtons);
                              await logic.serverAPI.callPluginMethod('set_button_config', {
                                  buttons: newButtons,
                                  showNotifications: showNotifications
                              });
                          }, style: {
                              color: '#e05f5f',
                              cursor: 'pointer',
                              padding: '5px 8px',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              backgroundColor: 'rgba(224, 95, 95, 0.12)',
                              borderRadius: '4px',
                              textDecoration: 'none',
                              userSelect: 'none',
                          } },
                          React__default["default"].createElement(FaTrash, { size: 13 }),
                          React__default["default"].createElement("span", { style: { fontSize: '12px', textDecoration: 'none' } }, "Remove"))))))),
              buttons.length < 5 && (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: { marginTop: '8px' } },
                      React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: async () => {
                              // Find first button not in current list
                              const availableButton = BUTTON_OPTIONS.find(opt => !buttons.includes(opt.data));
                              if (availableButton) {
                                  const newButtons = [...buttons, availableButton.data];
                                  setButtons(newButtons);
                                  await logic.serverAPI.callPluginMethod('set_button_config', {
                                      buttons: newButtons,
                                      showNotifications: showNotifications
                                  });
                              }
                          } }, "\u2795 Add Button")))),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: {
                          padding: '8px',
                          backgroundColor: logic.inputRegistered ? '#1a3a1a' : '#3a1a1a',
                          borderRadius: '4px',
                          fontSize: '12px',
                          textAlign: 'center',
                          fontFamily: 'monospace'
                      } },
                      "Input: ",
                      logic.inputRegistered ? "OK" : "FAILED",
                      React__default["default"].createElement("br", null),
                      "Button: ",
                      React__default["default"].createElement("strong", null, buttonState))),
              enabled && modelReady && (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: {
                          padding: '12px',
                          backgroundColor: recording ? '#4ade80' : '#3b4252',
                          borderRadius: '8px',
                          textAlign: 'center',
                          fontWeight: 'bold',
                          fontSize: '14px',
                          border: recording ? '2px solid #22c55e' : '2px solid #4c566a',
                          transition: 'all 0.3s ease'
                      } }, recording ? '🎤 Recording...' : '✓ Ready'))),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: { marginTop: '4px', marginBottom: '8px' } },
                      React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => logic.testRecording((text, time) => {
                              setLastTranscription(text);
                              setLastTranscriptionTime(time);
                          }), disabled: !enabled || !modelReady || modelLoading || recording },
                          React__default["default"].createElement("div", { style: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' } },
                              React__default["default"].createElement("span", { style: { position: 'relative', display: 'inline-flex' } },
                                  React__default["default"].createElement(FaMicrophone, { size: 14 }),
                                  React__default["default"].createElement(FaCircle, { size: 6, style: { position: 'absolute', bottom: '-1px', right: '-3px', color: '#e05f5f' } })),
                              React__default["default"].createElement("span", null, "Test Recording (3s)"))))),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: {
                          padding: '12px',
                          backgroundColor: '#1a2f1a',
                          borderRadius: '8px',
                          marginTop: '12px',
                          border: '1px solid #2d5a2d'
                      } },
                      React__default["default"].createElement("div", { style: {
                              fontWeight: 'bold',
                              marginBottom: '8px',
                              color: '#4ade80',
                              fontSize: '14px'
                          } }, "Last Transcription:"),
                      React__default["default"].createElement("div", { style: {
                              backgroundColor: '#0f1f0f',
                              padding: '10px',
                              borderRadius: '6px',
                              fontFamily: 'monospace',
                              fontSize: '13px',
                              wordWrap: 'break-word',
                              minHeight: '40px',
                              lineHeight: '1.4',
                              border: '1px solid #1a3a1a'
                          } }, lastTranscription || React__default["default"].createElement("span", { style: { color: '#666', fontStyle: 'italic' } }, "No transcription yet")),
                      lastTranscriptionTime && (React__default["default"].createElement("div", { style: {
                              fontSize: '11px',
                              marginTop: '8px',
                              color: '#888',
                              textAlign: 'right'
                          } }, lastTranscriptionTime))))),
          React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "How to use:" },
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: { fontSize: '13px', lineHeight: '1.6' } },
                      React__default["default"].createElement("strong", null, "Push-to-Talk:"),
                      React__default["default"].createElement("ul", { style: { marginLeft: '15px', marginTop: '5px', marginBottom: '10px' } },
                          React__default["default"].createElement("li", null,
                              "Hold ",
                              React__default["default"].createElement("strong", null, buttons.join('+')),
                              " ",
                              buttons.length > 1 ? 'together' : '',
                              " to record"),
                          React__default["default"].createElement("li", null, "Release to transcribe and type into active window"),
                          React__default["default"].createElement("li", null, "Configure button combo above (1-5 buttons)")),
                      React__default["default"].createElement("strong", null, "Tips:"),
                      React__default["default"].createElement("ul", { style: { marginLeft: '15px', marginTop: '5px' } },
                          React__default["default"].createElement("li", null, "Make sure your game/app is the active window"),
                          React__default["default"].createElement("li", null, "Speak clearly for best results"),
                          React__default["default"].createElement("li", null, "Works great for in-game chat")))))));
  };
  var index = deckyFrontendLib.definePlugin((serverApi) => {
      let logic = new DectationLogic(serverApi);
      let input_register = null;
      // Use RegisterForControllerInputMessages (RegisterForControllerStateChanges doesn't exist)
      try {
          input_register = window.SteamClient.Input.RegisterForControllerInputMessages(logic.handleButtonInput);
          logic.inputRegistered = true;
          console.log("[Decktation] RegisterForControllerInputMessages succeeded");
      }
      catch (e) {
          console.error("[Decktation] RegisterForControllerInputMessages failed:", e);
      }
      // Seed the recording start count so we don't fire a spurious toast on load
      serverApi.callPluginMethod('get_status', {}).then((result) => {
          if (result.success && result.result) {
              logic.prevRecordingStartCount = result.result.recording_start_count || 0;
          }
      });
      // Background notification polling — runs for the full plugin lifetime regardless
      // of whether the Decky panel is open, so toasts appear while in-game.
      const bgNotifyInterval = setInterval(async () => {
          if (!logic.enabled)
              return;
          try {
              const result = await serverApi.callPluginMethod('get_status', {});
              if (result.success && result.result) {
                  if (logic.showNotifications) {
                      const startCount = result.result.recording_start_count || 0;
                      if (startCount > logic.prevRecordingStartCount) {
                          logic.notify("Recording", 1500, "🎤 Recording...");
                      }
                      logic.prevRecordingStartCount = startCount;
                      const pendingText = result.result.pending_text || "";
                      const pendingDelay = result.result.pending_delay || 0;
                      if (pendingText && !logic.prevPendingText) {
                          const secs = Math.round(pendingDelay);
                          logic.notify(`Sending in ${secs}s`, (pendingDelay + 0.5) * 1000, `"${pendingText}" — hold PTT to cancel`)
                              .then(id => { logic.lastPendingToastId = id; });
                      }
                      else if (!pendingText && logic.prevPendingText) {
                          if (logic.lastPendingToastId >= 0) {
                              logic.dismissNotification(logic.lastPendingToastId);
                              logic.lastPendingToastId = -1;
                          }
                      }
                      logic.prevPendingText = pendingText;
                  }
              }
          }
          catch (_e) { }
      }, 200);
      return {
          title: React__default["default"].createElement("div", { className: deckyFrontendLib.quickAccessMenuClasses.Title }, "Decktation"),
          content: React__default["default"].createElement(DectationPanel, { logic: logic }),
          icon: React__default["default"].createElement(FaMicrophone, null),
          onDismount() {
              clearInterval(bgNotifyInterval);
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

  return index;

})(DFL, SP_REACT);
