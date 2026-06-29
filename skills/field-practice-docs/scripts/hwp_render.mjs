import { readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { join } from "node:path";
import process from "node:process";

function resolveCore() {
  for (const base of [
    import.meta.url,
    pathToFileURL(join(process.cwd(), "x.js")).href,
  ]) {
    try {
      return createRequire(base).resolve("@rhwp/core");
    } catch {
      continue;
    }
  }
  return null;
}

function usage() {
  console.error(
    "usage: node hwp_render.mjs <input.hwp|.hwpx> <pageIndex> <out.svg>\n" +
      "  renders one page to SVG for visual QA (rhwp engine, same as HOP)\n" +
      "  then on macOS: qlmanage -t -s 1200 -o . out.svg  (SVG -> out.svg.png)\n" +
      "  requires: npm install @rhwp/core",
  );
}

async function main() {
  const [input, page, output] = process.argv.slice(2);
  if (!input || !output) {
    usage();
    return 64;
  }
  const jsPath = resolveCore();
  if (jsPath === null) {
    console.error("@rhwp/core not found. Run: npm install @rhwp/core");
    return 69;
  }
  globalThis.measureTextWidth = (font, text) =>
    text ? String(text).length * 10 : 0;
  const { initSync, HwpDocument } = await import(jsPath);
  initSync({ module: await readFile(jsPath.replace(/rhwp\.js$/, "rhwp_bg.wasm")) });
  const doc = new HwpDocument(new Uint8Array(await readFile(input)));
  const index = Number(page || 0);
  const svg = doc.renderPageSvg(index);
  await writeFile(output, svg);
  console.log(
    JSON.stringify({
      input,
      page: index,
      pages: doc.pageCount(),
      svgBytes: svg.length,
      output,
    }),
  );
  doc.free();
  return 0;
}

process.exit(await main());
