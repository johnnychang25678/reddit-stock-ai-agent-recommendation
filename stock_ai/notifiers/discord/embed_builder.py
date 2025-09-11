import json
import math
import datetime as dt

FIELD_LIMIT = 1024  # Discord limit per field value
TITLE_LIMIT = 256
DESC_LIMIT = 4096

def _truncate(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[:limit-1] + "…"

def _chunk_field(name: str, value: str, inline=False):
    """Yield one or more fields, chunking value to <= 1024 chars each."""
    if not value:
        return []
    chunks = [value[i:i+FIELD_LIMIT] for i in range(0, len(value), FIELD_LIMIT)]
    if len(chunks) == 1:
        return [{"name": name, "value": chunks[0], "inline": inline}]
    fields = []
    for idx, part in enumerate(chunks, 1):
        suffix = f" (part {idx})"
        fields.append({"name": _truncate(name + suffix, 256), "value": part, "inline": inline})
    return fields


def _json_or_none(s):
    if not s or not isinstance(s, str): return None
    try: return json.loads(s)
    except json.JSONDecodeError: return None

def _fmt(v, n=2):
    if v is None: return "—"
    if isinstance(v, (int,)): return str(v)
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v): return "—"
        return f"{v:.{n}f}"
    return str(v)

def _color_for_conf(conf: str | None) -> int:
    # high -> green, medium -> yellow, low -> gray, default discord blurple
    table = {"high": 0x00B894, "medium": 0xF1C40F, "low": 0x95A5A6}
    return table.get((conf or "").lower(), 0x7289DA)

def build_embed(ticker: str, info: dict) -> dict:
    rec = _json_or_none(info.get("stock_recommendations"))
    snap = info.get("snapshot") or {}
    plans_raw = info.get("portfolio") or []
    plan = next((p for p in ([_json_or_none(x) for x in plans_raw]) if p), None)

    # ----- top: TRADING PLAN (prominent, first) -----
    if plan:
        entry = _fmt(plan.get("entry_price"))
        stop  = _fmt(plan.get("stop_loss"))
        tps   = ", ".join(_fmt(x) for x in (plan.get("take_profits") or [])) or "—"
        rr    = _fmt(plan.get("risk_reward"))
        hz    = _fmt(plan.get("time_horizon_days"), 0)
        rationale = plan.get("rationale") or ""
        plan_desc = (
            f"**🧭 Trading Strategy For You**\n"
            f"**Entry:** {entry}   |   **Stop:** {stop}\n"
            f"**Targets:** {tps}\n"
            f"**Horizon:** {hz} days   |   **R/R:** {rr}\n"
            f"{('**Why:** ' + rationale) if rationale else ''}"
        )
    else:
        plan_desc = "**🧭 Trading Strategy For You**\nNo plan available."

    # ----- fields below the plan -----
    fields = []

    # Recommendation (reason + link)
    if rec:
        reason = rec.get("reason") or "—"
        conf   = rec.get("confidence")
        srcurl = rec.get("reddit_post_url")
        rec_lines = [
                     f"**Reddit Post URL:** {srcurl}" if srcurl else None,
                     f"**Analysis:** {reason}",
                     ]
        fields.append({"name": "Source", "value": "\n".join([x for x in rec_lines if x]), "inline": False})
    else:
        conf = None  # for color

    # Snapshot after that
    if snap:
        snap_str = "\n".join(f"{k}: {v}" for k, v in snap.items() if k != "error")
        fields.append({"name": "Snapshot", "value": snap_str, "inline": False})
        if snap.get("error"):
            fields.append({"name": "Data Note", "value": str(snap['error']), "inline": False})

    embed = {
        "title": f"{ticker} {'(confidence: ' + conf.capitalize() if conf else ''})",
        "description": plan_desc,            # PLAN FIRST & bolded labels
        "color": _color_for_conf(conf),
        "fields": fields[:10],               # keep tidy
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "footer": {"text": "Stock-AI weekly report"},
    }
    return embed