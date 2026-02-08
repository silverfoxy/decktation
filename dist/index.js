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
  function FaMicrophone (props) {
    return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 352 512"},"child":[{"tag":"path","attr":{"d":"M176 352c53.02 0 96-42.98 96-96V96c0-53.02-42.98-96-96-96S80 42.98 80 96v160c0 53.02 42.98 96 96 96zm160-160h-16c-8.84 0-16 7.16-16 16v48c0 74.8-64.49 134.82-140.79 127.38C96.71 376.89 48 317.11 48 250.3V208c0-8.84-7.16-16-16-16H16c-8.84 0-16 7.16-16 16v40.16c0 89.64 63.97 169.55 152 181.69V464H96c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16h-56v-33.77C285.71 418.47 352 344.9 352 256v-48c0-8.84-7.16-16-16-16z"}}]})(props);
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
          this.notify = async (message, duration = 2000, body = "") => {
              if (!body) {
                  body = message;
              }
              this.serverAPI.toaster.toast({
                  title: message,
                  body: body,
                  duration: duration,
                  critical: true
              });
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
          this.testRecording = async () => {
              if (!this.recording) {
                  this.recording = true;
                  await this.serverAPI.callPluginMethod('start_recording', {});
                  this.notify("Decktation", 1500, "Recording started (manual test)");
              }
              else {
                  this.recording = false;
                  await this.serverAPI.callPluginMethod('stop_recording', {});
                  this.notify("Decktation", 1500, "Recording stopped (manual test)");
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
      const [button1, setButton1] = React.useState("L1");
      const [button2, setButton2] = React.useState("R1");
      React.useEffect(() => {
          setEnabled(logic.enabled);
          setRecording(logic.recording);
          logic.onButtonChange = () => {
              setButtonState(logic.lastButtonState);
          };
          // Load button configuration
          logic.serverAPI.callPluginMethod('get_button_config', {}).then((result) => {
              if (result.success && result.result) {
                  const config = result.result.config;
                  if (config) {
                      setButton1(config.button1 || "L1");
                      setButton2(config.button2 || "R1");
                  }
              }
          });
          return () => {
              logic.onButtonChange = null;
          };
      }, []);
      React.useEffect(() => {
          const interval = setInterval(async () => {
              const result = await logic.serverAPI.callPluginMethod('get_status', {});
              if (result.success && result.result) {
                  setServiceReady(result.result.service_ready);
                  setModelReady(result.result.model_ready);
                  setModelLoading(result.result.model_loading);
                  if (logic.enabled) {
                      setRecording(result.result.recording);
                  }
              }
          }, 1000);
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
                  React__default["default"].createElement("div", { style: {
                          padding: '8px',
                          backgroundColor: '#1a1a1a',
                          borderRadius: '4px',
                          fontSize: '13px',
                          textAlign: 'center',
                          border: '1px solid #444'
                      } },
                      "Hold ",
                      React__default["default"].createElement("strong", null,
                          button1,
                          "+",
                          button2),
                      " to record")),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: "Button 1", menuLabel: "Select First Button", rgOptions: BUTTON_OPTIONS, selectedOption: button1, onChange: async (option) => {
                          setButton1(option.data);
                          await logic.serverAPI.callPluginMethod('set_button_config', {
                              button1: option.data,
                              button2: button2
                          });
                      } })),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: "Button 2", menuLabel: "Select Second Button", rgOptions: BUTTON_OPTIONS, selectedOption: button2, onChange: async (option) => {
                          setButton2(option.data);
                          await logic.serverAPI.callPluginMethod('set_button_config', {
                              button1: button1,
                              button2: option.data
                          });
                      } })),
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
                          padding: '10px',
                          backgroundColor: recording ? '#4ade80' : '#374151',
                          borderRadius: '8px',
                          textAlign: 'center',
                          fontWeight: 'bold'
                      } }, recording ? 'Recording...' : 'Ready'))),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => logic.testRecording(), disabled: !enabled || !modelReady || modelLoading }, recording ? 'Stop Test Recording' : 'Start Test Recording'))),
          React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "How to use:" },
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { style: { fontSize: '13px', lineHeight: '1.6' } },
                      React__default["default"].createElement("strong", null, "Push-to-Talk:"),
                      React__default["default"].createElement("ul", { style: { marginLeft: '15px', marginTop: '5px', marginBottom: '10px' } },
                          React__default["default"].createElement("li", null,
                              "Hold ",
                              React__default["default"].createElement("strong", null,
                                  button1,
                                  "+",
                                  button2),
                              " together to record"),
                          React__default["default"].createElement("li", null, "Release to transcribe and type into active window"),
                          React__default["default"].createElement("li", null, "Change button combo above if needed")),
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
      return {
          title: React__default["default"].createElement("div", { className: deckyFrontendLib.quickAccessMenuClasses.Title }, "Decktation"),
          content: React__default["default"].createElement(DectationPanel, { logic: logic }),
          icon: React__default["default"].createElement(FaMicrophone, null),
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

  return index;

})(DFL, SP_REACT);
