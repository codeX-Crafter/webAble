import React, { useCallback, useEffect, useRef, useState } from "react";
import { Header, AuditForm, AuditLoading } from "./components/AuditForm";
import ResultsDashboard from "./components/ResultsDashboard";
import ScanProgress from "./components/ScanProgress";
import { buildRequest, getOrCreateVisualBaseline } from "./utils";
import { createAuditJob } from "./api.mjs";

const SCAN_STORAGE_KEY = "webable.activeScan";
function readSavedScan() {
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(SCAN_STORAGE_KEY) || "null");
    return saved && typeof saved === "object" ? saved : null;
  } catch {
    return null;
  }
}

function saveScan(scan) {
  try {
    window.sessionStorage.setItem(SCAN_STORAGE_KEY, JSON.stringify(scan));
    return true;
  } catch {
    return false;
  }
}

function routeId(path, route) {
  const match = path.match(new RegExp(`^/${route}/([^/]+)$`));
  return match ? decodeURIComponent(match[1]) : "";
}
function newScanId() {
  return window.crypto?.randomUUID?.() ||
    `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const empty = () => ({
  url: "",
  aiOptIn: false,
});
function withoutOwnerContext(payload) {
  const request = { ...payload };
  delete request.accessibility_context;
  return request;
}
export default function App() {
  const [path, setPath] = useState(window.location.pathname),
    [job, setJob] = useState(null);
  const [form, setForm] = useState(empty),
    [loading, setLoading] = useState(false),
    [response, setResponse] = useState(null),
    [error, setError] = useState(""),
    [visualBaseline, setVisualBaseline] = useState(null),
    [currentScanId, setCurrentScanId] = useState(""),
    [baselinePersisted, setBaselinePersisted] = useState(true);
  const pending = useRef(false);
  const navigate = useCallback((nextPath, replace = false) => {
    window.history[replace ? "replaceState" : "pushState"]({}, "", nextPath);
    setPath(nextPath);
  }, []);
  const showReport = useCallback((result, scan) => {
    const savedScan = { ...scan, result };
    const saved = saveScan(savedScan);
    const scanId = scan.scanId || scan.jobId;
    const savedBaseline = getOrCreateVisualBaseline(result, scanId);
    setJob(savedScan);
    setResponse(result);
    setVisualBaseline(savedBaseline.baseline);
    setCurrentScanId(scanId);
    setBaselinePersisted(savedBaseline.persisted);
    setError(
      saved
        ? ""
        : "The report is available, but this browser could not save the scan for refresh recovery.",
    );
    navigate(`/report/${encodeURIComponent(scanId)}`);
  }, [navigate]);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  useEffect(() => {
    const scanId = routeId(path, "scan") || routeId(path, "report");
    if (!scanId) return;
    const saved = readSavedScan();
    if (!saved || (saved.scanId || saved.jobId) !== scanId || !saved.payload) {
      setError("This scan is no longer available in this browser session. Start a new audit.");
      setJob(null);
      setResponse(null);
      return;
    }
    setJob(saved);
    if (routeId(path, "report")) {
      if (saved.result) {
        const baseline = getOrCreateVisualBaseline(saved.result, saved.scanId || saved.jobId);
        setResponse(saved.result);
        setVisualBaseline(baseline.baseline);
        setCurrentScanId(saved.scanId || saved.jobId);
        setBaselinePersisted(baseline.persisted);
      } else {
        navigate(`/scan/${encodeURIComponent(saved.scanId || saved.jobId)}`, true);
      }
    }
  }, [path, navigate]);
  async function startAudit(payload) {
    if (pending.current) return;
    pending.current = true;
    setLoading(true);
    setError("");
    try {
      const submission = await createAuditJob(payload);
      const scan = {
        jobId: submission.job_id,
        scanId: newScanId(),
        payload,
        startedAt: Date.now(),
        result: null,
      };
      const saved = saveScan(scan);
      setJob(scan);
      setResponse(null);
      setError(saved ? "" : "This scan is running, but refresh recovery is unavailable because browser session storage could not be written.");
      navigate(`/scan/${encodeURIComponent(scan.scanId)}`);
    } catch (e) {
      setError(e.message || "The audit request failed.");
    } finally {
      pending.current = false;
      setLoading(false);
    }
  }
  function submit(event) {
    event?.preventDefault();
    if (pending.current) return;
    void startAudit(buildRequest(form));
  }
  const onScanComplete = useCallback(
    (result) => {
      if (job) showReport(result, job);
    },
    [job, showReport],
  );
  const retryScan = useCallback(() => {
    if (job?.payload) void startAudit(withoutOwnerContext(job.payload));
  }, [job]);
  function reset() {
    setForm(empty());
    setResponse(null);
    setVisualBaseline(null);
    setCurrentScanId("");
    setBaselinePersisted(true);
    setError("");
    setJob(null);
    navigate("/");
    document.getElementById("audit-url")?.focus();
  }
  const isScanning = Boolean(routeId(path, "scan") && job && !response);
  return (
    <>
      <a className="skip-link" href={isScanning ? "#scan-title" : "#audit-url"}>
        Skip to audit
      </a>
      <Header
        onNew={reset}
        hasResults={Boolean(response && !loading)}
        isLanding={!isScanning && !response}
      />
      <main className={isScanning ? "scan-page" : response ? "has-results" : "landing"}>
        {!isScanning && (
        <section className="intro">
          <p>
            WEBABLE AUDIT · CONTEXT-AWARE ACCESSIBILITY ENGINE · WCAG 2.2 AAA
          </p>
          <h1>
            <span className="hero-find-line">Find what’s broken.</span>
            <br />
            <span className="hero-fix-line">Know what to fix.</span>
          </h1>
          <p className="hero-line">
            Audit accessibility barriers, responsive layout collisions, and
            functional reliability with real browser evidence. Start with any
            public URL. No account or setup required.
          </p>
        </section>
        )}
        <AuditForm
          form={form}
          setForm={setForm}
          loading={loading}
          response={response}
          onSubmit={submit}
          hidden={isScanning}
          isLanding={!isScanning && !response}
        />
        {!response && !isScanning && (
          <div className="landing-story">
            <section id="products" className="product-section" aria-label="WebAble products">
              <h2 className="product-section-title">
                From automated discovery to verifiable remediation
              </h2>
              <div className="product-intro">
                <article>
                  <div className="product-card-heading">
                    <p className="eyebrow">WEBABLE AUDIT</p>
                    <span className="product-chip success">Continuous Capture</span>
                  </div>
                  <h2>Discover what’s broken.</h2>
                  <p>
                    Capture desktop, tablet, and mobile views simultaneously.
                    Uncover accessibility barriers, layout overflow clipping,
                    touch-target gaps, and DOM structure issues with
                    high-fidelity browser screenshots.
                  </p>
                  <div className="product-example">
                    <div className="example-title">
                      <span>Rule: color-contrast</span>
                      <span className="example-status danger">Failed</span>
                    </div>
                    <div className="example-selector">
                      Selector: nav &gt; a.cta-btn
                    </div>
                    <div className="example-contrast">
                      <span className="contrast-swatch" />
                      Foreground #A29D93 on #FAF7F2 (2.4:1)
                    </div>
                  </div>
                  <div className="product-card-footer">
                    <span>Multi-viewport snapshotting</span>
                    <strong>axe-core v4.10</strong>
                  </div>
                </article>
                <article>
                  <div className="product-card-heading">
                    <p className="eyebrow">WEBABLE AGENT</p>
                    <span className="product-chip warning">Automated Remediation</span>
                  </div>
                  <h2>Understand and fix why.</h2>
                  <p>
                    Receive plain-language remediation instructions tailored
                    to your exact HTML/CSS stack. Codebase connection and
                    advisory code diffs eliminate hours of trial-and-error
                    guesswork.
                  </p>
                  <div className="product-example">
                    <div className="example-title">
                      <span>Remediation Suggestion</span>
                      <span className="example-status positive">Ready</span>
                    </div>
                    <code className="diff-line removed">
                      - &lt;button class="text-stone-400"&gt;
                    </code>
                    <code className="diff-line added">
                      + &lt;button class="text-stone-900" aria-label="Submit"&gt;
                    </code>
                  </div>
                  <div className="product-card-footer">
                    <span>Advisory insights &amp; code patches</span>
                    <strong>WCAG Guidance</strong>
                  </div>
                </article>
              </div>
            </section>
            <section id="how-it-works" className="workflow-intro">
              <h2>How WebAble verifies conformance in production</h2>
              <p>
                A deterministic four-phase loop that turns ambiguous design
                reviews into actionable engineering tasks.
              </p>
              <div className="workflow-steps">
                <article>
                  <div className="workflow-card-heading">
                    <span className="workflow-step-number">01</span>
                    <span className="workflow-phase">PHASE 01</span>
                  </div>
                  <h3>Audit</h3>
                  <p>
                    Automate headless Chromium sessions across 3 synchronized
                    viewports. Collect live DOM trees, computed styles, and
                    accessibility trees.
                  </p>
                  <div className="workflow-step-footer">
                    <span>Execution</span>
                    <strong>Deterministic crawl</strong>
                  </div>
                </article>
                <article>
                  <div className="workflow-card-heading">
                    <span className="workflow-step-number">02</span>
                    <span className="workflow-phase">PHASE 02</span>
                  </div>
                  <h3>Understand</h3>
                  <p>
                    Group detected barriers by component and severity. Inspect
                    exact selector paths, contrast ratios, and WCAG criteria
                    failure rationales.
                  </p>
                  <div className="workflow-step-footer">
                    <span>Diagnostics</span>
                    <strong>Context grouping</strong>
                  </div>
                </article>
                <article>
                  <div className="workflow-card-heading">
                    <span className="workflow-step-number">03</span>
                    <span className="workflow-phase">PHASE 03</span>
                  </div>
                  <h3>Fix</h3>
                  <p>
                    Apply precise remediation snippets directly to your
                    codebase. Correct touch target dimensions, ARIA semantics,
                    and contrast tokens.
                  </p>
                  <div className="workflow-step-footer">
                    <span>Remediation</span>
                    <strong>Direct codebase patch</strong>
                  </div>
                </article>
                <article>
                  <div className="workflow-card-heading">
                    <span className="workflow-step-number">04</span>
                    <span className="workflow-phase">PHASE 04</span>
                  </div>
                  <h3>Verify</h3>
                  <p>
                    Trigger automated re-scan against your baseline. Confirm
                    all barriers have cleared and certify WCAG 2.2 AA
                    conformance without regressions.
                  </p>
                  <div className="workflow-step-footer">
                    <span>Certification</span>
                    <strong>Proof of conformance</strong>
                  </div>
                </article>
              </div>
            </section>
          </div>
        )}
        {error && (
          <p id="form-error" className="error-message" role="alert">
            {error}
          </p>
        )}
        {loading && <AuditLoading url={form.url} />}
        {isScanning && (
          <ScanProgress
            job={job}
            onComplete={onScanComplete}
            onRetry={retryScan}
            onNew={reset}
          />
        )}
        {response && !loading && (
          <ResultsDashboard
            response={response}
            visualBaseline={visualBaseline}
            currentScanId={currentScanId}
            baselinePersisted={baselinePersisted}
            onAgain={(aiAssistanceOptIn) =>
              void startAudit({
                ...withoutOwnerContext(job?.payload || buildRequest(form)),
                ai_assistance_opt_in: aiAssistanceOptIn,
              })
            }
            onNew={reset}
          />
        )}
        <footer>
          WebAble · Evidence for better decisions. Human review for conformance.
        </footer>
      </main>
    </>
  );
}
