const req = window.webpackChunksteamui.push([[Symbol("thor-pads")], {}, r => r]);
for (const id of Object.keys(req.m)) {
  let e; try { e = req(id); } catch (x) { continue; }
  if (!e || typeof e !== "object") continue;
  for (const k of Object.keys(e)) {
    let v; try { v = e[k]; } catch (x) { continue; }
    if (v && typeof v === "object" && "m_controllerList" in v) {
      const l = v.m_controllerList;
      const arr = Array.isArray(l) ? l : (l && typeof l.values === "function" ? Array.from(l.values()) : Object.values(l || {}));
      return arr.map(c => { const o = {}; for (const f of Object.keys(c)) { const x = c[f]; if (["string","number","boolean"].includes(typeof x)) o[f] = x; } return o; });
    }
  }
}
return "store not found";
