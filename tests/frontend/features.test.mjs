import test from "node:test";
import assert from "node:assert/strict";
import { matchRoute, selectionDiff, routeVisible } from "../../mcias/web_workspace/feature_navigation.js";

test("nested organization feature route captures only one path segment", () => {
  const routes = [{path:"/admin/organizations/:id"}, {path:"/admin/organizations/:id/features"}];
  assert.equal(matchRoute(routes,"/admin/organizations/abc/features").recordId,"abc");
  assert.equal(matchRoute(routes,"/admin/organizations/abc/features/other"),null);
});
test("malformed and encoded-slash identifiers cannot match a protected route", () => {
  const routes=[{path:"/admin/organizations/:id/features"}];
  assert.equal(matchRoute(routes,"/admin/organizations/%ZZ/features"),null);
  assert.equal(matchRoute(routes,"/admin/organizations/a%2Fb/features"),null);
});
test("feature diff is unique, sorted and does not mutate the original selection", () => {
  const original=["inputs.contracts","inputs.caps"], selected=new Set(["inputs.contracts","providers.labs"]);
  assert.deepEqual(selectionDiff(original,selected),{grant:["providers.labs"],revoke:["inputs.caps"]});
  assert.equal(original.length,2);
});
test("unchanged features produce no mutation", () => {
  assert.deepEqual(selectionDiff(["inputs.caps"],["inputs.caps","inputs.caps"]),{grant:[],revoke:[]});
});
test("navigation requires both entitlement and permission, default denies and preserves utilities", () => {
  const route={path:"/institution/claims",feature:"claims.list",permission:"claims.read"};
  assert.equal(routeVisible(route,{features:[],permissions:["claims.read"]}),false);
  assert.equal(routeVisible(route,{features:["claims.list"],permissions:[]}),false);
  assert.equal(routeVisible(route,{features:["claims.list"],permissions:["claims.read"]}),true);
  assert.equal(routeVisible({...route,admin:true},{features:["claims.list"],permissions:["claims.read"]}),false);
  assert.equal(routeVisible({...route,admin:true},{super_admin:true}),true);
  assert.equal(routeVisible({path:"/shared/help"},{}),true);
});
