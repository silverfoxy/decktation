import React, { useEffect, useRef, useState } from "react";
import { ButtonItem, DropdownItem, Focusable, Navigation, TextField, ToggleField } from "decky-frontend-lib";
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
const styles = `
.decktation-editor { position:fixed; inset:0; z-index:1; box-sizing:border-box; height:100vh; padding:40px 36px 24px; background:#101923; color:#ecf1f6; display:flex; flex-direction:column; gap:16px; font-size:16px; }
.decktation-editor * { box-sizing:border-box; }
.decktation-editor h1 { font-size:26px; margin:0; }
.decktation-editor h2 { font-size:21px; margin:0 0 14px; text-transform:capitalize; }
.decktation-editor header,.decktation-editor footer,.decktation-editor .tabs,.decktation-editor .inline { display:flex; align-items:center; gap:12px; }
.decktation-editor header { justify-content:space-between; background:transparent; padding:0; }
.decktation-editor .subtitle { color:#aab8c7; font-size:14px; margin-top:5px; }
.decktation-editor .tabs > * { flex:1; }
.decktation-editor .workspace { display:grid; grid-template-columns: minmax(240px, 32%) 1fr; gap:20px; min-height:0; flex:1; }
.decktation-editor .channel-list,.decktation-editor .details { min-height:0; overflow-y:auto; padding:16px; border-radius:8px; background:#1b2836; }
.decktation-editor .channel-list { display:flex; flex-direction:column; gap:8px; }
.decktation-editor .channel-rows { flex:1; overflow-y:auto; min-height:80px; }
.decktation-editor .channel-row { margin:4px 0; border-left:3px solid transparent; }
.decktation-editor .channel-row.selected { border-color:#66c0f4; background:#263f53; }
.decktation-editor .channel-row > * { width:100%; margin:0; }
.decktation-editor .channel-label { display:flex; justify-content:space-between; gap:12px; width:100%; text-transform:capitalize; }
.decktation-editor code { color:#9cc7e3; text-transform:none; }
.decktation-editor .field { margin-bottom:18px; }
.decktation-editor .chips { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 20px; }
.decktation-editor .hint { color:#aab8c7; font-size:14px; line-height:1.5; }
.decktation-editor footer { border-top:1px solid #344659; padding-top:12px; justify-content:space-between; }
.decktation-editor .keywords { flex:1; overflow-y:auto; background:#1b2836; padding:24px; border-radius:8px; }
.decktation-editor .notice { padding:12px; background:#354557; border-radius:6px; }
.decktation-editor .error { color:#ffb7b7; }
@media (max-width:700px) { .decktation-editor { padding:30px 16px 16px; } .decktation-editor .workspace { grid-template-columns:220px 1fr; gap:12px; } }
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
        <header><div><h1>{t("Game profiles")}</h1><div className="subtitle">{t("Keywords and channel routing for each game")}</div></div>
            <DropdownItem label={t("Game profile")} rgOptions={presets.map(preset => ({ data:preset.id, label:t(preset.name) }))} selectedOption={game} disabled={disabled}
                onChange={option => { if (String(option.data) !== game) leave(String(option.data)); }} /></header>
        {pending && <Focusable className="notice" role="alertdialog" aria-label={t("Unsaved changes")}>
            <div>{t("Discard unsaved changes?")}</div><div className="inline">
                <ButtonItem layout="below" onClick={() => setPendingAction(null)}>{t("Keep editing")}</ButtonItem>
                <ButtonItem layout="below" onClick={() => { const next = pendingAction?.game; setPendingAction(null); if (next) setGame(next); else Navigation.NavigateBack(); }}>{t("Discard changes")}</ButtonItem>
            </div></Focusable>}
        <div className="tabs"><ButtonItem layout="below" disabled={disabled} onClick={() => setTab("channels")}>{tab === "channels" ? "● " : ""}{t("Channels")}</ButtonItem>
            <ButtonItem layout="below" disabled={disabled} onClick={() => setTab("keywords")}>{tab === "keywords" ? "● " : ""}{t("Keywords")}</ButtonItem></div>
        {!profile && <div role="status">{error || t("Loading...")}</div>}
        {profile && tab === "channels" && <div className="workspace">
            <Focusable className="channel-list"><TextField label={t("Search channels")} value={search} disabled={disabled} onChange={event => setSearch(event.target.value)} />
                <Focusable className="channel-rows" aria-label={t("Channel list")}>
                    {filtered.map(channel => <div key={channel} className={`channel-row ${selected === channel ? "selected" : ""}`}>
                        <ButtonItem layout="below" disabled={disabled} onClick={() => {
                            if (trigger.trim()) { setError(t("Add or clear the spoken trigger before selecting another channel.")); return; }
                            setSelected(channel); setError("");
                            (details.current?.querySelector('input, button, [role="button"]') as HTMLElement | null)?.focus();
                        }}><span className="channel-label"><span>{title(channel)}{profile.default_channel === channel ? " ★" : ""}</span><code>{profile.channels[channel].trim() || t("Text only")}</code></span></ButtonItem>
                    </div>)}
                    {!filtered.length && <p className="hint">{t("No matching channels")}</p>}
                </Focusable>
                {!addingChannel && <ButtonItem layout="below" disabled={disabled} onClick={() => setAddingChannel(true)}>{t("Add channel")}</ButtonItem>}
                {addingChannel && <><TextField label={t("New channel name")} value={newChannel} disabled={disabled} onChange={event => setNewChannel(event.target.value)} />
                <ButtonItem layout="below" disabled={disabled || !/^[a-z][a-z0-9_]{0,39}$/.test(newChannel) || newChannel in profile.channels || Object.keys(profile.channels).length >= 40}
                    onClick={() => {
                        if (trigger.trim()) { setError(t("Add or clear the spoken trigger before adding a channel.")); return; }
                        if (profile.channel_triggers[title(newChannel)]) { setError(t("This name is already a spoken trigger for another channel.")); return; }
                        update({ ...profile, channels:{ ...profile.channels, [newChannel]:"" }, channel_triggers:{ ...profile.channel_triggers, [title(newChannel)]:newChannel } });
                        setSelected(newChannel); setSearch(""); setNewChannel(""); setAddingChannel(false);
                    }}>{t("Add channel")}</ButtonItem>
                <div className="hint">{t("Use lowercase letters, numbers, or underscores. Start with a letter.")}</div>
                <ButtonItem layout="below" disabled={disabled} onClick={() => { setAddingChannel(false); setNewChannel(""); }}>{t("Cancel")}</ButtonItem></>}
            </Focusable>
            <Focusable className="details"><div ref={details}><h2>{title(selected)}</h2>
                <div className="field"><TextField label={t("Chat command")} value={profile.channels[selected] || ""} disabled={disabled}
                    description={t("For example /p. Leave empty to type without a channel command.")}
                    onChange={event => update({ ...profile, channels:{ ...profile.channels, [selected]:event.target.value } })} /></div>
                <div className="field"><ToggleField label={t("Use as default channel")} checked={profile.default_channel === selected} disabled={disabled || profile.default_channel === selected}
                    onChange={() => update({ ...profile, default_channel:selected })} /></div>
                <h2>{t("Additional spoken triggers")}</h2>
                <p className="hint">{t("Say a trigger before your message to select this channel. Built-in language triggers remain available.")}</p>
                <div className="chips">{aliases.map(phrase => <ButtonItem key={phrase} layout="below" disabled={disabled} onClick={() => {
                    const next = { ...profile.channel_triggers }; delete next[phrase]; update({ ...profile, channel_triggers:next });
                }}>{t("Remove trigger")}: {phrase} ×</ButtonItem>)}</div>
                <TextField label={t("New spoken trigger")} value={trigger} disabled={disabled} onChange={event => setTrigger(event.target.value)} />
                <ButtonItem layout="below" disabled={disabled || !trigger.trim()} onClick={() => {
                    const phrase = trigger.trim().toLowerCase();
                    if (phrase in profile.channel_triggers && profile.channel_triggers[phrase] !== selected) { setError(t("Each spoken trigger must belong to one channel.")); return; }
                    update({ ...profile, channel_triggers:{ ...profile.channel_triggers, [phrase]:selected } }); setTrigger("");
                }}>{t("Add trigger")}</ButtonItem>
                <p className="hint">{t("Example")}: <strong>{aliases[0] || title(selected)} {t("hello everyone")}</strong> → <code>{profile.channels[selected].trim()} {t("hello everyone")}</code></p>
            </div></Focusable>
        </div>}
        {profile && tab === "keywords" && <Focusable className="keywords"><h2>{t("Recognition keywords")}</h2>
            <p className="hint">{t("Names and game terms that help Whisper recognize speech. These hints apply to every channel in this game profile.")}</p>
            <div className="inline"><TextField label={t("New keyword")} value={keyword} disabled={disabled} onChange={event => setKeyword(event.target.value)} />
                <ButtonItem layout="below" disabled={disabled || !keyword.trim() || profile.hotwords.length >= 100} onClick={() => {
                    const word = keyword.trim(); if (!profile.hotwords.includes(word)) update({ ...profile, hotwords:[...profile.hotwords, word] }); setKeyword("");
                }}>{t("Add keyword")}</ButtonItem></div>
            <div className="chips">{profile.hotwords.map((word, index) => <ButtonItem key={`${index}-${word}`} layout="below" disabled={disabled}
                onClick={() => update({ ...profile, hotwords:profile.hotwords.filter((_, position) => position !== index) })}>{t("Remove keyword")}: {word} ×</ButtonItem>)}</div>
            {!profile.hotwords.length && <p className="hint">{t("No custom keywords yet. Add character names, places, or unusual game terms.")}</p>}
        </Focusable>}
        <footer><ButtonItem layout="below" disabled={busy} onClick={() => leave()}>{t("Back")}</ButtonItem>
            <div role={error ? "alert" : "status"} className={error ? "error" : "hint"}>{error || (dirty ? t("Unsaved changes") : message)}</div>
            <ButtonItem layout="below" disabled={disabled || !profile || !dirty} onClick={save}>{busy ? t("Saving...") : t("Save changes")}</ButtonItem></footer>
    </Focusable>;
}
