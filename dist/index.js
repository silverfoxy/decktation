(function (deckyFrontendLib, React$1) {
  'use strict';

  function _interopDefaultLegacy (e) { return e && typeof e === 'object' && 'default' in e ? e : { 'default': e }; }

  var React__default = /*#__PURE__*/_interopDefaultLegacy(React$1);

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
  const BUTTON_OPTIONS = [
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
  class WoWVoiceLogic {
      constructor(serverAPI) {
          this.enabled = false;
          this.recording = false;
          this.lastButtonPress = Date.now();
          this.selectedButton = BUTTONS.A; // Default: Steam + A
          this.steamPressed = false;
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
          this.handleButtonInput = async (val) => {
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
                      this.notify("WoW Voice", 1500, "Recording...");
                  }
                  // Stop recording when combo is released
                  else if (!comboPressed && this.recording) {
                      this.lastButtonPress = Date.now();
                      this.recording = false;
                      await this.serverAPI.callPluginMethod('stop_recording', {});
                      this.notify("WoW Voice", 1500, "Transcribing...");
                  }
              }
          };
          this.testRecording = async () => {
              if (!this.recording) {
                  this.recording = true;
                  await this.serverAPI.callPluginMethod('start_recording', {});
                  this.notify("WoW Voice", 1500, "Recording started (manual test)");
              }
              else {
                  this.recording = false;
                  await this.serverAPI.callPluginMethod('stop_recording', {});
                  this.notify("WoW Voice", 1500, "Recording stopped (manual test)");
              }
          };
          this.serverAPI = serverAPI;
          // Load saved button preference
          const saved = localStorage.getItem('wow_voice_button');
          if (saved !== null) {
              this.selectedButton = parseInt(saved);
          }
      }
      setButton(buttonId) {
          this.selectedButton = buttonId;
          localStorage.setItem('wow_voice_button', buttonId.toString());
      }
  }
  const WoWVoicePanel = ({ logic }) => {
      const [enabled, setEnabled] = React$1.useState(false);
      const [recording, setRecording] = React$1.useState(false);
      const [selectedButton, setSelectedButton] = React$1.useState(logic.selectedButton);
      const [depsInstalled, setDepsInstalled] = React$1.useState(false);
      const [serviceReady, setServiceReady] = React$1.useState(false);
      React$1.useEffect(() => {
          setEnabled(logic.enabled);
          setRecording(logic.recording);
      }, []);
      // Poll plugin status
      React$1.useEffect(() => {
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
      const getButtonLabel = (buttonId) => {
          const option = BUTTON_OPTIONS.find(opt => opt.data === buttonId);
          return option ? option.label : "Unknown";
      };
      return (React.createElement("div", null,
          React.createElement(deckyFrontendLib.PanelSection, null,
              !depsInstalled && (React.createElement(deckyFrontendLib.PanelSectionRow, null,
                  React.createElement("div", { style: {
                          padding: '10px',
                          backgroundColor: '#ff9800',
                          borderRadius: '8px',
                          textAlign: 'center',
                          fontWeight: 'bold'
                      } }, "\u23F3 Installing dependencies... (first run)"))),
              depsInstalled && !serviceReady && (React.createElement(deckyFrontendLib.PanelSectionRow, null,
                  React.createElement("div", { style: {
                          padding: '10px',
                          backgroundColor: '#2196f3',
                          borderRadius: '8px',
                          textAlign: 'center',
                          fontWeight: 'bold'
                      } }, "\u23F3 Loading Whisper model..."))),
              React.createElement(deckyFrontendLib.PanelSectionRow, null,
                  React.createElement(deckyFrontendLib.ToggleField, { label: "Enable Voice Chat", checked: enabled, disabled: !serviceReady, onChange: (e) => {
                          setEnabled(e);
                          logic.enabled = e;
                          if (!e && logic.recording) {
                              logic.serverAPI.callPluginMethod('stop_recording', {});
                              logic.recording = false;
                              setRecording(false);
                          }
                      } })),
              React.createElement(deckyFrontendLib.PanelSectionRow, null,
                  React.createElement(deckyFrontendLib.Dropdown, { rgOptions: BUTTON_OPTIONS, label: "Push-to-Talk Button", strDefaultLabel: getButtonLabel(selectedButton), selectedOption: selectedButton, onChange: (option) => {
                          setSelectedButton(option.data);
                          logic.setButton(option.data);
                      }, disabled: recording })),
              React.createElement(deckyFrontendLib.PanelSectionRow, null,
                  React.createElement("div", { style: {
                          padding: '8px',
                          backgroundColor: '#1a1a1a',
                          borderRadius: '4px',
                          fontSize: '13px',
                          textAlign: 'center',
                          border: '1px solid #444'
                      } },
                      "Hold: ",
                      React.createElement("strong", null,
                          "Steam + ",
                          getButtonLabel(selectedButton)))),
              enabled && (React.createElement(deckyFrontendLib.PanelSectionRow, null,
                  React.createElement("div", { style: {
                          padding: '10px',
                          backgroundColor: recording ? '#4ade80' : '#374151',
                          borderRadius: '8px',
                          textAlign: 'center',
                          fontWeight: 'bold'
                      } }, recording ? '🎤 Recording...' : '⏸ Ready'))),
              React.createElement(deckyFrontendLib.PanelSectionRow, null,
                  React.createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => logic.testRecording(), disabled: !enabled }, recording ? 'Stop Test Recording' : 'Start Test Recording'))),
          React.createElement(deckyFrontendLib.PanelSection, { title: "How to use:" },
              React.createElement(deckyFrontendLib.PanelSectionRow, null,
                  React.createElement("div", { style: { fontSize: '13px', lineHeight: '1.6' } },
                      React.createElement("strong", null, "Push-to-Talk:"),
                      React.createElement("ul", { style: { marginLeft: '15px', marginTop: '5px', marginBottom: '10px' } },
                          React.createElement("li", null,
                              "Hold ",
                              React.createElement("strong", null,
                                  "Steam + ",
                                  getButtonLabel(selectedButton)),
                              " to record"),
                          React.createElement("li", null, "Release to transcribe and send to WoW chat")),
                      React.createElement("strong", null, "Tips:"),
                      React.createElement("ul", { style: { marginLeft: '15px', marginTop: '5px' } },
                          React.createElement("li", null, "Make sure WoW is the active window"),
                          React.createElement("li", null, "Speak clearly for best results"),
                          React.createElement("li", null, "WoW addon context improves accuracy")))))));
  };
  var index = deckyFrontendLib.definePlugin((serverApi) => {
      let logic = new WoWVoiceLogic(serverApi);
      let input_register = window.SteamClient.Input.RegisterForControllerStateChanges(logic.handleButtonInput);
      return {
          title: React.createElement("div", { className: deckyFrontendLib.quickAccessMenuClasses.Title }, "WoW Voice Chat"),
          content: React.createElement(WoWVoicePanel, { logic: logic }),
          icon: React.createElement(FaMicrophone, null),
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

  return index;

})(DFL, SP_REACT);
