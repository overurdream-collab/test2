import test from 'node:test';
import assert from 'node:assert/strict';
import { matchRoute, routeVisibleForContext, navigationGroupsForContext } from '../mcias/web_workspace/w1_navigation.js';
const routes = [
  {path:'/admin/users',kind:'users',admin:true,permission:'users.read',availability:'partial'},
  {path:'/institution/dashboard',kind:'dashboard',admin:false,permission:'reports.read',availability:'partial'},
  {path:'/institution/claims',kind:'claims',admin:false,permission:'claims.read',availability:'partial'},
  {path:'/institution/hidden',kind:'unavailable',permission:'',availability:'unavailable'},
  {path:'/institution/claims/:id',kind:'claim-detail',permission:'claims.read'},
];
test('W1 routes: exact, parameterized, malformed and nested',()=>{
  assert.equal(matchRoute(routes,'/institution/dashboard').route.kind,'dashboard');
  assert.equal(matchRoute(routes,'/institution/claims/abc').recordId,'abc');
  assert.equal(matchRoute(routes,'/institution/claims/%2F'),null);
  assert.equal(matchRoute(routes,'/institution/claims/a/b'),null);
});
test('W1 three roles: main permissions and Super Admin admin gate',()=>{
  const superAdmin={roles:['super_admin'],permissions:['users.read','reports.read','claims.read']};
  const admin={roles:['admin'],permissions:['reports.read','claims.read']};
  const user={roles:['user'],permissions:['reports.read']};
  assert.equal(routeVisibleForContext(routes[0],superAdmin),true);
  assert.equal(routeVisibleForContext(routes[0],admin),false);
  assert.equal(routeVisibleForContext(routes[2],admin),true);
  assert.equal(routeVisibleForContext(routes[2],user),false);
  assert.equal(routeVisibleForContext(routes[3],superAdmin),false);
  assert.equal(routeVisibleForContext(routes[1],user),true);
});
test('W1 navigation excludes unsupported and unauthorized routes',()=>{
  const user={roles:['user'],permissions:['reports.read']};
  const visible=navigationGroupsForContext(routes,'institution',user).flatMap(g=>g[2].map(r=>r.path));
  assert.deepEqual(visible,['/institution/dashboard']);
});
