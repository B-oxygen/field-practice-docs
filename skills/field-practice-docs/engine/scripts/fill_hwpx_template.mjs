import { spawnSync } from "node:child_process";

const result = spawnSync("uv", ["run", "python", "-m", "field_practice.cli", "fill-template", ...process.argv.slice(2)], {
  stdio: "inherit",
});

process.exit(result.status ?? 1);
