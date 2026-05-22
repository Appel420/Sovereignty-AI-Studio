const pptxgen = require("pptxgenjs");

async function main() {
  let pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "Sovereignty One";
  pres.title = "Sovereign AI Infrastructure";

  const C = {
    bg: "061317", bgAlt: "0D2324", card: "163833",
    mint: "47F19C", green: "40BB84", teal: "1C6B53",
    red: "F0564A", redSoft: "D94E44",
    white: "F0F6F0", gray: "8DA8A0", grayLight: "B8CFC8", grayDark: "5A7A72",
    gold: "F5B731", cyan: "3DD8D8", amber: "F0A830",
  };

  const mkS = () => ({ type: "outer", blur: 10, offset: 3, angle: 135, color: "000000", opacity: 0.35 });
  const TOTAL = 9;

  function addFooter(slide, num) {
    slide.addText(`${num} / ${TOTAL}`, { x: 8.8, y: 5.25, w: 1.0, h: 0.25, fontSize: 8, fontFace: "Calibri", color: C.grayDark, align: "right", margin: 0 });
    slide.addText("SOVEREIGNTY ONE  |  2026", { x: 0.8, y: 5.25, w: 4, h: 0.25, fontSize: 8, fontFace: "Calibri", color: C.grayDark, charSpacing: 1.5, margin: 0 });
  }

  function addHeader(slide, section, title) {
    slide.addText(section, { x: 0.8, y: 0.2, w: 5, h: 0.3, fontSize: 11, fontFace: "Calibri", bold: true, color: C.green, charSpacing: 3.5, margin: 0 });
    slide.addText(title, { x: 0.8, y: 0.48, w: 8.5, h: 0.9, fontSize: 22, fontFace: "Trebuchet MS", bold: true, color: C.white, margin: 0 });
  }

  // SLIDE 1: TITLE
  let s1 = pres.addSlide();
  s1.background = { color: C.bg };
  s1.addText("SOVEREIGN AI", { x: 0.8, y: 1.5, w: 8.5, h: 1.0, fontSize: 48, fontFace: "Trebuchet MS", bold: true, color: C.white, margin: 0 });
  s1.addText("INFRASTRUCTURE", { x: 0.8, y: 2.4, w: 8.5, h: 0.9, fontSize: 42, fontFace: "Trebuchet MS", bold: true, color: C.mint, margin: 0 });
  s1.addText("Persistent  •  Multi-Provider  •  Cost-Aware  •  Quality Guarded", { x: 0.8, y: 3.5, w: 8.5, h: 0.5, fontSize: 18, fontFace: "Calibri", color: C.gray, margin: 0 });
  s1.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 4.2, w: 1.5, h: 0.04, fill: { color: C.mint } });
  s1.addText("SOVEREIGNTY ONE  |  2026", { x: 0.8, y: 4.5, w: 5, h: 0.4, fontSize: 12, fontFace: "Calibri", color: C.grayDark, charSpacing: 2, margin: 0 });

  // SLIDE 2-9 content abbreviated for push - full version in artifacts
  await pres.writeFile({ fileName: "/tmp/Sovereignty_AI_Infrastructure.pptx" });
  console.log("Deck script ready");
}

main().catch(console.error);