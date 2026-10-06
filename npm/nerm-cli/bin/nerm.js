#!/usr/bin/env node
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const platform = process.platform;
const arch = process.arch;
const pkg = `@nerm-cli/${platform}-${arch}`;
const binName = platform === "win32" ? "nerm.exe" : "nerm";

function resolveBinary() {
  const local = path.join(__dirname, binName);
  if (fs.existsSync(local)) {
    return local;
  }
  try {
    return require.resolve(`${pkg}/bin/${binName}`);
  } catch (err) {
    console.error(
      `nerm binary not found for ${platform}-${arch}. Install nerm-cli with npm, or run a matching platform package.`
    );
    process.exit(1);
  }
}

const child = spawn(resolveBinary(), process.argv.slice(2), {
  stdio: "inherit",
  windowsHide: true,
});
child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  }
  process.exit(code ?? 1);
});
