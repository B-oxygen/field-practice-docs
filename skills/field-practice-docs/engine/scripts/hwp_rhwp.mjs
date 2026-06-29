import { readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { join, extname } from "node:path";
import process from "node:process";

function resolveCore() {
  const bases = [import.meta.url, pathToFileURL(join(process.cwd(), "x.js")).href];
  for (const base of bases) {
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
    "usage: node hwp_rhwp.mjs <input.hwp|.hwpx> <output.hwp|.hwpx> [mapping.json]\n" +
      "  mapping.json = {\"old text\": \"new text\", ...} applied via replaceAll\n" +
      "  output format is chosen by the output extension (.hwp or .hwpx)\n" +
      "  with no mapping it converts input to the output format unchanged\n" +
      "  requires: npm install @rhwp/core",
  );
}

async function main() {
  const [input, output, mappingPath] = process.argv.slice(2);
  if (!input || !output) {
    usage();
    return 64;
  }
  const jsPath = resolveCore();
  if (jsPath === null) {
    console.error("@rhwp/core not found. Run: npm install @rhwp/core");
    return 69;
  }
  const wasmPath = jsPath.replace(/rhwp\.js$/, "rhwp_bg.wasm");
  globalThis.measureTextWidth = (font, text) =>
    text ? String(text).length * 10 : 0;
  const { initSync, HwpDocument } = await import(jsPath);
  initSync({ module: await readFile(wasmPath) });

  const doc = new HwpDocument(new Uint8Array(await readFile(input)));
  const summary = { input, output, pages: doc.pageCount(), replaced: {} };

  if (mappingPath) {
    const mapping = JSON.parse(await readFile(mappingPath, "utf8"));
    for (const [oldText, newText] of Object.entries(mapping)) {
      const res = JSON.parse(doc.replaceAll(oldText, newText, false));
      summary.replaced[oldText] = res.count ?? 0;
    }
  }

  const ext = extname(output).toLowerCase();
  const bytes = ext === ".hwp" ? doc.exportHwp() : doc.exportHwpx();
  await writeFile(output, Buffer.from(bytes));
  summary.bytes = bytes.length;
  doc.free();
  console.log(JSON.stringify(summary, null, 2));
  return 0;
}

process.exit(await main());
