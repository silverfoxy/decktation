/** The only dependency on Decky's internal installer route. */
export type PreparedUpdate = { artifact: string; version: string; hash: string };
export type InstallResult = { success: boolean; error?: string };
type Loader = { call?: (...args: unknown[]) => Promise<unknown> };
const unavailable = "Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.";

export async function requestPluginUpdate(update: PreparedUpdate): Promise<InstallResult> {
    try {
        const loader = (typeof window === "undefined" ? undefined :
            (window as unknown as { DeckyBackend?: Loader }).DeckyBackend);
        if (typeof loader?.call !== "function") return { success: false, error: unavailable };
        // Defense against accidentally handing a remote artifact to Loader.
        if (!/^file:\/\/\/tmp\/decktation-update-[A-Za-z0-9_-]+\.zip$/.test(update.artifact)) {
            return { success: false, error: "The update could not be verified, so it was not installed." };
        }
        const result = await loader.call("utilities/install_plugin", update.artifact,
            "Decktation", update.version, update.hash, 2);
        if (result === false || (result && typeof result === "object" &&
            "success" in result && (result as {success: unknown}).success === false)) {
            return { success: false, error: unavailable };
        }
        // This requests a native prompt; it does not report installation success.
        leaveStalePluginPanel();
        return { success: true };
    } catch (_error) {
        return { success: false, error: unavailable };
    }
}

/** Optional navigation workaround for Loader #976; no Steam patches or reloads. */
export function leaveStalePluginPanel(): boolean {
    try {
        const state = (typeof window === "undefined" ? undefined :
            (window as unknown as { DeckyPluginLoader?: { deckyState?: {
                publicState?: () => { activePlugin?: { name?: string } | null };
                closeActivePlugin?: () => void;
            } } }).DeckyPluginLoader?.deckyState);
        if (typeof state?.publicState !== "function" || typeof state.closeActivePlugin !== "function" ||
            state.publicState().activePlugin?.name !== "Decktation") return false;
        state.closeActivePlugin();
        return true;
    } catch (_error) {
        return false;
    }
}
