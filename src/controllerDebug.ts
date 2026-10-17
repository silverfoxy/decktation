/** Controller capture is owned by the backend; this client never creates a deadline or a report. */
export type ControllerDebugState = "idle" | "starting" | "recording" | "stopping" | "ready" | "failed";
export type ControllerLiveInput = {
    pressed: {source: string; button: string}[];
    last_event: {at_ms: number; source: string; kind: "key" | "hid" | "mapped" | "binding";
        button?: string; code?: number; pressed: boolean} | null;
};
export type ControllerDebugSnapshot = {
    success: true;
    session: string | null;
    revision: number;
    state: ControllerDebugState;
    remaining_ms: number;
    event_count: number;
    device_count: number;
    metadata: Record<string, string>;
    report: Record<string, any> | null;
    error?: string;
    live_input?: ControllerLiveInput | null;
    event_id?: string | null;
};
export type ControllerDebugView = {
    snapshot: ControllerDebugSnapshot;
    pending: "start" | "stop" | "resume" | "upload" | null;
    error: string;
};
type Rpc = {
    start: () => Promise<any>;
    get: (session: string) => Promise<any>;
    stop: (session: string) => Promise<any>;
    resume: () => Promise<any>;
    upload: (session: string, consent: boolean) => Promise<any>;
};
const ACTIVE = new Set<ControllerDebugState>(["starting", "recording", "stopping"]);
const STATES = new Set(["idle", ...ACTIVE, "ready", "failed"]);
const idle = (): ControllerDebugSnapshot => ({success: true, session: null, revision: 0, state: "idle",
    remaining_ms: 0, event_count: 0, device_count: 0, metadata: {}, report: null});
const object = (value: any): boolean => value !== null && typeof value === "object" && !Array.isArray(value);

const LIVE_BUTTONS = new Set(["A", "B", "X", "Y", "L1", "R1", "L2", "R2", "L3", "R3",
    "L4", "R4", "L5", "R5", "View", "Menu", "D-pad Up", "D-pad Down", "D-pad Left", "D-pad Right",
    "Left Trackpad", "Right Trackpad"]);
const liveSource = (value: any): boolean => typeof value === "string" && /^source_([1-9]|1[0-6])$/.test(value);
const liveCode = (value: any): boolean => Number.isInteger(value) &&
    ((value >= 0x100 && value <= 0x15f) || (value >= 0x220 && value <= 0x223) || (value >= 0x2c0 && value <= 0x2ff));
function liveInput(value: any): ControllerLiveInput | null {
    if (!object(value) || !Array.isArray(value.pressed) || value.pressed.length > 32 ||
        !value.pressed.every((entry: any) => object(entry) && liveSource(entry.source) && LIVE_BUTTONS.has(entry.button))) return null;
    const event = value.last_event;
    if (event !== null && (!object(event) || !Number.isFinite(event.at_ms) || event.at_ms < 0 || event.at_ms > 30000 ||
        !liveSource(event.source) || !["key", "hid", "mapped", "binding"].includes(event.kind) || typeof event.pressed !== "boolean" ||
        (event.button !== undefined && !LIVE_BUTTONS.has(event.button)) ||
        (event.code !== undefined && !liveCode(event.code)) ||
        (event.kind === "key" ? !liveCode(event.code) : !LIVE_BUTTONS.has(event.button)))) return null;
    return {pressed: value.pressed.map(({source, button}: any) => ({source, button})),
        last_event: event === null ? null : {at_ms: event.at_ms, source: event.source, kind: event.kind,
            ...(event.button !== undefined ? {button: event.button} : {}),
            ...(event.code !== undefined ? {code: event.code} : {}), pressed: event.pressed}};
}

export class ControllerDebugClient {
    view: ControllerDebugView = {snapshot: idle(), pending: null, error: ""};
    private listeners = new Set<(view: ControllerDebugView) => void>();
    private pollTimer: ReturnType<typeof setTimeout> | undefined;
    private epoch = 0;
    private disposed = false;
    private cancelRequests = new Set<() => void>();

    constructor(private rpc: Rpc) {}

    subscribe(listener: (view: ControllerDebugView) => void): () => void {
        this.listeners.add(listener);
        listener(this.view);
        return () => { this.listeners.delete(listener); };
    }

    private emit(patch: Partial<ControllerDebugView>): void {
        this.view = {...this.view, ...patch};
        for (const listener of this.listeners) listener(this.view);
    }

    private clearPoll(): void {
        if (this.pollTimer !== undefined) clearTimeout(this.pollTimer);
        this.pollTimer = undefined;
    }

    private async request(invoke: () => Promise<any>, timeout = 5000): Promise<any> {
        let timer: ReturnType<typeof setTimeout> | undefined;
        let cancel = () => {};
        try {
            return await new Promise((resolve, reject) => {
                cancel = () => reject(new Error("Controller debugger disconnected."));
                this.cancelRequests.add(cancel);
                timer = setTimeout(() => reject(new Error("Controller debugger did not respond. Try a new capture.")), timeout);
                Promise.resolve().then(invoke).then(resolve, reject);
            });
        } finally {
            if (timer !== undefined) clearTimeout(timer);
            this.cancelRequests.delete(cancel);
        }
    }

    private accept(result: any, expectedSession?: string): void {
        if (!result?.success) throw new Error(result?.error || "Could not read controller report");
        if (!STATES.has(result.state) || !Number.isInteger(result.revision) || result.revision < 0 ||
                !Number.isInteger(result.remaining_ms) || result.remaining_ms < 0 || result.remaining_ms > 30000 ||
                !Number.isInteger(result.event_count) || result.event_count < 0 ||
                !Number.isInteger(result.device_count) || result.device_count < 0 ||
                !object(result.metadata) ||
                (result.state === "idle" ? result.session !== null : typeof result.session !== "string" || !result.session) ||
                (expectedSession !== undefined && result.session !== expectedSession) ||
                (result.state === "ready" && (!object(result.report) || !["complete", "stopped"].includes(result.report.phase)))) {
            throw new Error("Invalid controller capture status. Reopen Diagnostics to reconnect.");
        }
        const current = this.view.snapshot;
        if (current.session === result.session && result.revision < current.revision) return;
        // Even a newer stale transport response cannot resurrect a terminal session.
        if (current.session === result.session && ["ready", "failed"].includes(current.state) && ACTIVE.has(result.state)) return;
        this.emit({snapshot: {...result, report: result.state === "ready" ? result.report : null,
            live_input: result.state === "recording" ? liveInput(result.live_input) : null}, error: ""});
    }

    private schedulePoll(): void {
        this.clearPoll();
        if (this.disposed || this.view.pending || this.view.error || !ACTIVE.has(this.view.snapshot.state)) return;
        this.pollTimer = setTimeout(() => this.poll(), 250);
    }

    private async poll(): Promise<void> {
        this.pollTimer = undefined;
        const token = this.epoch;
        const session = this.view.snapshot.session;
        if (!session || this.disposed || this.view.pending) return;
        try {
            const result = await this.request(() => this.rpc.get(session));
            if (!this.disposed && token === this.epoch) this.accept(result, session);
        } catch (error) {
            if (!this.disposed && token === this.epoch) this.emit({error: (error as Error).message, snapshot: {...this.view.snapshot, live_input: null}});
        } finally {
            if (!this.disposed && token === this.epoch) this.schedulePoll();
        }
    }

    private async command(pending: ControllerDebugView["pending"], invoke: () => Promise<any>, expectedSession?: string): Promise<void> {
        const token = ++this.epoch;
        this.clearPoll();
        this.emit({pending, error: ""});
        try {
            const result = await this.request(invoke, pending === "upload" ? 15000 : 5000);
            if (!this.disposed && token === this.epoch) this.accept(result, expectedSession);
        } catch (error) {
            if (!this.disposed && token === this.epoch) this.emit({error: (error as Error).message, snapshot: {...this.view.snapshot, live_input: null}});
        } finally {
            if (!this.disposed && token === this.epoch) {
                this.emit({pending: null});
                this.schedulePoll();
            }
        }
    }

    async connect(): Promise<void> {
        this.disposed = false;
        await this.command("resume", () => this.rpc.resume());
    }

    async start(): Promise<void> {
        if (this.disposed || (this.view.pending && this.view.pending !== "resume") || ACTIVE.has(this.view.snapshot.state)) return;
        await this.command("start", () => this.rpc.start());
    }

    async stop(): Promise<void> {
        const {snapshot, pending} = this.view;
        if (this.disposed || pending || !snapshot.session || !["starting", "recording"].includes(snapshot.state)) return;
        await this.command("stop", () => this.rpc.stop(snapshot.session!), snapshot.session);
    }

    async refresh(): Promise<void> {
        if (!this.disposed && !this.view.pending) await this.command("resume", () => this.rpc.resume());
    }

    async upload(): Promise<void> {
        const {snapshot, pending} = this.view;
        if (this.disposed || pending || snapshot.state !== "ready" || !snapshot.session || snapshot.event_id) return;
        await this.command("upload", () => this.rpc.upload(snapshot.session!, true), snapshot.session);
    }

    dispose(): void {
        this.disposed = true;
        ++this.epoch;
        this.clearPoll();
        for (const cancel of this.cancelRequests) cancel();
        this.listeners.clear();
    }
}
