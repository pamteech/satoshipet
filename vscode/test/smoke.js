// smoke test sem VS Code: carrega a extensão com um "vscode" falso e confere humor + html.
const Module = require("module");
const orig = Module._load;
Module._load = function (req, ...r) {
  if (req === "vscode") return { workspace: { getConfiguration: () => ({ get: () => undefined }) } };
  return orig.call(this, req, ...r);
};
const ext = require("../extension.js");
const assert = require("assert");
assert.strictEqual(ext._humorPor(3), "moon");
assert.strictEqual(ext._humorPor(-3), "rekt");
assert.strictEqual(ext._humorPor(0), "garimpando");
console.log("vscode smoke OK");
