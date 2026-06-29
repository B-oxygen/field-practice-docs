import { readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const [, , sourcePath, targetPath] = process.argv;

if (!sourcePath || !targetPath) {
  console.error("usage: node scripts/markdown_to_hwpx.mjs <source.md> <target.hwpx>");
  process.exit(64);
}

async function loadKordoc() {
  try {
    return await import("kordoc");
  } catch {
    console.error(
      "kordoc is not installed. Install Node.js dependencies with `npm install kordoc`, then rerun export-hwpx.",
    );
    process.exit(2);
  }
}

function pickConverter(kordoc) {
  const candidates = [
    kordoc.markdownToHwpx,
    kordoc.markdownToHwpX,
    kordoc.default?.markdownToHwpx,
    kordoc.default?.markdownToHwpX,
  ];
  return candidates.find((candidate) => typeof candidate === "function");
}

async function main() {
  const markdown = await readFile(sourcePath, "utf8");
  const kordoc = await loadKordoc();
  const converter = pickConverter(kordoc);
  if (!converter) {
    console.error("kordoc is installed, but no markdown-to-HWPX converter export was found.");
    process.exit(3);
  }
  const converted = await converter(markdown, { baseDir: dirname(fileURLToPath(import.meta.url)) });
  const buffer = Buffer.isBuffer(converted) ? converted : Buffer.from(converted);
  await writeFile(targetPath, buffer);
}

await main();
