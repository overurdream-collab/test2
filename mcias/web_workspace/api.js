/** @typedef {{id:string,username:string,organization:{id:string,name:string}|null,roles:string[],permissions:string[],expires_at:string}} SessionContext
 * @typedef {{id:string,batch_id:string,version:number,fingerprint:string,source_sha256:string,summary:{total_claims:number,by_currency:Object<string,object>}}} ReportSnapshot
 * @typedef {{items:object[],has_more:boolean,offset?:number,limit?:number}} Page
 */
import { L } from "./ui.js";
export class ApiError extends Error {
  constructor(status) {
    super(
      status === 401
        ? L(
            "انتهت الجلسة أو بيانات الدخول غير صحيحة.",
            "Session expired or credentials are invalid.",
          )
        : status === 403
          ? L(
              "الخادم رفض الوصول. راجع المسؤول لتوفير الصلاحية اللازمة.",
              "The server denied access. Ask your administrator for the required permission.",
            )
          : status === 404
            ? L(
                "لم يتم العثور على سجل مصرح بهذا المعرّف.",
                "No authorized record was found with this identifier.",
              )
            : status === 409
              ? L(
                  "تعارض في الحالة أو سلامة الأدلة أو فصل المسؤوليات.",
                  "State, evidence integrity or separation-of-duties conflict.",
                )
              : status === 422
                ? L(
                    "راجع الحقول وضوابط البيانات المطلوبة.",
                    "Check the fields and required data constraints.",
                  )
                : status === 429
                  ? L(
                      "طلبات كثيرة. أعد المحاولة لاحقًا.",
                      "Too many attempts. Try again later.",
                    )
                  : L(
                      "الخدمة غير متاحة. تحقق من اتصال الخادم.",
                      "Service unavailable. Check server connectivity.",
                    ),
    );
    this.status = status;
  }
}
export class ApiClient {
  #token = null;
  #epoch = 0;
  #controllers = new Set();
  #demo = null;
  #featureData = false;
  enableFeatureData() { this.#featureData = true; }
  onExpiry = () => {};
  setToken(value) {
    this.#token = value;
  }
  clear() {
    this.#featureData = false;
    this.#token = null;
    this.#demo = null;
    this.#epoch++;
    for (const c of this.#controllers) c.abort();
    this.#controllers.clear();
  }
  demo(fixture) {
    this.#demo = fixture;
  }
  async request(
    path,
    { method = "GET", body, raw = false, download = false } = {},
  ) {
    if (!path.startsWith("/api/v1/") && !path.startsWith("/health/"))
      throw new Error("Same-origin API only");
    if (this.#demo) {
      if (method !== "GET")
        throw new Error(
          L(
            "العرض الاصطناعي للقراءة فقط؛ لا تُرسل إجراءات للخادم.",
            "Synthetic preview is read-only; actions are never sent to the server.",
          ),
        );
      return this.#demoResponse(path);
    }
    if (this.#featureData && method === "GET" && path.startsWith("/api/v1/workspace/catalog/"))
      path = path.replace("/api/v1/workspace/catalog/", "/api/v1/feature-data/catalog/");
    const epoch = this.#epoch,
      controller = new AbortController();
    this.#controllers.add(controller);
    const headers = {
      Accept: download ? "application/octet-stream" : "application/json",
    };
    if (this.#token) headers.Authorization = "Bearer " + this.#token;
    if (body !== undefined)
      headers["Content-Type"] = raw
        ? "application/octet-stream"
        : "application/json";
    try {
      let response;
      try {
        response = await fetch(path, {
          method,
          headers,
          body:
            body === undefined ? undefined : raw ? body : JSON.stringify(body),
          cache: "no-store",
          credentials: "omit",
          referrerPolicy: "no-referrer",
          signal: controller.signal,
          redirect: "error",
        });
      } catch (error) {
        if (error.name === "AbortError") throw error;
        throw new ApiError(503);
      }
      if (epoch !== this.#epoch)
        throw new DOMException("Stale response", "AbortError");
      if (response.status === 401 && this.#token) {
        this.clear();
        this.onExpiry();
      }
      if (!response.ok) throw new ApiError(response.status);
      let payload;
      try {
        payload = response.status === 204 ? null : download ? await response.blob() : await response.json();
      } catch (error) {
        if (error.name === "AbortError") throw error;
        throw new ApiError(502);
      }
      if (epoch !== this.#epoch) throw new DOMException("Stale response", "AbortError");
      return payload;
    } finally {
      this.#controllers.delete(controller);
    }
  }
  #demoResponse(path) {
    const f = this.#demo,
      u = new URL(path, location.origin),
      p = u.pathname;
    const offset = Number(u.searchParams.get("offset") || 0),
      limit = Number(u.searchParams.get("limit") || 25);
    const page = (items) => ({
      items: items.slice(offset, offset + limit),
      has_more: offset + limit < items.length,
      offset,
      limit,
    });
    if (p === "/api/v1/workspace/context") return structuredClone(f.context);
    if (p === "/health/live" || p === "/health/ready")
      return { status: "synthetic_preview" };
    if (p === "/api/v1/report-explorer/snapshots") return page(f.reports);
    if (/^\/api\/v1\/reports\/snapshots\/[^/]+$/.test(p))
      return f.reports.find((x) => p.endsWith(x.id)) || f.reports[0];
    if (p.endsWith("/entries") && p.includes("/report-explorer/"))
      return { ...page(f.report_entries), total: f.report_entries.length };
    if (p.startsWith("/api/v1/workspace/catalog/"))
      return page(f.catalog[p.split("/").pop()] || []);
    if (p.startsWith("/api/v1/workspace/users/"))
      return f.catalog.users.find((x) => p.endsWith(x.id)) || {};
    if (p.startsWith("/api/v1/workspace/claims/"))
      return f.catalog.claims.find((x) => p.endsWith(x.id)) || {};
    if (p.startsWith("/api/v1/audits/")) return structuredClone(f.audit);
    if (p.startsWith("/api/v1/governance/cases/"))
      return structuredClone(f.case);
    if (p.endsWith("/studio/tasks")) return page(f.tasks);
    if (p.includes("/studio/tasks/"))
      return f.tasks.find((x) => p.endsWith(x.id)) || f.tasks[0];
    if (p.endsWith("/capabilities")) return f.capabilities;
    if (p.endsWith("/runs")) return page([]);
    if (p.endsWith("/manifest"))
      return {
        status: "extracted",
        manifest: { demo: true, total_rows: 12, covered_rows: 12 },
      };
    throw new ApiError(404);
  }
  async download(path, filename) {
    const blob = await this.request(path, { download: true });
    const url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
