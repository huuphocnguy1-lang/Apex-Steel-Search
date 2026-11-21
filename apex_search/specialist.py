"""Steel Specialist: troubleshooting for ESP, casting, hot strip mill, pay-off reel, laminar cooling, hydraulics."""
from . import search

AREAS = [("ESP", "ESP line"), ("Caster", "Casting"), ("RM", "HRM / roughing mill"), ("PS", "Pendulum shear & piler"),
         ("IDH", "Induction heater & descaler"), ("HSM", "Finishing mill (FM)"), ("LC", "Laminar cooling"),
         ("DC", "HSS & down coilers"), ("HYD", "Hydraulics"), ("POR", "Pay-off reel")]

SHORT = {"ESP": "ESP", "Caster": "Caster", "RM": "HRM / RM", "PS": "Pendulum shear", "IDH": "IDH / descaler",
         "HSM": "FM", "LC": "Cooling", "DC": "HSS & coilers", "HYD": "Hydraulics", "POR": "POR"}

AREA_BRIEF = {
    "ESP": "Endless strip production (thin slab caster directly coupled to roughing mill, induction heater and finishing "
           "mill): casting speed / mill mass-flow coupling, induction heater power and exit temperature, descaling, "
           "loopers, strip tracking, flying shear and coilers, interaction between caster events and mill stability.",
    "Caster": "Continuous casting (incl. thin slab / funnel mould): ladle, turret, tundish, stopper rod, SEN, argon, "
              "mould level control, mould powder, oscillation (frequency, stroke, negative strip time), mould heat flux "
              "and thermocouples, breakout prediction (stickers), EMS/EMBr, secondary cooling, soft/liquid core "
              "reduction, segment roll gap and bulging, straightening and the 700–900 °C ductility trough, "
              "liquidus/superheat, defects (longitudinal/transverse/corner cracks, centre segregation, inclusions, "
              "pinholes), SEN clogging.",
    "RM": "High Reduction Mill / roughing stands R1–R4 directly after the caster: large reductions with the casting "
          "heat, HGC and AGC (gaugemeter, mill modulus), tilt / wedge / camber, crown C25/C40, centre-line deviation, "
          "interstand tension control by speed (no loopers), roll cooling, work-roll bending / shifting, main drives, "
          "roll change and calibration (balancing, taration, contact, zeroing, modulus test).",
    "PS": "Pendulum (pendular) shear SHP and pusher / piler: plate mode at casting start or when the FM is not ready, "
          "batch cuts, emergency / tail-out cuts, coil-mode permissives, eccentric knife frame, encoders, knife "
          "clearance and wear, overload (OVL), hydraulic balancing and swivelling, knife cooling, cut length from "
          "bar speed and tracking, piler / pusher lift and travel, knife-change safety.",
    "IDH": "Induction heater (inductors, medium-frequency converters, cooling water, entry / exit pyrometers, power "
           "distribution), edge heater, rotary crop shear SHR, high-pressure descaler (pumps, accumulators, headers, "
           "nozzles), scale defects.",
    "DC": "High-speed flying shear (drum / cam, encoders, cut angle, fly-wheel, lubrication) and down coilers DC1–3 "
          "(pinch rolls, side guides, mandrel expansion, wrapper rolls step control and calibration, coil change in "
          "endless mode, telescoping, coil marks, LAS speed).",
    "HSM": "Hot strip mill / finishing mill: AGC and roll gap, interstand tension, looper control and oscillation, "
           "mass-flow mismatch, roll wear and thermal crown, flatness and profile, FDT, cobbles and strip breaks, side "
           "guides, edge defects, scale, downcoilers, set-up model adaptation.",
    "POR": "Pay-off reels (pickling / cold mill entry): mandrel expansion, coil loading, CPC/EPC strip centring, back "
           "tension, deflector and pinch rolls, telescoped coils, strip wandering, entry welder interaction.",
    "LC": "Laminar cooling and coiling temperature control: top/bottom header banks, valves and positioners, water "
          "pressure and temperature, edge masking, pyrometers (steam, dirty windows), cooling model and adaptation, "
          "CT deviations along the strip, flatness after cooling.",
    "HYD": "Industrial hydraulics (ISO 1219): pumps (fixed / variable / pressure-compensated), servo and proportional "
           "valves, directional, relief, reducing, counterbalance and pilot-operated check valves, accumulators "
           "(nitrogen pre-charge), cylinders and seals, filtration and ISO 4406 cleanliness, flushing, oil temperature "
           "and viscosity, cavitation, internal leakage, servo hunting and hysteresis, hydraulic safety "
           "(residual pressure, accumulators, suspended loads).",
}

FORMAT = (
    "Structure every troubleshooting answer with these headings:\n"
    "**What I understand / what I see** (describe attached photos first: equipment, damage, readable text, alarms)\n"
    "**Likely causes** (numbered, most likely first, with the reason)\n"
    "**Checks** (signals to look at, measurements, inspections — concrete)\n"
    "**Actions**\n"
    "**Safety** (lock-out/tag-out, residual pressure, hot metal, radioactive sources… when relevant)\n"
    "Cite document sources as [n]. PAST CASE sources are the plant's own lessons learned: use them when similar. "
    "Never invent plant-specific set points: if a value is not in the sources, give a typical range and say "
    "'check your plant value'. Answer in the same language as the question."
)


def system_prompt(area: str) -> str:
    return ("You are the Apex Steel Specialist, a senior engineer specialised in ESP endless strip production lines "
            "(Arvedi / Primetals), industrial hydraulics and the steel process, with commissioning and troubleshooting "
            "experience on caster, HRM, pendulum shear, induction heater, finishing mill, cooling and coilers. "
            + search.SOURCE_RULES + "Area of this question: "
            f"{dict(AREAS).get(area, area)}. Expertise: {AREA_BRIEF.get(area, '')}\n\n{FORMAT}\n"
            "You assist engineers: always remind to follow OEM procedures for safety-critical work.")


def specialist_answer(db, ai, area: str, question: str, history=None, attachments=None, extra_context: str = "",
                      on_token=None) -> dict:
    import json as _json
    attachments = attachments or []
    key = None
    if not history and not attachments and question.strip():
        key = search.cache_key("specialist", area, ai.chat_model_label(), question, extra_context)
        hit = db.cache_get(key, (getattr(ai, "cfg", None) or {}).get("answer_cache_days", 7))
        if hit:
            res = _json.loads(hit)
            res["cached"] = True
            if on_token:
                on_token(res["text"])
            return res
    q = question.strip() or "Analyse the attached file(s) and troubleshoot the problem they show."
    probe = q + " " + area + " " + " ".join(a["text"][:300] for a in attachments) + " " + extra_context[:500]
    srcs = search._gather_sources(db, ai, probe, max_sources=4, budget=5500)
    cases = db.similar_cases(probe, area, k=3)
    sources, blocks, n = [], [], 0
    if extra_context:
        blocks.append("CONTEXT FROM THE ANALYSIS TOOL:\n" + extra_context[:6000])
    for a in attachments:
        n += 1
        body = a["text"][:6000] if a["text"] else ("(picture attached — see image)" if a.get("image") else "(no text)")
        blocks.append(f"[{n}] ATTACHED BY USER: {a['name']}\n{body}")
        sources.append((n, None, a["name"], a["path"]))
    for c in cases:
        n += 1
        blocks.append(f"[{n}] PAST CASE {c['date']} ({c['area']}): symptom: {c['symptom']} | root cause: {c['cause']} | fix: {c['fix']}")
        sources.append((n, None, f"Lesson learned {c['date']}: {c['symptom'][:60]}", None))
    for fid, texts in srcs.items():
        r = db.get(fid)
        if r is None:
            continue
        n += 1
        org = search.source_origin(r["path"])
        blocks.append(f"[{n}] {search.source_label(org)}: {r['name']}\n" + "\n…\n".join(texts))
        sources.append((n, fid, search.source_icon(org) + r["name"], r["path"]))
    msgs = [{"role": "system", "content": system_prompt(area)}]
    for h in (history or [])[-4:]:
        msgs.append({"role": h["role"], "content": h["content"][:1500]})
    msgs.append({"role": "user", "content": "SOURCES:\n\n" + ("\n\n".join(blocks) or "(none found)") + f"\n\nQUESTION: {q}"})
    images = [a["image"] for a in attachments if a.get("image")]
    text = ai.chat(msgs, images=images or None, on_token=on_token)
    res = {"text": text, "sources": sources, "cases": [dict(c) for c in cases]}
    if key and text:
        db.cache_put(key, _json.dumps(res))
    return res


def specialist_with_files(db, ai, area, question, history, paths, cfg, extra_context="", on_token=None):
    att = search.prepare_attachments(paths, cfg) if paths else None
    return specialist_answer(db, ai, area, question, history, att, extra_context, on_token)


# ------------------------------------------------------------------ metallurgy helpers
LIQUIDUS_COEF = {"C": 78, "Si": 7.6, "Mn": 4.9, "P": 34.4, "S": 38, "Cu": 4.7, "Ni": 3.1, "Cr": 1.3, "Al": 3.6}


def liquidus(comp: dict) -> float:
    """General empirical liquidus (°C). Plant grade tables always have priority."""
    return 1536 - sum(LIQUIDUS_COEF[k] * float(comp.get(k, 0) or 0) for k in LIQUIDUS_COEF)


def casting_temperatures(comp: dict, superheat: float = 25, ladle_losses: float = 38) -> dict:
    tl = liquidus(comp)
    return {"liquidus": tl, "tundish": tl + superheat, "ladle": tl + superheat + ladle_losses}
