import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../../mcias/web_workspace/views.js", import.meta.url), "utf8");
const workspace = source.slice(source.indexOf("const clauseSections = ["), source.indexOf("function batchFourFileExports("));

test("eight canonical input sections exist and have a unified action toolbar", () => {
  for (const section of ["contracts","providers","beneficiaries","copays","categories","exclusions","approvals","tariffs"]) {
    assert.match(workspace, new RegExp('\\["' + section + '",'));
  }
  assert.match(workspace, /fileArea\.append\(importAction, addAction, editAction\)/);
  assert.match(workspace, /L\("تعديل", "Edit"\)/);
  assert.match(workspace, /L\("إضافة", "Add"\)/);
  assert.match(workspace, /L\("استيراد ملف \(رفع المصدر\)", "Import file \(source upload\)"\)/);
});
test("edit requires a selected source record and retains append-only revision linkage", () => {
  assert.match(workspace, /editAction\.disabled = true/);
  assert.match(workspace, /selectedRecord = \{\.\.\.record, section\}/);
  assert.match(workspace, /editAction\.disabled = ctx\.demo \|\| !allowed\(ctx, "reference\.write"\)/);
  assert.match(workspace, /replaces_id:previous\?\.id \|\| null/);
  assert.match(workspace, /method:"POST",body:/);
});
test("upload clearly remains source-stage only, not falsely certified extraction", () => {
  assert.match(workspace, /Upload alone does not extract or approve clauses/);
  assert.match(workspace, /Automated clause extraction is not activated/);
});
