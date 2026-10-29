const manifest = {"name":"FatterPad"};
const API_VERSION = 2;
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
}
const callable = api.callable;
const toaster = api.toaster;
const definePlugin = (fn) => (...args) => fn(...args);

const DFL = window.DFL;
const SP_REACT = window.SP_REACT;
const SP_JSX = window.SP_JSX;
const { useEffect, useState } = SP_REACT;
const jsx = SP_JSX.jsx;
const jsxs = SP_JSX.jsxs;

const status = callable("status");
const setLayout = callable("set_layout");
const forget = callable("forget");
const setIdentity = callable("set_identity");
const setNintendo = callable("set_nintendo");
const NMODE_ON = "The game sees a Switch Pro: its own Nintendo prompts, ZL/ZR on or off. From its next launch.";
const NMODE_OFF = "Analog triggers, Xbox prompts. Turn on for a game that ships Nintendo prompts.";
const NMODE_WHY = { "PCGamingWiki": "PCGamingWiki says it has Nintendo prompts", "this game": "set for this game" };
const log = (...a) => console.log("[FatterPad]", ...a);

// The game Steam is running (null in the library with nothing open). For a
// non-Steam shortcut this is its shortcut app id, the same number gamescope
// reports as the focused app.
function runningApp() {
    try {
        const a = DFL.Router && DFL.Router.MainRunningApp;
        if (a && a.appid) return { appid: Number(a.appid), name: a.display_name || "" };
    } catch (e) {
        log("running app lookup failed", e);
    }
    return null;
}

const WHY = { "default": "the default", "Steam UI": "Steam's UI", "Steam UI (default)": "the default" };
function because(why) {
    if (!why) return "";
    if (WHY[why]) return WHY[why];
    if (why.startsWith("class ")) return `every ${why.slice(6)} game`;
    if (why.startsWith("launcher ")) return `our emulator launcher (${why.slice(9)})`;
    if (why.startsWith("app ")) return "this game";
    return why;
}
const NINTENDO_ON = "The printed A on the right is A. For Switch and other Nintendo-style games.";
const NINTENDO_OFF = "Like an Xbox pad: when the game says A, press the bottom button.";

function Content() {
    const [st, setSt] = useState(null);
    const [busy, setBusy] = useState(false);
    const [byClass, setByClass] = useState(false);
    const app = runningApp();

    const refresh = async () => {
        try {
            const r = await status(app ? app.appid : null);
            setSt(r);
            if (r && r.game_because) setByClass(r.game_because.startsWith("class "));
        } catch (e) {
            setSt({ ok: false, error: String(e) });
        }
    };
    useEffect(() => { refresh(); }, []);

    const game = st && st.ok ? st.game : null;
    const layout = st && st.ok ? (st.game_layout || st.layout) : null;
    const title = (app && app.name) || (game && game.title) || "";
    const row = (child) => jsx(DFL.PanelSectionRow, { children: child });

    const change = async (fn) => {
        if (busy) return;
        setBusy(true);
        try {
            const r = await fn();
            if (!r || !r.ok) {
                toaster.toast({ title: "FatterPad", body: (r && r.error) || "could not change the layout", duration: 6000 });
            }
        } catch (e) {
            toaster.toast({ title: "FatterPad", body: String(e), duration: 6000 });
        } finally {
            setBusy(false);
            refresh();
        }
    };

    if (!st) return jsx(DFL.PanelSection, { children: row(jsx("div", { children: "…" })) });
    if (!st.ok) return jsx(DFL.PanelSection, { children: row(jsx("div", { style: { fontSize: "12px" },
        children: `fatterpad-abxy is not answering: ${st.error}` })) });
    if (!game && !app) {
        return jsxs(DFL.PanelSection, { title: "Face buttons", children: [
            row(jsx(DFL.ToggleField, {
                label: "Nintendo layout for every game",
                description: st.default === "letters" ? NINTENDO_ON : NINTENDO_OFF,
                checked: st.default === "letters",
                disabled: busy,
                onChange: (on) => change(() => setLayout(on ? "letters" : "positions", "default", 0)),
            })),
            row(jsx("div", { style: { fontSize: "12px", opacity: 0.8 },
                children: "Start a game, then open this panel to pick its own layout." })),
        ] });
    }
    const appid = app ? app.appid : game.app;
    const scope = byClass ? "class" : "game";
    return jsxs(DFL.PanelSection, { title: "Face buttons", children: [
        row(jsx("div", { style: { fontSize: "13px", fontWeight: "bold" }, children: title || `App ${appid}` })),
        row(jsx(DFL.ToggleField, {
            label: "Nintendo layout (A on the right)",
            description: layout === "letters" ? NINTENDO_ON : NINTENDO_OFF,
            checked: layout === "letters",
            disabled: busy,
            onChange: (on) => change(() => setLayout(on ? "letters" : "positions", scope, appid)),
        })),
        row(jsx(DFL.ToggleField, {
            label: "Every game of this emulator",
            description: game && game.class ? `Saves the choice for all ${game.class} games.` : "Bring the game to the front once first.",
            checked: byClass,
            disabled: busy || !(game && game.class),
            onChange: (on) => setByClass(on),
        })),
        row(jsx(DFL.ToggleField, {
            label: "Nintendo mode",
            description: (st.game_nintendo ? NMODE_ON : NMODE_OFF)
                + (st.game_nintendo_because ? ` (${NMODE_WHY[st.game_nintendo_because] || st.game_nintendo_because})` : ""),
            checked: !!st.game_nintendo,
            disabled: busy || !(appid > 0 && appid < 2147483648),
            onChange: (on) => change(() => setNintendo(on ? "on" : "off", appid)),
        })),
        row(jsx(DFL.ButtonItem, {
            layout: "below",
            disabled: busy,
            onClick: () => change(() => forget(scope, appid)),
            children: "Back to the default",
        })),
        row(jsx("div", { style: { fontSize: "12px", opacity: 0.75 }, children:
            `Now: ${layout === "positions" ? "Xbox layout" : "Nintendo layout"}, from ${because(st.game_because || st.because)}.` })),
    ] });
}

var index = definePlugin(() => ({
    name: "FatterPad",
    content: jsx(Content, {}),
    // A gamepad's four face buttons.
    icon: jsx("svg", { viewBox: "0 0 24 24", width: "1em", height: "1em", fill: "currentColor",
        children: [
            jsx("circle", { cx: 12, cy: 5, r: 3 }, "n"),
            jsx("circle", { cx: 19, cy: 12, r: 3 }, "e"),
            jsx("circle", { cx: 12, cy: 19, r: 3 }, "s"),
            jsx("circle", { cx: 5, cy: 12, r: 3 }, "w"),
        ] }),
    alwaysRender: false,
}));

export { index as default };
