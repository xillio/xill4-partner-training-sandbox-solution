const pptxgen = require("pptxgenjs");

const INK   = "10201E", INK2 = "1B302C", TEAL = "0E6B60", TEAL_LT = "4CC0AE";
const PAPER = "F6F8F7", WHITE = "FFFFFF", AMBER = "B4720E", AMBER_W = "F6EDDC";
const MUTED = "56635F", MUTED_D = "9BB0AB", NEUTRAL = "8A9794";
const RULE  = "DCE3E1", TINT = "E7F0EE";
const HEAD = "Cambria", BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.33 x 7.5 -- set before any slide
pres.author = "Kamil Beeli de Belfort";
pres.title  = "Xill4 Partner Training Sandbox";

const W = 13.33, M = 0.62, CW = W - M * 2;

/* ---------- helpers ---------- */

function light() {
  const s = pres.addSlide();
  s.background = { color: PAPER };
  return s;
}
function dark() {
  const s = pres.addSlide();
  s.background = { color: INK };
  return s;
}

// chapter marker + slide title. The number is the motif, repeated on every chapter slide.
function header(s, num, chapter, title) {
  s.addShape(pres.ShapeType.ellipse, {
    x: M, y: 0.42, w: 0.46, h: 0.46, fill: { color: TEAL },
  });
  s.addText(String(num), {
    x: M, y: 0.42, w: 0.46, h: 0.46, isTextBox: true, align: "center", valign: "middle",
    fontFace: BODY, fontSize: 15, bold: true, color: WHITE, margin: 0,
  });
  s.addText(chapter.toUpperCase(), {
    x: M + 0.66, y: 0.44, w: CW - 0.7, h: 0.42, isTextBox: true, valign: "middle",
    fontFace: BODY, fontSize: 10.5, bold: true, color: TEAL, charSpacing: 2, margin: 0,
  });
  s.addText(title, {
    x: M, y: 1.06, w: CW, h: 0.72, isTextBox: true,
    fontFace: HEAD, fontSize: 30, bold: true, color: INK, margin: 0,
  });
}

function card(s, o) {
  s.addShape(pres.ShapeType.roundRect, {
    x: o.x, y: o.y, w: o.w, h: o.h, rectRadius: 0.06,
    fill: { color: o.fill || WHITE },
    line: { color: o.line || RULE, width: 1 },
  });
}

function stat(s, x, y, w, value, label) {
  s.addText(value, {
    x: x, y: y, w: w, h: 0.78, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 40, bold: true, color: INK,
  });
  s.addText(label, {
    x: x, y: y + 0.8, w: w, h: 0.6, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 11.5, color: MUTED,
  });
}

// bold lead + description on one row, with a small teal dot as the marker
function row(s, x, y, w, lead, desc, dotColor) {
  s.addShape(pres.ShapeType.ellipse, {
    x: x, y: y + 0.13, w: 0.12, h: 0.12, fill: { color: dotColor || TEAL },
  });
  s.addText(
    [
      { text: lead, options: { bold: true, color: INK } },
      { text: desc ? "  " + desc : "", options: { color: MUTED } },
    ],
    { x: x + 0.28, y: y, w: w - 0.28, h: 0.52, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13.5, valign: "top" }
  );
}

function note(s, y, text, color) {
  s.addText(text, {
    x: M, y: y, w: CW, h: 0.5, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 11, italic: true, color: color || MUTED,
  });
}

/* ---------- 1. title ---------- */
{
  const s = dark();
  s.addText("BUDGET PROPOSAL", {
    x: M, y: 1.5, w: 7.6, h: 0.35, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, bold: true, color: TEAL_LT, charSpacing: 3,
  });
  s.addText("A Xillio-owned sandbox\nfor partner training", {
    x: M, y: 2.0, w: 7.8, h: 1.9, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 40, bold: true, color: WHITE, lineSpacing: 46,
  });
  s.addText(
    "Own the training environment instead of borrowing the partner's — so exercises can be designed, paced and verified automatically.",
    { x: M, y: 4.05, w: 7.3, h: 1.0, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 15, color: MUTED_D }
  );
  s.addText("Kamil Beeli de Belfort   ·   Partner Training   ·   September 2026", {
    x: M, y: 6.5, w: 8.5, h: 0.4, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 11, color: MUTED_D, charSpacing: 1,
  });

  // motif: one host, many sandboxes -- 3 of 12 filled
  const gx = 9.0, gy = 2.15, cw = 1.02, ch = 0.78, gap = 0.16;
  s.addText("ONE HOST, TWELVE SANDBOXES", {
    x: gx, y: 1.55, w: 3.8, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 9.5, bold: true, color: MUTED_D, charSpacing: 2,
  });
  for (let r = 0; r < 4; r++) {
    for (let c = 0; c < 3; c++) {
      const filled = r * 3 + c < 3;
      s.addShape(pres.ShapeType.roundRect, {
        x: gx + c * (cw + gap), y: gy + r * (ch + gap), w: cw, h: ch, rectRadius: 0.05,
        fill: { color: filled ? TEAL : INK2 },
        line: { color: filled ? TEAL : "2C4340", width: 1 },
      });
    }
  }
  s.addNotes("Framing: the environment we train in is the constraint. Everything in this deck follows from owning it.");
}

/* ---------- 2. agenda ---------- */
{
  const s = light();
  s.addText("Agenda", {
    x: M, y: 0.55, w: CW, h: 0.8, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 32, bold: true, color: INK,
  });
  s.addText("Six chapters, and what each one covers", {
    x: M, y: 1.32, w: CW, h: 0.4, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 13.5, color: MUTED,
  });

  const chapters = [
    ["Why change", "What the partner-provided environment costs us today"],
    ["What we propose", "A sandbox Xillio owns, with exercises Xillio authors"],
    ["Where the time goes", "The trainer's 40 hours per cohort, and how delivery changes"],
    ["Systems and dashboards", "What trainees practise against, and who gets to see what"],
    ["Proof", "How we will know whether it actually worked"],
    ["Cost and decision", "Budget, payback, and what is being asked for"],
  ];
  let y = 2.0;
  chapters.forEach(([name, desc], i) => {
    s.addShape(pres.ShapeType.ellipse, {
      x: M + 0.06, y: y + 0.06, w: 0.5, h: 0.5, fill: { color: i < 3 ? TEAL : INK },
    });
    s.addText(String(i + 1), {
      x: M + 0.06, y: y + 0.06, w: 0.5, h: 0.5, isTextBox: true, align: "center",
      valign: "middle", fontFace: BODY, fontSize: 16, bold: true, color: WHITE, margin: 0,
    });
    s.addText(name, {
      x: M + 0.8, y: y, w: 4.2, h: 0.4, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 16, bold: true, color: INK,
    });
    s.addText(desc, {
      x: M + 5.0, y: y + 0.03, w: CW - 5.1, h: 0.45, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: MUTED,
    });
    if (i < chapters.length - 1) {
      s.addShape(pres.ShapeType.line, {
        x: M + 0.8, y: y + 0.68, w: CW - 0.9, h: 0, line: { color: RULE, width: 1 },
      });
    }
    y += 0.78;
  });
  s.addNotes("Walk the six chapters, then say the decision asked for is Phase 1 only.");
}

/* ---------- 3. ch1a problem ---------- */
{
  const s = light();
  header(s, 1, "Why change", "We don’t own the environment the training runs on");
  s.addText("Trainees work in an environment the partner provides. Five consequences follow.", {
    x: M, y: 1.82, w: CW, h: 0.4, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 13.5, color: MUTED,
  });
  const items = [
    ["No control", "over what is installed, what data exists, or when it is available"],
    ["Exercises can’t be designed in advance", "— the data isn’t ours"],
    ["Pacing depends on someone else’s IT", "— training stalls when the environment isn’t ready"],
    ["No two partners get the same training", "— outcomes vary by partner, not by engineer"],
    ["Hands-on work can’t be verified automatically", "— we don’t know what “correct” looks like in their environment"],
  ];
  let y = 2.45;
  items.forEach(([lead, desc]) => { row(s, M, y, CW, lead, desc); y += 0.72; });
  card(s, { x: M, y: 6.16, w: CW, h: 0.72, fill: TINT, line: TINT });
  s.addText("Every one of these is a consequence of borrowing the environment — not of how the training is taught.", {
    x: M + 0.3, y: 6.16, w: CW - 0.6, h: 0.72, isTextBox: true, valign: "middle", margin: 0,
    fontFace: BODY, fontSize: 13, bold: true, color: TEAL,
  });
}

/* ---------- 4. ch1b numbers ---------- */
{
  const s = light();
  header(s, 1, "Why change", "Partner training today, by the numbers");
  const w = (CW - 0.9) / 4;
  stat(s, M,                 2.15, w, "€10,000", "Fixed price per cohort,\nwhatever the headcount");
  stat(s, M + (w + 0.3),     2.15, w, "40 h",       "Trainer time per cohort");
  stat(s, M + (w + 0.3) * 2, 2.15, w, "15+",        "Cohorts a year");
  stat(s, M + (w + 0.3) * 3, 2.15, w, "3 → 4",  "Partner trainers,\nwith a fourth in training");

  s.addShape(pres.ShapeType.line, { x: M, y: 4.05, w: CW, h: 0, line: { color: RULE, width: 1 } });

  card(s, { x: M, y: 4.35, w: (CW - 0.35) / 2, h: 1.5 });
  s.addText("Ramp-up", {
    x: M + 0.35, y: 4.6, w: 4.5, h: 0.35, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 11, bold: true, color: TEAL, charSpacing: 1.5,
  });
  s.addText("Over two months to project-ready today.\nThe target is four weeks.", {
    x: M + 0.35, y: 4.98, w: (CW - 0.35) / 2 - 0.7, h: 0.8, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 14.5, color: INK,
  });

  card(s, { x: M + (CW - 0.35) / 2 + 0.35, y: 4.35, w: (CW - 0.35) / 2, h: 1.5 });
  s.addText("Non-billable share", {
    x: M + (CW - 0.35) / 2 + 0.7, y: 4.6, w: 4.5, h: 0.35, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 11, bold: true, color: AMBER, charSpacing: 1.5,
  });
  s.addText("About a quarter of a cohort’s hours are non-billable — pure cost, no revenue attached.", {
    x: M + (CW - 0.35) / 2 + 0.7, y: 4.98, w: (CW - 0.35) / 2 - 0.7, h: 0.9, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 14.5, color: INK,
  });
  note(s, 6.15, "Hours from Harvest, one representative cohort. Price is fixed per cohort, so hours saved improve margin and release senior capacity.");
}

/* ---------- 5. ch2a proposal ---------- */
{
  const s = light();
  header(s, 2, "What we propose", "A sandbox Xillio owns, with exercises Xillio authors");
  const items = [
    ["One isolated Xill4 instance per trainee", "reached in a browser, no partner setup"],
    ["An exercise per topic", "controlled scope, defined outcome, realistic messy data"],
    ["Automatic verification", "scored in seconds, naming the specific wrong value"],
    ["Progress recorded per topic", "not one pass or fail at the end"],
    ["The partner picks source and target systems", "practice matches the migration they must deliver"],
  ];
  let y = 2.0;
  items.forEach(([lead, desc]) => { row(s, M, y, 7.1, lead, desc); y += 0.8; });

  card(s, { x: 8.05, y: 2.0, w: W - 8.05 - M, h: 2.9, fill: TINT, line: TINT });
  s.addText("WHY IT CAN ONLY WORK HERE", {
    x: 8.4, y: 2.25, w: 3.9, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 9.5, bold: true, color: TEAL, charSpacing: 2,
  });
  s.addText("Because Xillio authors the extraction scope, the transformation rules and the target structure, the correct outcome is known before the trainee starts.\n\nThat is what makes automatic verification possible.", {
    x: 8.4, y: 2.62, w: 3.9, h: 2.1, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 14, color: INK, lineSpacing: 20,
  });
  card(s, { x: 8.05, y: 5.1, w: W - 8.05 - M, h: 1.35 });
  s.addText("Precedent", {
    x: 8.4, y: 5.28, w: 3.9, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10.5, bold: true, color: MUTED, charSpacing: 1.5,
  });
  s.addText("The practical Xill4 exam is already marked automatically. This extends that from one exam to every topic.", {
    x: 8.4, y: 5.6, w: 3.9, h: 0.8, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12.5, color: INK,
  });
}

/* ---------- 6. ch2b trainee flow ---------- */
{
  const s = light();
  header(s, 2, "What we propose", "What a trainee actually does");
  const steps = [
    ["Read the brief", "The scope, the rules, the target structure — written by us"],
    ["Build it in Xill4", "Their own instance, their own copy of the messy data"],
    ["Press Check my work", "As often as they like, with no penalty for attempts"],
    ["Score in seconds", "Which tasks passed, which value was wrong, next topic unlocks"],
  ];
  const cwid = (CW - 3 * 0.45) / 4;
  steps.forEach(([t, d], i) => {
    const x = M + i * (cwid + 0.45);
    card(s, { x: x, y: 2.25, w: cwid, h: 2.5 });
    s.addShape(pres.ShapeType.ellipse, {
      x: x + 0.28, y: 2.55, w: 0.44, h: 0.44, fill: { color: TEAL },
    });
    s.addText(String(i + 1), {
      x: x + 0.28, y: 2.55, w: 0.44, h: 0.44, isTextBox: true, align: "center",
      valign: "middle", fontFace: BODY, fontSize: 14, bold: true, color: WHITE, margin: 0,
    });
    s.addText(t, {
      x: x + 0.28, y: 3.15, w: cwid - 0.56, h: 0.45, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 15, bold: true, color: INK,
    });
    s.addText(d, {
      x: x + 0.28, y: 3.62, w: cwid - 0.56, h: 1.0, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12, color: MUTED,
    });
    if (i < 3) {
      s.addShape(pres.ShapeType.rightArrow, {
        x: x + cwid + 0.09, y: 3.38, w: 0.27, h: 0.22, fill: { color: TEAL_LT },
      });
    }
  });
  card(s, { x: M, y: 5.15, w: CW, h: 1.25, fill: TINT, line: TINT });
  s.addText("Each trainee’s practice data is generated from their own identity", {
    x: M + 0.35, y: 5.38, w: CW - 0.7, h: 0.35, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 14, bold: true, color: TEAL,
  });
  s.addText("Same kinds of defect, different records. An answer passed between trainees scores zero — so nobody has to police it.", {
    x: M + 0.35, y: 5.75, w: CW - 0.7, h: 0.5, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 13, color: INK,
  });
}

/* ---------- 7. ch3a hours chart ---------- */
{
  const s = light();
  header(s, 3, "Where the time goes", "Where the trainer’s 40 hours go");

  const data = [{
    name: "Hours",
    labels: ["Support & Q&A", "Project artifacts", "Xill4 setup", "Teaching sessions", "Kick-offs"],
    values: [12.0, 10.5, 8.25, 7.25, 2.5],
  }];
  s.addChart(pres.ChartType.bar, data, {
    x: M, y: 1.95, w: 8.0, h: 3.5,
    barDir: "bar", barGapWidthPct: 45,
    chartColors: [TEAL, TEAL, TEAL, NEUTRAL, NEUTRAL],
    varyColors: true,
    showLegend: false,
    showTitle: false,
    showValue: true,
    dataLabelPosition: "outEnd",
    dataLabelFontFace: BODY, dataLabelFontSize: 11, dataLabelColor: INK,
    catAxisLabelFontFace: BODY, catAxisLabelFontSize: 12, catAxisLabelColor: INK,
    valAxisLabelFontFace: BODY, valAxisLabelFontSize: 10, valAxisLabelColor: MUTED,
    valAxisMaxVal: 14,
    valGridLine: { color: RULE, size: 1 },
    catGridLine: { style: "none" },
    valAxisLineShow: false, catAxisLineShow: false,
    plotArea: { fill: { color: PAPER } },
  });

  card(s, { x: 9.0, y: 1.95, w: W - 9.0 - M, h: 3.5, fill: WHITE, line: RULE });
  s.addShape(pres.ShapeType.rect, { x: 9.35, y: 2.28, w: 0.22, h: 0.22, fill: { color: TEAL } });
  s.addText("Addressable by the sandbox", {
    x: 9.68, y: 2.2, w: 3.0, h: 0.38, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, bold: true, color: INK,
  });
  s.addText("Support, artifacts and setup:\n30.75 of 40.5 hours — 76%", {
    x: 9.35, y: 2.62, w: 3.3, h: 0.7, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12.5, color: MUTED,
  });
  s.addShape(pres.ShapeType.rect, { x: 9.35, y: 3.5, w: 0.22, h: 0.22, fill: { color: NEUTRAL } });
  s.addText("Largely unchanged", {
    x: 9.68, y: 3.42, w: 3.0, h: 0.38, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, bold: true, color: INK,
  });
  s.addText("Teaching is reshaped into\nstand-ups, not removed.", {
    x: 9.35, y: 3.84, w: 3.3, h: 0.7, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12.5, color: MUTED,
  });
  s.addShape(pres.ShapeType.line, { x: 9.35, y: 4.62, w: 3.3, h: 0, line: { color: RULE, width: 1 } });
  s.addText("≈ 17.5 h saved per cohort", {
    x: 9.35, y: 4.75, w: 3.3, h: 0.45, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 15, bold: true, color: TEAL,
  });

  note(s, 5.62, "One representative cohort, from Harvest. Illustrative reduction: setup 8.25→1 h, support 12→6 h, artifacts 10.5→6 h. Confirming this is the pilot’s job.");
  note(s, 6.12, "A separate, atypical engagement ran to 20 hours of preparation because a trainer hand-built Azure VMs so the partner could train at all — that is the cost of having no sandbox, paid manually.", AMBER);
}

/* ---------- 8. ch3b delivery ---------- */
{
  const s = light();
  header(s, 3, "Where the time goes", "How the training itself changes");
  const colw = (CW - 0.5) / 2;

  card(s, { x: M, y: 2.0, w: colw, h: 2.75 });
  s.addText("TODAY", {
    x: M + 0.32, y: 2.2, w: colw - 0.64, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10, bold: true, color: MUTED, charSpacing: 2,
  });
  s.addText(
    [
      { text: "Long workshops and lectures", options: { bullet: true, breakLine: true } },
      { text: "Questions queue for the one person who can answer", options: { bullet: true, breakLine: true } },
      { text: "One practical exam at the end", options: { bullet: true, breakLine: true } },
      { text: "A trainee who slips holds up the cohort", options: { bullet: true } },
    ],
    { x: M + 0.32, y: 2.58, w: colw - 0.64, h: 2.0, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13.5, color: INK, paraSpaceAfter: 8 }
  );

  card(s, { x: M + colw + 0.5, y: 2.0, w: colw, h: 2.75, fill: TINT, line: TEAL });
  s.addText("WITH THE SANDBOX", {
    x: M + colw + 0.82, y: 2.2, w: colw - 0.64, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10, bold: true, color: TEAL, charSpacing: 2,
  });
  s.addText(
    [
      { text: "Short stand-ups: next tasks, review the last, deadlines", options: { bullet: true, breakLine: true } },
      { text: "Instant feedback, at any hour, unlimited attempts", options: { bullet: true, breakLine: true } },
      { text: "Graded evidence per topic, all the way through", options: { bullet: true, breakLine: true } },
      { text: "The cohort moves on; they finish self-paced", options: { bullet: true } },
    ],
    { x: M + colw + 0.82, y: 2.58, w: colw - 0.64, h: 2.0, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13.5, color: INK, paraSpaceAfter: 8 }
  );

  s.addText("Deadlines, as proposed", {
    x: M, y: 5.02, w: CW, h: 0.35, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 11, bold: true, color: TEAL, charSpacing: 1.5,
  });
  let y = 5.42;
  [
    ["A miss means nothing was submitted", "never a failed attempt — or trainees stop trying the hard ones"],
    ["One grace deferral per course", "stated in the joining terms, not discovered at enforcement"],
    ["Two misses: automatic notice", "to the trainee and the partner contact. Third: the trainer decides."],
  ].forEach(([lead, desc]) => { row(s, M, y, CW, lead, desc); y += 0.5; });
  s.addNotes("The self-paced window is only offerable because marking is automatic — it is a consequence of the sandbox, not a policy beside it.");
}

/* ---------- 9. ch4a systems ---------- */
{
  const s = light();
  header(s, 4, "Systems and dashboards", "What trainees practise against");
  s.addText("A source is read, a target is written — so a cohort can share one source, but each trainee needs their own target space.", {
    x: M, y: 1.82, w: CW, h: 0.4, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 13.5, color: MUTED,
  });

  const items = [
    ["File share", "Source or target", "A mounted folder per trainee", "Available first", TEAL],
    ["Object storage", "Target", "A bucket or prefix per trainee", "Small effort", TEAL],
    ["SharePoint Online", "Target · Migration API", "A folder per trainee in one shared site", "Medium effort", TEAL],
    ["OpenText Content Server", "Source", "None needed — one instance, read-only", "Demo VM in place", TEAL],
  ];
  const cwid = (CW - 0.45) / 2, chgt = 1.42;
  items.forEach(([name, role, iso, status], i) => {
    const x = M + (i % 2) * (cwid + 0.45);
    const y = 2.35 + Math.floor(i / 2) * (chgt + 0.35);
    card(s, { x: x, y: y, w: cwid, h: chgt });
    s.addText(name, {
      x: x + 0.32, y: y + 0.2, w: cwid - 2.4, h: 0.38, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 15.5, bold: true, color: INK,
    });
    s.addShape(pres.ShapeType.roundRect, {
      x: x + cwid - 2.0, y: y + 0.22, w: 1.72, h: 0.32, rectRadius: 0.04,
      fill: { color: TINT }, line: { color: TINT },
    });
    s.addText(status, {
      x: x + cwid - 2.0, y: y + 0.22, w: 1.72, h: 0.32, isTextBox: true, align: "center",
      valign: "middle", margin: 0, fontFace: BODY, fontSize: 9.5, bold: true, color: TEAL,
    });
    s.addText(role, {
      x: x + 0.32, y: y + 0.62, w: cwid - 0.64, h: 0.3, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 11, color: MUTED, charSpacing: 0.5,
    });
    s.addText(iso, {
      x: x + 0.32, y: y + 0.94, w: cwid - 0.64, h: 0.36, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: INK,
    });
  });

  card(s, { x: M, y: 5.9, w: CW, h: 0.95, fill: TINT, line: TINT });
  s.addText("Both ends of OpenText → SharePoint Online are already available to us — the OTCS demo VM as a shared read-only source. That is the migration partners most often have to deliver.", {
    x: M + 0.35, y: 5.9, w: CW - 0.7, h: 0.95, isTextBox: true, valign: "middle", margin: 0,
    fontFace: BODY, fontSize: 13, bold: true, color: TEAL,
  });
  s.addNotes("One adapter per system, built once, then usable by every exercise — so a menu of combinations is not a matrix of exercises.");
}

/* ---------- 10. ch4b dashboards ---------- */
{
  const s = light();
  header(s, 4, "Systems and dashboards", "Two dashboards, split on a trust boundary");
  const colw = (CW - 0.5) / 2;

  card(s, { x: M, y: 2.0, w: colw, h: 3.4 });
  s.addText("INTERNAL · PO AND TRAINER", {
    x: M + 0.32, y: 2.22, w: colw - 0.64, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10, bold: true, color: TEAL, charSpacing: 2,
  });
  s.addText(
    [
      { text: "All cohorts; progress per trainee, per topic", options: { bullet: true, breakLine: true } },
      { text: "Attention list: stuck vs silent — different problems", options: { bullet: true, breakLine: true } },
      { text: "Which exercise a whole cohort fails — the material, not the trainees", options: { bullet: true, breakLine: true } },
      { text: "Trainer hours per cohort as a trend, from Harvest", options: { bullet: true, breakLine: true } },
      { text: "Cohorts per quarter, completion, capacity", options: { bullet: true } },
    ],
    { x: M + 0.32, y: 2.62, w: colw - 0.64, h: 2.6, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: INK, paraSpaceAfter: 8 }
  );

  card(s, { x: M + colw + 0.5, y: 2.0, w: colw, h: 3.4 });
  s.addText("EXTERNAL · TRAINEE AND PARTNER", {
    x: M + colw + 0.82, y: 2.22, w: colw - 0.64, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10, bold: true, color: AMBER, charSpacing: 2,
  });
  s.addText(
    [
      { text: "A trainee sees only their own progress and deadlines", options: { bullet: true, breakLine: true } },
      { text: "A partner contact sees only their own engineers", options: { bullet: true, breakLine: true } },
      { text: "Never hours, never cost, never other trainees", options: { bullet: true, breakLine: true } },
      { text: "Completion evidence per topic, generated", options: { bullet: true } },
    ],
    { x: M + colw + 0.82, y: 2.62, w: colw - 0.64, h: 2.6, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: INK, paraSpaceAfter: 8 }
  );

  card(s, { x: M, y: 5.7, w: CW, h: 0.85, fill: TINT, line: TINT });
  s.addText("Trainees are external people, so this is a security boundary rather than a layout choice.", {
    x: M + 0.35, y: 5.7, w: CW - 0.7, h: 0.85, isTextBox: true, valign: "middle", margin: 0,
    fontFace: BODY, fontSize: 13, bold: true, color: TEAL,
  });
}

/* ---------- 11. ch5 proof ---------- */
{
  const s = light();
  header(s, 5, "Proof", "How we will know whether it worked");
  const items = [
    ["A new Harvest project is a requirement of running the pilot", "not a recommendation — the pilot does not start without it"],
    ["Its tasks roll up to today’s categories", "so the pilot compares against real past cohorts, not a blank page"],
    ["The baseline is fixed before the pilot starts", "from cohorts already logged, so nobody sets the bar afterwards"],
    ["The pilot passes only if both hold", "the hour target is met, and a real trainee judges the marking fair"],
  ];
  let y = 2.1;
  items.forEach(([lead, desc], i) => {
    s.addShape(pres.ShapeType.ellipse, {
      x: M + 0.02, y: y, w: 0.44, h: 0.44, fill: { color: i === 3 ? INK : TEAL },
    });
    s.addText(String(i + 1), {
      x: M + 0.02, y: y, w: 0.44, h: 0.44, isTextBox: true, align: "center", valign: "middle",
      margin: 0, fontFace: BODY, fontSize: 14, bold: true, color: WHITE,
    });
    s.addText(lead, {
      x: M + 0.72, y: y - 0.02, w: CW - 0.8, h: 0.4, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 15.5, bold: true, color: INK,
    });
    s.addText(desc, {
      x: M + 0.72, y: y + 0.36, w: CW - 0.8, h: 0.4, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: MUTED,
    });
    y += 0.98;
  });
  card(s, { x: M, y: 6.06, w: CW, h: 0.9, fill: TINT, line: TINT });
  s.addText("The request is therefore self-auditing: approval rests on a claimed reduction, and Harvest settles it by the third or fourth cohort.", {
    x: M + 0.35, y: 6.06, w: CW - 0.7, h: 0.9, isTextBox: true, valign: "middle", margin: 0,
    fontFace: BODY, fontSize: 13.5, bold: true, color: TEAL,
  });
}

/* ---------- 12. phases ---------- */
{
  const s = light();
  header(s, 5, "Proof", "Four phases, each with a gate");
  const phases = [
    ["Phase 1", "One sandbox, and a pilot", "Provision a Xill4 container per trainee, seed the data, run one exercise end to end with a real person.", "Gate: hours target met, and the trainee judges the marking fair", TEAL],
    ["Phase 2", "Cohort-ready", "Provisioning for a full cohort, sign-in for external trainees, both dashboards, automated notices.", "Gate: first cohort delivered; Harvest shows hours falling", TEAL],
    ["Phase 3", "Exercise library", "One exercise per topic, so stand-ups can replace workshops. Progression unlocks as trainees pass.", "Needs a day or two per exercise from the material owner", NEUTRAL],
    ["Phase 4", "Self-service enrolment", "Partners enrol when they need to; more source and target systems added as demand appears.", "", NEUTRAL],
  ];
  const cwid = (CW - 3 * 0.36) / 4;
  phases.forEach(([tag, name, desc, gate, color], i) => {
    const x = M + i * (cwid + 0.36);
    card(s, { x: x, y: 2.05, w: cwid, h: 4.0 });
    s.addShape(pres.ShapeType.roundRect, {
      x: x + 0.3, y: 2.32, w: 1.28, h: 0.34, rectRadius: 0.04,
      fill: { color: color }, line: { color: color },
    });
    s.addText(tag.toUpperCase(), {
      x: x + 0.3, y: 2.32, w: 1.28, h: 0.34, isTextBox: true, align: "center", valign: "middle",
      margin: 0, fontFace: BODY, fontSize: 9.5, bold: true, color: WHITE, charSpacing: 1,
    });
    s.addText(name, {
      x: x + 0.3, y: 2.82, w: cwid - 0.6, h: 0.7, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 15, bold: true, color: INK,
    });
    s.addText(desc, {
      x: x + 0.3, y: 3.5, w: cwid - 0.6, h: 1.5, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12, color: MUTED,
    });
    if (gate) {
      s.addShape(pres.ShapeType.line, {
        x: x + 0.3, y: 5.08, w: cwid - 0.6, h: 0, line: { color: RULE, width: 1 },
      });
      s.addText(gate, {
        x: x + 0.3, y: 5.2, w: cwid - 0.6, h: 0.75, isTextBox: true, margin: 0,
        fontFace: BODY, fontSize: 11.5, bold: true, color: TEAL,
      });
    }
  });
  note(s, 6.25, "Funds released one phase at a time, with a go or no-go at each boundary. Phase 1 is the only immediate spend.");
}

/* ---------- 13. cost ---------- */
{
  const s = light();
  header(s, 6, "Cost and decision", "Cost and payback");

  s.addText("ONE-OFF BUILD", {
    x: M, y: 1.95, w: 6.6, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10, bold: true, color: MUTED, charSpacing: 2,
  });
  s.addTable(
    [
      [
        { text: "Phase", options: { bold: true, color: MUTED, fontSize: 10 } },
        { text: "Effort", options: { bold: true, color: MUTED, fontSize: 10, align: "right" } },
        { text: "At €800/day", options: { bold: true, color: MUTED, fontSize: 10, align: "right" } },
      ],
      ["Phase 1 — sandbox and pilot", { text: "5–8 days", options: { align: "right" } }, { text: "€4,000–6,400", options: { align: "right" } }],
      ["Phase 2 — cohort-ready", { text: "15–25 days", options: { align: "right" } }, { text: "€12,000–20,000", options: { align: "right" } }],
      [
        { text: "Total", options: { bold: true } },
        { text: "20–33 days", options: { bold: true, align: "right" } },
        { text: "€16,000–26,400", options: { bold: true, align: "right" } },
      ],
    ],
    { x: M, y: 2.32, w: 6.6, colW: [3.3, 1.5, 1.8], rowH: 0.42,
      fontFace: BODY, fontSize: 12.5, color: INK, valign: "middle",
      border: { type: "solid", color: RULE, pt: 1 }, fill: { color: WHITE } }
  );

  s.addText("RETURN", {
    x: 7.65, y: 1.95, w: W - 7.65 - M, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10, bold: true, color: MUTED, charSpacing: 2,
  });
  card(s, { x: 7.65, y: 2.32, w: W - 7.65 - M, h: 1.94, fill: TINT, line: TINT });
  s.addText("≈ €26,000", {
    x: 8.0, y: 2.52, w: 4.4, h: 0.7, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 34, bold: true, color: TEAL,
  });
  s.addText("a year at 15 cohorts — about 17.5 hours saved per cohort, roughly €1,750 each", {
    x: 8.0, y: 3.2, w: 4.4, h: 0.9, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12.5, color: INK,
  });

  let y = 4.55;
  [
    ["Payback inside the first year", "on trainer hours alone"],
    ["Recurring: one shared host per cohort", "plus €800–1,600 per new exercise, written once and reused forever"],
    ["Price per cohort is fixed", "so hours saved improve margin and release senior capacity"],
    ["Not counted", "ramp-up falling from two months to four weeks"],
  ].forEach(([lead, desc]) => { row(s, M, y, CW, lead, desc); y += 0.52; });
  note(s, 6.65, "Effort figures are estimates. Phase 1 exists partly to replace the Phase 2 estimate with a measurement.");
}

/* ---------- 14. risks ---------- */
{
  const s = light();
  header(s, 6, "Cost and decision", "Risks, and what we do about them");
  const items = [
    ["Container resource use is unknown", "fewer sandboxes per host would raise Phase 2 hosting — Phase 1 measures it first", TEAL],
    ["Exercise authoring is the real ongoing cost", "infrastructure is cheap; curriculum is the investment — plan for it rather than discover it", TEAL],
    ["Trainee work lives in MongoDB", "keeping or resetting it is a database design task, not an afterthought", TEAL],
    ["Live cloud targets can fail correct work", "jobs queue and throttle — stand-ins teach technique; real services only where their friction is the lesson", AMBER],
    ["Licence terms per instance", "expected fine for training-only use; worth confirming in writing before Phase 2", AMBER],
  ];
  let y = 2.15;
  items.forEach(([lead, desc, c]) => { row(s, M, y, CW, lead, desc, c); y += 0.82; });
  s.addNotes("None of these are blocking. The first three are answered by Phase 1; the last two are decisions, not unknowns.");
}

/* ---------- 15. decision ---------- */
{
  const s = dark();
  s.addText("6  ·  COST AND DECISION", {
    x: M, y: 0.7, w: CW, h: 0.35, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10.5, bold: true, color: TEAL_LT, charSpacing: 2.5,
  });
  s.addText("What Phase 1 approval unlocks", {
    x: M, y: 1.2, w: 8.4, h: 0.9, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 34, bold: true, color: WHITE,
  });
  s.addText(
    [
      { text: "Work starts the same week — pull the image, stand up one sandbox, seed it, and put a real person through one exercise", options: { bullet: true, breakLine: true } },
      { text: "It produces the three things a Phase 2 decision needs: a working sandbox, measured cost per trainee, and a verdict on whether the marking is fair", options: { bullet: true, breakLine: true } },
      { text: "And it establishes the Harvest baseline that settles the business case either way", options: { bullet: true } },
    ],
    { x: M, y: 2.35, w: 7.6, h: 2.4, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 15, color: MUTED_D, paraSpaceAfter: 12 }
  );

  s.addShape(pres.ShapeType.roundRect, {
    x: 8.5, y: 2.35, w: W - 8.5 - M, h: 2.5, rectRadius: 0.07,
    fill: { color: TEAL }, line: { color: TEAL },
  });
  s.addText("RECOMMENDED", {
    x: 8.85, y: 2.62, w: 3.5, h: 0.3, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 9.5, bold: true, color: "BFE3DC", charSpacing: 2,
  });
  s.addText("Approve Phases 1 and 2 with a ceiling.\n\nRelease Phase 1 now.\n\nHold Phase 2 until Phase 1 reports.", {
    x: 8.85, y: 3.0, w: 3.5, h: 1.7, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 14.5, bold: true, color: WHITE, lineSpacing: 19,
  });

  s.addShape(pres.ShapeType.line, { x: M, y: 5.5, w: CW, h: 0, line: { color: "2C4340", width: 1 } });
  s.addText("Comments and questions welcome — the full written proposal carries a feedback box on every section.", {
    x: M, y: 5.72, w: CW, h: 0.5, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12.5, italic: true, color: MUTED_D,
  });
  s.addNotes("Ask for Phase 1 only. Everything else follows from what Phase 1 measures.");
}

pres.writeFile({ fileName: "Xill4-Partner-Training-Sandbox.pptx" })
  .then(f => console.log("wrote", f));
