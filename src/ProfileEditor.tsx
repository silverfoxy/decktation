import React, { useEffect, useRef, useState } from "react";
import { DialogButton, Dropdown, Focusable, Navigation, TextField, TextFieldProps } from "decky-frontend-lib";
import { callable } from "@decky/api";
import { t } from "./i18n";

export const PROFILE_EDITOR_ROUTE = "/decktation/profiles";
let initialGame = "wow";
export function openProfileEditor(game: string) {
    initialGame = game;
    Navigation.Navigate(PROFILE_EDITOR_ROUTE);
    Navigation.CloseSideMenus();
}
type Profile = {
    hotwords: string[];
    channels: Record<string, string>;
    channel_triggers: Record<string, string>;
    default_channel: string;
};
type Preset = { id: string; name: string };
const loadProfile = callable<[game: string], any>("get_profile_editor");
const saveProfile = callable<[game: string, profile: Profile], any>("save_profile_editor");
const getPresets = callable<[], any>("get_presets");
const title = (channel: string) => channel.replace(/_/g, " ");
// Use raw full-screen controls, rather than Steam's tall quick-access form rows.
function EditorTextField({ label, description, ...props }: TextFieldProps) {
    return <div className="editor-field">
        <div className="editor-label">{label}</div>
        <TextField {...props} aria-label={String(label)} style={{ height: 32, minHeight: 32, padding: "5px 8px", fontSize: 14, lineHeight: "20px", margin: 0 }} />
        {description && <div className="hint">{description}</div>}
    </div>;
}
const styles = `
.decktation-editor { position:fixed; inset:0; z-index:1; box-sizing:border-box; height:100vh; padding:44px 20px 16px; background:#101923; color:#ecf1f6; display:flex; flex-direction:column; gap:10px; font-size:14px; line-height:1.35; overflow:hidden; }
.decktation-editor * { box-sizing:border-box; }
.decktation-editor h1 { font-size:20px; line-height:1.2; margin:0; white-space:nowrap; }
.decktation-editor h2 { font-size:17px; line-height:1.25; margin:0; text-transform:capitalize; }
.decktation-editor header,.decktation-editor footer,.decktation-editor .tabs,.decktation-editor .inline { display:flex; align-items:center; gap:8px; min-width:0; }
.decktation-editor header { flex-shrink:0; justify-content:space-between; background:transparent; padding:0; min-height:36px; }
.decktation-editor .tabs { flex-shrink:0; }
.decktation-editor .profile-picker { display:flex; align-items:center; gap:8px; min-width:0; }
.decktation-editor .profile-picker > span { font-size:12px; color:#aab8c7; white-space:nowrap; }
.decktation-editor .profile-picker > :last-child { width:210px; min-width:0; }
.decktation-editor .profile-picker button,.decktation-editor .profile-picker [role="button"],.decktation-editor .profile-picker select { min-height:32px !important; height:32px !important; padding:4px 8px !important; font-size:14px !important; margin:0 !important; }
.decktation-editor .editor-button { display:block; min-height:32px !important; height:32px; min-width:0 !important; width:auto; margin:0 !important; padding:5px 10px !important; font-size:14px !important; line-height:20px !important; flex-shrink:0; white-space:nowrap; }
.decktation-editor .tabs .editor-button { width:100px; }
.decktation-editor .workspace { display:grid; grid-template-columns:minmax(210px,30%) minmax(0,1fr); gap:12px; min-height:0; flex:1; }
.decktation-editor .channel-list,.decktation-editor .details { min-height:0; min-width:0; padding:12px; border-radius:6px; background:#1b2836; }
.decktation-editor .channel-list { display:flex; flex-direction:column; gap:8px; overflow:hidden; }
.decktation-editor .channel-list > :not(.channel-rows) { flex-shrink:0; }
.decktation-editor .channel-rows { flex:1; overflow-y:auto; min-height:0; }
.decktation-editor .channel-row { margin:0 0 3px; border-left:3px solid transparent; }
.decktation-editor .channel-row.selected { border-color:#66c0f4; background:#263f53; }
.decktation-editor .channel-row .editor-button { width:100%; text-align:left; border-radius:3px; }
.decktation-editor .channel-label { display:flex; justify-content:space-between; align-items:center; gap:10px; width:100%; text-transform:capitalize; }
.decktation-editor .channel-label > span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.decktation-editor code { color:#9cc7e3; text-transform:none; font-size:13px; }
.decktation-editor .details { overflow-y:auto; }
.decktation-editor .details-body { display:flex; flex-direction:column; gap:12px; }
.decktation-editor .editor-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.decktation-editor .editor-label { font-size:13px; color:#cdd7e2; line-height:18px; }
.decktation-editor .editor-field input { width:100%; min-width:0; height:32px !important; min-height:32px !important; margin:0 !important; padding:5px 8px !important; font-size:14px !important; line-height:20px !important; background:#101923 !important; color:#ecf1f6 !important; border:1px solid #53687c !important; border-radius:4px; }
.decktation-editor .field { margin:0; }
.decktation-editor .trigger-section { display:flex; flex-direction:column; gap:8px; }
.decktation-editor .trigger-section .inline { align-items:flex-end; }
.decktation-editor .inline .editor-field { flex:1; }
.decktation-editor .chips { display:flex; flex-wrap:wrap; gap:6px; margin:0; }
.decktation-editor .hint { color:#aab8c7; font-size:12px; line-height:1.4; margin:0; }
.decktation-editor footer { flex-shrink:0; border-top:1px solid #344659; padding-top:8px; justify-content:space-between; min-height:40px; }
.decktation-editor footer [role="alert"],.decktation-editor footer [role="status"] { flex:1; min-width:0; text-align:center; }
.decktation-editor .keywords { flex:1; min-height:0; overflow-y:auto; background:#1b2836; padding:16px; border-radius:6px; display:flex; flex-direction:column; gap:12px; }
.decktation-editor .notice { padding:10px; background:#354557; border-radius:6px; flex-shrink:0; }
.decktation-editor .error { color:#ffb7b7; font-size:12px; }
@media (max-width:850px) { .decktation-editor { padding:36px 12px 12px; gap:8px; } .decktation-editor h1 { font-size:18px; } .decktation-editor .profile-picker > span { display:none; } .decktation-editor .profile-picker > :last-child { width:190px; } .decktation-editor .tabs .editor-button { width:88px; } .decktation-editor .channel-list,.decktation-editor .details { padding:10px; } }
`;

export function ProfileEditor() {
    const [game, setGame] = useState(initialGame);
    const [presets, setPresets] = useState<Preset[]>([]);
    const [profile, setProfile] = useState<Profile | null>(null);
    const [selected, setSelected] = useState("");
    const [tab, setTab] = useState<"channels" | "keywords">("channels");
    const [search, setSearch] = useState("");
    const [newChannel, setNewChannel] = useState("");
    const [addingChannel, setAddingChannel] = useState(false);
    const [trigger, setTrigger] = useState("");
    const [keyword, setKeyword] = useState("");
    const [busy, setBusy] = useState(false);
    const [dirty, setDirty] = useState(false);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");
    const [pendingAction, setPendingAction] = useState<{ game?: string } | null>(null);
    const details = useRef<HTMLDivElement>(null);
    const mounted = useRef(true);
    useEffect(() => {
        mounted.current = true;
        getPresets().then(result => {
            if (!mounted.current) return;
            if (result.success) setPresets(result.presets); else setError(result.error);
        }).catch(error => { if (mounted.current) setError(String(error)); });
        return () => { mounted.current = false; };
    }, []);
    useEffect(() => {
        let active = true;
        setProfile(null); setError(""); setMessage(""); setDirty(false); setSearch("");
        setTrigger(""); setKeyword(""); setNewChannel(""); setAddingChannel(false);
        loadProfile(game).then(result => {
            if (!active) return;
            if (!result.success) { setError(result.error); return; }
            const loaded = result.profile;
            setProfile({ ...loaded, hotwords: Array.isArray(loaded.hotwords) ? loaded.hotwords : loaded.hotwords ? [loaded.hotwords] : [] });
            setSelected(loaded.default_channel);
        }).catch(error => { if (active) setError(String(error)); });
        return () => { active = false; };
    }, [game]);
    function update(next: Profile) { setProfile(next); setDirty(true); setMessage(""); setError(""); }
    function leave(nextGame?: string) {
        if (busy) return;
        if (dirty || trigger.trim() || keyword.trim() || newChannel.trim()) { setPendingAction(nextGame ? { game: nextGame } : {}); return; }
        if (nextGame) setGame(nextGame); else Navigation.NavigateBack();
    }
    async function save() {
        if (!profile) return;
        if (trigger.trim() || keyword.trim() || newChannel.trim()) { setError(t("Add or clear the text you entered before saving.")); return; }
        setBusy(true); setError("");
        try {
            const channels = Object.fromEntries(Object.entries(profile.channels as Record<string, string>).map(([key, command]) => [key, command.trim() ? command.trim() + " " : ""]));
            const result = await saveProfile(game, { ...profile, channels });
            if (!mounted.current) return;
            if (!result.success) throw new Error(result.error);
            setProfile({ ...profile, channels }); setDirty(false); setMessage(t("Saved"));
        } catch (error) { if (mounted.current) setError(String(error)); }
        finally { if (mounted.current) setBusy(false); }
    }
    const pending = pendingAction !== null;
    const disabled = busy || pending;
    const filtered = profile ? Object.keys(profile.channels).filter(channel =>
        `${title(channel)} ${profile.channels[channel]} ${Object.entries(profile.channel_triggers).filter(([, value]) => value === channel).map(([key]) => key).join(" ")}`.toLowerCase().includes(search.toLowerCase())) : [];
    const aliases = profile ? Object.entries(profile.channel_triggers).filter(([, channel]) => channel === selected).map(([phrase]) => phrase) : [];
    return <Focusable className="decktation-editor" onCancel={(event: any) => { event.stopPropagation(); event.preventDefault(); if (pending) setPendingAction(null); else leave(); }} onCancelActionDescription={t("Back")}>
        <style>{styles}</style>
        <header><h1>{t("Game profiles")}</h1>
            <div className="tabs"><DialogButton className="editor-button" disabled={disabled} onClick={() => setTab("channels")}>{tab === "channels" ? "● " : ""}{t("Channels")}</DialogButton>
                <DialogButton className="editor-button" disabled={disabled} onClick={() => setTab("keywords")}>{tab === "keywords" ? "● " : ""}{t("Keywords")}</DialogButton></div>
            <div className="profile-picker"><span>{t("Game profile")}</span><Dropdown menuLabel={t("Game profile")} rgOptions={presets.map(preset => ({ data:preset.id, label:t(preset.name) }))} selectedOption={game} disabled={disabled}
                onChange={option => { if (String(option.data) !== game) leave(String(option.data)); }} /></div></header>
        {pending && <Focusable className="notice" role="alertdialog" aria-label={t("Unsaved changes")}>
            <div>{t("Discard unsaved changes?")}</div><div className="inline">
                <DialogButton className="editor-button" onClick={() => setPendingAction(null)}>{t("Keep editing")}</DialogButton>
                <DialogButton className="editor-button" onClick={() => { const next = pendingAction?.game; setPendingAction(null); if (next) setGame(next); else Navigation.NavigateBack(); }}>{t("Discard changes")}</DialogButton>
            </div></Focusable>}
        {!profile && <div role="status">{error || t("Loading...")}</div>}
        {profile && tab === "channels" && <div className="workspace">
            <Focusable className="channel-list"><EditorTextField label={t("Search channels")} value={search} disabled={disabled} onChange={event => setSearch(event.target.value)} />
                <Focusable className="channel-rows" aria-label={t("Channel list")}>
                    {filtered.map(channel => <div key={channel} className={`channel-row ${selected === channel ? "selected" : ""}`}>
                        <DialogButton className="editor-button" disabled={disabled} onClick={() => {
                            if (trigger.trim()) { setError(t("Add or clear the spoken trigger before selecting another channel.")); return; }
                            setSelected(channel); setError("");
                            (details.current?.querySelector('input, button, [role="button"]') as HTMLElement | null)?.focus();
                        }}><span className="channel-label"><span>{title(channel)}{profile.default_channel === channel ? " ★" : ""}</span><code>{profile.channels[channel].trim() || t("Text only")}</code></span></DialogButton>
                    </div>)}
                    {!filtered.length && <p className="hint">{t("No matching channels")}</p>}
                </Focusable>
                {!addingChannel && <DialogButton className="editor-button" disabled={disabled} onClick={() => setAddingChannel(true)}>{t("Add channel")}</DialogButton>}
                {addingChannel && <><EditorTextField label={t("New channel name")} value={newChannel} disabled={disabled} onChange={event => setNewChannel(event.target.value)} />
                <DialogButton className="editor-button" disabled={disabled || !/^[a-z][a-z0-9_]{0,39}$/.test(newChannel) || newChannel in profile.channels || Object.keys(profile.channels).length >= 40}
                    onClick={() => {
                        if (trigger.trim()) { setError(t("Add or clear the spoken trigger before adding a channel.")); return; }
                        if (profile.channel_triggers[title(newChannel)]) { setError(t("This name is already a spoken trigger for another channel.")); return; }
                        update({ ...profile, channels:{ ...profile.channels, [newChannel]:"" }, channel_triggers:{ ...profile.channel_triggers, [title(newChannel)]:newChannel } });
                        setSelected(newChannel); setSearch(""); setNewChannel(""); setAddingChannel(false);
                    }}>{t("Add channel")}</DialogButton>
                <div className="hint">{t("Use lowercase letters, numbers, or underscores. Start with a letter.")}</div>
                <DialogButton className="editor-button" disabled={disabled} onClick={() => { setAddingChannel(false); setNewChannel(""); }}>{t("Cancel")}</DialogButton></>}
            </Focusable>
            <Focusable className="details"><div ref={details} className="details-body"><h2>{title(selected)}</h2>
                <div className="field"><EditorTextField label={t("Chat command")} value={profile.channels[selected] || ""} disabled={disabled}
                    description={t("For example /p. Leave empty to type without a channel command.")}
                    onChange={event => update({ ...profile, channels:{ ...profile.channels, [selected]:event.target.value } })} /></div>
                <div className="field"><DialogButton className="editor-button" disabled={disabled || profile.default_channel === selected}
                    onClick={() => update({ ...profile, default_channel:selected })}>{profile.default_channel === selected ? "★ " : "☆ "}{t("Use as default channel")}</DialogButton></div>
                <div className="trigger-section"><h2>{t("Additional spoken triggers")}</h2>
                <p className="hint">{t("Say a trigger before your message to select this channel. Built-in language triggers remain available.")}</p>
                <div className="chips">{aliases.map(phrase => <DialogButton className="editor-button" key={phrase} disabled={disabled} onClick={() => {
                    const next = { ...profile.channel_triggers }; delete next[phrase]; update({ ...profile, channel_triggers:next });
                }}>{t("Remove trigger")}: {phrase} ×</DialogButton>)}</div>
                <div className="inline"><EditorTextField label={t("New spoken trigger")} value={trigger} disabled={disabled} onChange={event => setTrigger(event.target.value)} />
                <DialogButton className="editor-button" disabled={disabled || !trigger.trim()} onClick={() => {
                    const phrase = trigger.trim().toLowerCase();
                    if (phrase in profile.channel_triggers && profile.channel_triggers[phrase] !== selected) { setError(t("Each spoken trigger must belong to one channel.")); return; }
                    update({ ...profile, channel_triggers:{ ...profile.channel_triggers, [phrase]:selected } }); setTrigger("");
                }}>{t("Add trigger")}</DialogButton></div></div>
                <p className="hint">{t("Example")}: <strong>{aliases[0] || title(selected)} {t("hello everyone")}</strong> → <code>{profile.channels[selected].trim()} {t("hello everyone")}</code></p>
            </div></Focusable>
        </div>}
        {profile && tab === "keywords" && <Focusable className="keywords"><h2>{t("Recognition keywords")}</h2>
            <p className="hint">{t("Names and game terms that help Whisper recognize speech. These hints apply to every channel in this game profile.")}</p>
            <div className="inline"><EditorTextField label={t("New keyword")} value={keyword} disabled={disabled} onChange={event => setKeyword(event.target.value)} />
                <DialogButton className="editor-button" disabled={disabled || !keyword.trim() || profile.hotwords.length >= 100} onClick={() => {
                    const word = keyword.trim(); if (!profile.hotwords.includes(word)) update({ ...profile, hotwords:[...profile.hotwords, word] }); setKeyword("");
                }}>{t("Add keyword")}</DialogButton></div>
            <div className="chips">{profile.hotwords.map((word, index) => <DialogButton className="editor-button" key={`${index}-${word}`} disabled={disabled}
                onClick={() => update({ ...profile, hotwords:profile.hotwords.filter((_, position) => position !== index) })}>{t("Remove keyword")}: {word} ×</DialogButton>)}</div>
            {!profile.hotwords.length && <p className="hint">{t("No custom keywords yet. Add character names, places, or unusual game terms.")}</p>}
        </Focusable>}
        <footer><DialogButton className="editor-button" disabled={busy} onClick={() => leave()}>{t("Back")}</DialogButton>
            <div role={error ? "alert" : "status"} className={error ? "error" : "hint"}>{error || (dirty ? t("Unsaved changes") : message)}</div>
            <DialogButton className="editor-button" disabled={disabled || !profile || !dirty} onClick={save}>{busy ? t("Saving...") : t("Save changes")}</DialogButton></footer>
    </Focusable>;
}
