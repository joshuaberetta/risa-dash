// RISA page 1: Common Operational Picture; and page 2, key findings, when d.pages has 2.
//
// Reads data.json, map.jpg, inset.jpg, overview.jpg, qr.svg, feedback.svg and sym/*.svg from the same folder,
// all written by risa/page1.py. The map frame size comes from data.page, the same
// numbers the worker used to render map.jpg, so the image fits exactly.
//
//   typst compile --font-path fonts --ignore-system-fonts page1.typ out.pdf

#let d = json("data.json")
#let P = d.page
#let L = d.labels
#let C = d.colors
#let ink = rgb(C.ink)
#let muted = rgb(C.muted)
#let rule = rgb(C.rule)
#let mm = 1mm

#let map-w = P.map.at(0) * mm
#let map-h = P.map.at(1) * mm
#let side-w = P.side * mm

#set page(width: P.w * mm, height: P.h * mm, margin: 0pt, fill: white)
#set text(font: "Inter", size: P.base * 1pt, fill: ink, lang: d.lang, hyphenate: false)
#set par(leading: 0.42em, spacing: 0.6em)

#let eyebrow(body) = text(size: 0.74em, weight: 600, tracking: 0.06em, fill: muted, upper(body))

// ---- header band --------------------------------------------------------------
#let band(title: d.title, page-label: L.page) = block(width: 100%, height: P.band * mm, fill: rgb(C.band), inset: (x: 0.55 * P.band * mm, y: 0pt), {
  set text(fill: rgb(C.band_ink))
  align(horizon, grid(
    columns: (auto, 1fr, auto), column-gutter: 0.35 * P.band * mm, align: horizon,
    // The national authority leads; RISA is credited as the method in the footer
    block(width: 0.16 * P.w * mm, {
      if d.authority != "" {
        grid(columns: (auto, 1fr), column-gutter: 0.6em, align: horizon,
          circle(radius: 0.2 * P.band * mm, stroke: 0.6pt + rgb(C.band_ink)),
          text(size: 0.9em, weight: 700, d.authority))
      } else { text(size: 0.9em, weight: 700, fill: rgb(C.band_ink).transparentize(40%), "RISA") }
    }),
    stack(spacing: 0.55em,
      text(size: 2.1em, weight: 700, title),
      text(size: 0.95em, fill: rgb(C.band_ink).transparentize(15%), d.subtitle)),
    align(right, {
      if d.code != "" {
        box(fill: rgb(C.accent), inset: (x: 0.5em, y: 0.3em), radius: 1.5pt,
          text(size: 0.85em, weight: 700, fill: rgb(C.accent_ink), d.code))
        linebreak()
      }
      text(size: 0.85em, d.date)
      linebreak()
      text(size: 0.85em, if d.glide != "" { d.glide + " · " + page-label } else { page-label })
    }),
  ))
})

// ---- map overlays -------------------------------------------------------------
#let north = rotate(-d.bearing * 1deg, box(width: 7mm, height: 10mm, {
  place(top + left, polygon(fill: ink, stroke: 1pt + white,
    (3.5mm, 0mm), (5.9mm, 6.2mm), (3.5mm, 4.8mm), (1.1mm, 6.2mm)))
  place(center + bottom, text(size: 0.8em, weight: 700, stroke: 1.6pt + white, "N"))
  place(center + bottom, text(size: 0.8em, weight: 700, "N"))
}))

#let scalebar = block(fill: white.transparentize(10%), inset: (x: 2mm, y: 1.6mm), radius: 1pt, {
  let w = d.scale.mm * mm
  box(width: w, height: 1.6mm, stroke: 0.5pt + ink, {
    place(left, rect(width: w / 2, height: 1.6mm, fill: ink, stroke: none))
  })
  v(0.6mm)
  box(width: w, text(size: 0.72em, { [0]; h(1fr); d.scale.label }))
  linebreak()
  text(size: 0.68em, fill: muted, [#d.scale.ratio #L.scale_note])
})

// Locator maps: the area round the site, and a country overview under it with the
// area's extent marked and joined to it by leader lines (as on MapAction's maps).
// Positions are in mm from the top left of the container (map frame or side panel).
#let LC = P.at("locators", default: (place: "map", area: none, overview: none, size: (0, 0)))
#let loc-area = if d.at("has_inset", default: false) { LC.area } else { none }
#let loc-over = if d.at("has_overview", default: false) { LC.overview } else { none }
#let loc-box(f, file) = place(top + left, dx: f.x * mm, dy: f.y * mm,
  block(width: f.w * mm, height: f.h * mm, clip: true, stroke: 0.6pt + ink, fill: white,
    image(file, width: 100%, height: 100%, fit: "cover")))
#let leader(a, b) = {
  place(top + left, line(start: a, end: b, stroke: (paint: white, thickness: 1.8pt, cap: "round")))
  place(top + left, line(start: a, end: b, stroke: 0.6pt + ink))
}
#let locators = {
  if loc-area != none { loc-box(loc-area, "inset.jpg") }
  if loc-over != none { loc-box(loc-over, "overview.jpg") }
  let m = d.at("marker", default: none)
  if loc-area != none and loc-over != none and m != none {
    let (a, o) = (loc-area, loc-over)
    let on-over(fx, fy) = ((o.x + fx * o.w) * mm, (o.y + fy * o.h) * mm)
    leader((a.x * mm, (a.y + a.h) * mm), on-over(m.at(0), m.at(1)))
    leader(((a.x + a.w) * mm, (a.y + a.h) * mm), on-over(m.at(2), m.at(1)))
  }
}
#let has-locators = loc-area != none or loc-over != none

#let map-frame = block(width: map-w, height: map-h, clip: true, stroke: (right: 0.5pt + rule), {
  image("map.jpg", width: map-w, height: map-h, fit: "cover")
  if has-locators and LC.place == "map" { locators }
  place(top + right, dx: -5mm, dy: 4mm, north)
  place(bottom + left, dx: 4mm, dy: -4mm, scalebar)
  if d.draft {
    place(center + horizon, rotate(-20deg, text(size: 6em, weight: 800, fill: white.transparentize(45%),
      stroke: 0.6pt + ink.transparentize(70%), L.draft)))
  }
})

// ---- legend -------------------------------------------------------------------
// Same patterns as the web map: solid open, dashed restricted, dotted closed
#let dash = (ok: none, partial: (array: (2.4mm, 1.2mm), phase: 0pt), no: (array: (0mm, 2mm), phase: 0pt), unknown: none)
#let route-swatch(st) = box(width: 9mm, height: 3mm, baseline: 25%, {
  place(horizon, line(length: 9mm, stroke: (paint: white, thickness: 1.9mm)))
  place(horizon, line(length: 9mm, stroke: (paint: rgb(C.status.at(st)), thickness: if st == "no" { 1.25mm } else { 1.05mm },
    dash: dash.at(st), cap: if st == "no" { "round" } else { "butt" })))
})
#let sym(file, size: 1.25em) = box(baseline: 22%, image(file, width: size, height: size))
#let leg-row(swatch, label) = grid(columns: (auto, 1fr), column-gutter: 0.5em, align: horizon, swatch, text(size: 0.88em, label))
#let leg-inline(swatch, label) = box({ swatch; h(0.35em); text(size: 0.88em, label) })

#let legend = {
  let lg = d.legend
  let an = lg.at("analysis", default: (classes: (), simulated: false, suggested: false))
  if lg.routes.len() == 0 and lg.services.len() == 0 and lg.areas.len() == 0 and an.classes.len() == 0 {
    text(fill: muted, L.no_features)
  }
  if lg.routes.len() > 0 {
    eyebrow(L.routes)
    v(0.25em)
    stack(spacing: 0.35em, ..lg.routes.map(st => leg-row(route-swatch(st), L.route_status.at(st))))
    v(0.7em)
  }
  if lg.services.len() > 0 {
    eyebrow(L.services)
    v(0.25em)
    grid(columns: (1fr, 1fr), column-gutter: 0.8em, row-gutter: 0.35em,
      ..lg.services.map(s => leg-row(sym("sym/" + s.type + "-ok.svg"), s.label)))
    v(0.45em)
    lg.statuses.map(st => leg-inline(sym("sym/water-" + st + ".svg"), L.status.at(st))).join(h(0.9em))
    v(0.7em)
  }
  if an.classes.len() > 0 {
    eyebrow(L.analysis + if an.simulated { " (" + L.simulated + ")" } else { "" })
    v(0.25em)
    stack(spacing: 0.35em, ..an.classes.map(c => leg-row(
      box(width: 6mm, height: 3.4mm, baseline: 20%,
        fill: if c.area { none } else { rgb(c.color).transparentize(65%) },
        stroke: (paint: rgb(c.color), thickness: if c.area { 1pt } else { 0.7pt },
          dash: if an.suggested { "dashed" } else { none })), c.label)))
    if an.suggested { v(0.2em); text(size: 0.78em, fill: muted, L.dashed) }
    v(0.7em)
  }
  if lg.areas.len() > 0 {
    eyebrow(L.areas)
    v(0.25em)
    stack(spacing: 0.35em, ..lg.areas.map(a => leg-row(
      box(width: 6mm, height: 3.4mm, baseline: 20%, fill: rgb(a.fill), stroke: 0.6pt + rgb(a.stroke)), a.label)))
  }
}

// ---- side panel ---------------------------------------------------------------
#let glance-box(g) = block(width: 100%, stroke: 0.5pt + rule, radius: 1.5pt, inset: (x: 0.6em, y: 0.55em), {
  text(size: 1.75em, weight: 700, if g.value != "" { g.value } else { "–" })
  linebreak()
  text(size: 0.78em, fill: muted, g.label)
  if g.tbc {
    h(0.4em)
    box(stroke: 0.5pt + muted, inset: (x: 0.25em, y: 0.15em), radius: 1pt, baseline: 15%,
      text(size: 0.66em, weight: 700, fill: muted, L.tbc))
  }
})

#let side = block(width: side-w, height: map-h, inset: (x: P.side_pad.at(0) * mm, y: P.side_pad.at(1) * mm), clip: true, {
  if has-locators and LC.place == "side" {
    block(width: LC.size.at(0) * mm, height: LC.size.at(1) * mm, locators)
    v(0.9em)
  }
  if d.key_message != "" {
    block(stroke: (left: 0.8mm + ink), inset: (left: 0.8em, y: 0.1em), {
      eyebrow(L.key_message)
      v(0.3em, weak: true)
      text(size: 1.05em, weight: 600, d.key_message)
    })
    v(0.9em)
  }
  grid(columns: (1fr, 1fr), gutter: 0.5em, ..d.glance.map(glance-box))
  v(1.1em)
  legend
})

// ---- footer -------------------------------------------------------------------
#let footer = block(width: 100%, height: P.foot * mm, stroke: (top: 0.5pt + rule), inset: (x: 0.55 * P.band * mm, y: 0pt), {
  set text(size: 0.7em, fill: muted)
  let qr(file, label) = grid(columns: (auto, auto), column-gutter: 0.6em, align: horizon,
    image(file, width: 0.75 * P.foot * mm), box(width: 5.5em, label))
  let feedback = d.at("feedback", default: "") != ""
  grid(columns: (1fr, auto, auto, auto) + (if feedback { (auto,) } else { () }), column-gutter: 6mm, align: horizon,
    par(leading: 0.35em, [*#L.sources:* #d.sources \ #d.disclaimer]),
    align(center, [#L.produced_with \ #text(size: 1.5em, weight: 800, fill: ink, "RISA") #L.method]),
    [#L.support \ #text(weight: 700, fill: ink, d.credits)],
    qr("qr.svg", L.scan),
    ..(if feedback { (qr("feedback.svg", L.feedback),) } else { () }),
  )
})

// ---- page ---------------------------------------------------------------------
#stack(spacing: 0pt, band(), grid(columns: (map-w, side-w), map-frame, side), footer)

// ---- page 2: key findings ------------------------------------------------------
#let pages = d.at("pages", default: (1,))
#if pages.contains(2) {
  let q = d.p2
  let L2 = q.labels
  let st-color(st) = rgb(C.status.at(st))
  // A status pill: colour and a word, so it reads in black and white too
  let pill(st, label) = box(stroke: 0.7pt + st-color(st), fill: st-color(st).transparentize(88%), radius: 6pt,
    inset: (x: 0.45em, y: 0.18em), baseline: 18%, text(size: 0.78em, weight: 700, fill: st-color(st).darken(25%), label))
  let heading(n, body) = block(below: 0.8em, grid(columns: (auto, 1fr), column-gutter: 0.55em, align: horizon,
    box(width: 1.7em, height: 1.7em, radius: 50%, fill: ink, align(center + horizon, text(weight: 800, fill: white, str(n)))),
    text(size: 1.45em, weight: 700, body)))
  let sub(body, note: none) = block(above: 1.2em, below: 0.5em, {
    eyebrow(body)
    if note != none { h(0.4em); text(size: 0.74em, fill: muted, note) }
  })
  let empty(body) = text(size: 0.9em, fill: muted, body)
  let col-h = (P.h - P.band - P.foot) * mm
  let pad = 0.55 * P.band * mm

  let q1 = {
    heading(1, L2.q1)
    if q.routes_open != "" { block(below: 0.8em, { pill(q.verdict, L.route_status.at(q.verdict)); h(0.5em); text(weight: 600, q.routes_open) }) }
    if q.routes.len() == 0 { empty(L2.no_routes) }
    stack(spacing: 0.55em, ..q.routes.map(r => grid(columns: (auto, auto, 1fr), column-gutter: 0.5em, align: (left + horizon, left + horizon, left),
      route-swatch(r.status), text(weight: 700, if r.label != "" { r.label } else { "–" }),
      text(size: 0.9em, fill: muted, [#L.route_status.at(r.status)#if r.note != "" [ · #r.note]]))))
    if q.reach_note != "" {
      block(above: 1em, width: 100%, fill: rgb(C.accent), inset: 0.75em, radius: 2pt, stroke: (left: 0.8mm + ink),
        text(weight: 600, q.reach_note))
    }
    if q.logistics.len() > 0 {
      sub(L2.logistics)
      stack(spacing: 0.55em, ..q.logistics.map(x => grid(columns: (auto, 1fr), column-gutter: 0.5em,
        pill(x.status, L.status.at(x.status)),
        [#text(weight: 700, x.label)#if x.label != x.kind [ #text(size: 0.85em, fill: muted, x.kind)]#if x.note != "" [ \ #text(size: 0.88em, fill: muted, x.note)]])))
    }
  }

  let q2 = {
    heading(2, L2.q2)
    if q.services.len() == 0 { empty(L2.no_services) } else {
      set text(size: 0.95em)
      let cell(v, st) = text(weight: 700, fill: if v > 0 { st-color(st).darken(20%) } else { muted }, if v > 0 { str(v) } else { "–" })
      table(columns: (1fr, auto, auto, auto, auto), stroke: none, inset: (x: 0.35em, y: 0.42em),
        align: (left, right, right, right, right),
        table.hline(stroke: 0.6pt + ink),
        text(weight: 700, L2.service), text(weight: 700, L2.total), text(weight: 700, fill: st-color("ok").darken(20%), L2.working),
        text(weight: 700, fill: st-color("partial").darken(20%), L2.partly), text(weight: 700, fill: st-color("no").darken(20%), L2.not),
        table.hline(stroke: 0.4pt + rule),
        ..q.services.map(s => (s.label, str(s.total), cell(s.ok, "ok"), cell(s.partial, "partial"), cell(s.no, "no"))).flatten(),
        table.hline(stroke: 0.4pt + rule))
    }
    sub(L2.by_block, note: L2.on_imagery)
    if q.blocks.len() == 0 { empty(L2.no_blocks) }
    stack(spacing: 0.4em, ..q.blocks.map(b => grid(columns: (4.5em, 1fr, 3em), column-gutter: 0.5em, align: horizon,
      text(size: 0.9em, b.label),
      box(width: 100%, height: 0.75em, fill: rgb(C.accent), radius: 1pt,
        box(width: b.shelters / q.block_max * 100%, height: 100%, fill: rgb("#C8A86B"), radius: 1pt)),
      align(right, text(weight: 700, str(b.shelters))))))
    if q.people != "" {
      block(above: 1em, {
        text(size: 1.5em, weight: 800, q.people); h(0.3em); text(L2.people)
        if q.households != "" { h(0.6em); text(size: 1.5em, weight: 800, q.households); h(0.3em); text(L2.households) }
        h(0.5em)
        box(stroke: 0.5pt + muted, inset: (x: 0.25em, y: 0.15em), radius: 1pt, baseline: 15%,
          text(size: 0.7em, weight: 700, fill: muted, L2.estimate + ", " + L.tbc))
        linebreak()
        text(size: 0.8em, fill: muted, q.household_note)
      })
    }
  }

  let q3 = {
    heading(3, L2.q3)
    if q.gaps.len() == 0 { empty(L2.no_gaps) }
    stack(spacing: 1em, ..q.gaps.enumerate().map(((i, g)) => grid(columns: (auto, 1fr), column-gutter: 0.7em,
      box(width: 1.9em, height: 1.9em, radius: 2pt, fill: st-color(g.status), align(center + horizon,
        text(size: 1.15em, weight: 800, fill: white, str(i + 1)))),
      {
        text(size: 1.1em, weight: 700, g.title)
        if g.at("text", default: "") != "" { linebreak(); text(size: 0.95em, g.text) }
        linebreak()
        v(0.15em)
        pill(g.status, if g.status == "no" { L2.urgent } else { L2.high })
        if g.at("who", default: "") != "" { h(0.4em); text(size: 0.85em, weight: 600, fill: muted, g.who) }
      })))
  }

  pagebreak()
  // Read at a glance, often from a wall: larger than page 1's side panel
  set text(size: P.base * 1.2pt)
  stack(spacing: 0pt,
    band(title: L2.title, page-label: L2.page),
    block(width: 100%, height: col-h, inset: (x: pad, y: 0.6 * pad),
      grid(columns: (1fr, 1fr, 1.15fr), column-gutter: 1.4 * pad,
        // Headings level across the columns: the same top inset in each
        block(inset: (top: 0.4 * pad), q1), block(stroke: (left: 0.5pt + rule), inset: (left: 0.7 * pad, top: 0.4 * pad), q2),
        block(width: 100%, height: 100%, fill: rgb(C.accent).lighten(50%), inset: (x: 0.7 * pad, top: 0.4 * pad, bottom: 0.7 * pad),
          radius: 2pt, q3))),
    footer)
}
