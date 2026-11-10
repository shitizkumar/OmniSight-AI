
import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";
const POLL_INTERVAL = 2000;
const MAX_POLLS = 150;

const SCREENSHOTS = [
  "mobile_small.png",
  "mobile.png",
  "tablet.png",
  "desktop.png",
  "verification_mobile_small.png",
  "verification_mobile.png",
  "verification_tablet.png",
  "verification_desktop.png",
];

function formatDate(value) {
  if (!value) return "Not available";
  return new Date(value).toLocaleString();
}

function Status({ value }) {
  const passed = value === "passed" || value === "completed";

  return (
    <span className={`status ${passed ? "success" : "failed"}`}>
      {value || "unknown"}
    </span>
  );
}

function App() {
  const [reports, setReports] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const [websiteUrl, setWebsiteUrl] = useState("");
  const [websiteJob, setWebsiteJob] = useState(null);
  const [websiteData, setWebsiteData] = useState(null);
  const [inspecting, setInspecting] = useState(false);
  const [websiteError, setWebsiteError] = useState("");
  const [pollCount, setPollCount] = useState(0);
  const [repairing, setRepairing] = useState(false);
  const [repairError, setRepairError] = useState("");
  const [repairResult, setRepairResult] = useState(null);

  const loadReports = useCallback(async () => {
    try {
      setError("");

      const response = await fetch(`${API_URL}/api/qa/reports`);

      if (!response.ok) {
        throw new Error("Unable to load QA reports.");
      }

      setReports(await response.json());
    } catch (err) {
      setError(err.message || "Backend connection failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  // Poll the backend while a website inspection is queued or running.
  useEffect(() => {
    const jobId = websiteJob?.job_id;
    const status = websiteJob?.status;

    if (!jobId || !["queued", "running"].includes(status)) return;

    if (pollCount >= MAX_POLLS) {
      setWebsiteError("Inspection timed out. Check the backend logs.");
      setWebsiteJob((current) => ({
        ...current,
        status: "timeout",
      }));
      setInspecting(false);
      return;
    }

    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/qa/runs/${encodeURIComponent(jobId)}`
        );

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.detail || "Unable to retrieve inspection status.");
        }

        const job = result.job || {};

        setWebsiteJob(job);
        setWebsiteData(result);
        setPollCount((count) => count + 1);

        if (["completed", "failed"].includes(job.status)) {
          setInspecting(false);

          if (job.status === "failed") {
            setWebsiteError(job.error || "Website inspection failed.");
          }
        }
      } catch (err) {
        setWebsiteError(err.message || "Unable to check inspection status.");
        setInspecting(false);
      }
    }, POLL_INTERVAL);

    return () => window.clearTimeout(timer);
  }, [websiteJob, pollCount]);

  async function inspectWebsite(event) {
    event.preventDefault();

    const url = websiteUrl.trim();

    if (!url) {
      setWebsiteError("Enter a website URL first.");
      return;
    }

    try {
      setInspecting(true);
      setWebsiteError("");
      setMessage("");
      setWebsiteData(null);
      setWebsiteJob(null);
      setPollCount(0);
      setRepairResult(null);
      setRepairError("");

      const response = await fetch(`${API_URL}/api/qa/inspect`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to start website inspection.");
      }

      setWebsiteJob(result);
      setMessage("Website inspection started.");
    } catch (err) {
      setWebsiteError(err.message || "Unable to start inspection.");
      setInspecting(false);
    }
  }

  async function submitDecision(decision, runId) {
    if (!runId) {
      setMessage("No completed run is available for review.");
      return;
    }

    const confirmed = window.confirm(
      `Are you sure you want to ${decision} this QA run?`
    );

    if (!confirmed) return;

    try {
      setSaving(true);
      setMessage("");

      const response = await fetch(`${API_URL}/api/qa/decision`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          run_id: runId,
          decision,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to save decision.");
      }

      setMessage(`QA decision ${decision} successfully.`);

      if (websiteJob?.job_id && websiteData) {
        const updated = await fetch(
          `${API_URL}/api/qa/runs/${encodeURIComponent(websiteJob.job_id)}`
        );

        if (updated.ok) {
          const updatedData = await updated.json();
          setWebsiteData(updatedData);
          setWebsiteJob(updatedData.job || null);
        }
      } else {
        await loadReports();
      }
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function previewApprovedRepair() {
    if (!runId || !jobId) return;

    try {
      setRepairing(true);
      setRepairError("");
      setRepairResult(null);

      const response = await fetch(`${API_URL}/api/qa/repair`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          run_id: runId,
          viewport_width: 320,
          viewport_height: 720,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to generate repair preview.");
      }

      setRepairResult(result);
    } catch (err) {
      setRepairError(err.message || "Repair preview failed.");
    } finally {
      setRepairing(false);
    }
  }

  if (loading) {
    return <main className="loading">Loading OmniSight QA reports...</main>;
  }

  const isWebsiteRun = Boolean(websiteData);
  const activeData = websiteData?.reports || websiteData || reports || {};

  const browser = activeData.verification || activeData.browser || {};
  const inspection = activeData.inspection || {};
  const recommendations = activeData.recommendations || {};
  const viewports = browser.viewports || {};
  const defects = inspection.defects || [];
  const fixes = recommendations.recommendations || [];
  const decision = activeData.decision || {};
  const hasOverflowDefect = defects.some((defect) =>
    `${defect.issue || ""} ${defect.element || ""} ${defect.evidence || ""}`
      .toLowerCase()
      .includes("overflow")
  );

  const viewportList = Object.entries(viewports);
  const passedCount = viewportList.filter(
    ([, item]) => item.status === "passed"
  ).length;

  const jobId = websiteJob?.job_id;
  const runId = websiteData?.job?.run_id || websiteData?.run_id || browser.run_id;
  const screenshotBase = jobId
    ? `${API_URL}/api/qa/runs/${encodeURIComponent(jobId)}/screenshots`
    : "";
  const canRepair = Boolean(
    runId &&
    jobId &&
    decision.decision === "approved" &&
    hasOverflowDefect
  );
  const repairPreviewBase = jobId
    ? `${API_URL}/api/qa/runs/${encodeURIComponent(jobId)}/repair-preview`
    : "";

  return (
    <main className="dashboard">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">O</div>
          <div>
            <h2>OmniSight</h2>
            <span>AI QUALITY ENGINE</span>
          </div>
        </div>

        <nav>
          <a href="#overview" className="active">Overview</a>
          <a href="#website-inspection">Website inspection</a>
          <a href="#viewports">Viewport tests</a>
          <a href="#screenshots">Screenshots</a>
          <a href="#inspection">UI inspection</a>
          <a href="#recommendations">Recommendations</a>
          <a href="#approval">QA approval</a>
        </nav>

        <div className="sidebar-footer">
          <span className="online-dot" />
          Backend connected
        </div>
      </aside>

      <section className="main-content">
        <header className="topbar">
          <div>
            <span className="eyebrow">QUALITY ASSURANCE / DASHBOARD</span>
            <h1>QA Command Center</h1>
            <p>Monitor automated UI testing and repair decisions.</p>
          </div>

          <button className="refresh-btn" onClick={loadReports}>
            Refresh reports
          </button>
        </header>

        {error && (
          <div className="alert error-alert">
            {error}
            <button onClick={loadReports}>Retry</button>
          </div>
        )}

        {message && <div className="alert">{message}</div>}

        <section id="website-inspection" className="panel website-panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">URL-DRIVEN AUTOMATION</span>
              <h2>Inspect a website</h2>
            </div>
            <Status value={websiteJob?.status || "idle"} />
          </div>

          <form className="url-form" onSubmit={inspectWebsite}>
            <input
              type="url"
              value={websiteUrl}
              onChange={(event) => setWebsiteUrl(event.target.value)}
              placeholder="https://example.com"
              aria-label="Website URL"
              required
            />
            <button
              className="inspect-btn"
              type="submit"
              disabled={inspecting}
            >
              {inspecting ? "Inspecting..." : "Inspect website"}
            </button>
          </form>

          <p className="muted">
            Runs read-only browser capture, UI inspection, repair recommendations
            and responsive verification.
          </p>

          {websiteError && (
            <div className="alert error-alert">{websiteError}</div>
          )}

          {websiteJob && (
            <div className="job-status">
              <div>
                <strong>Inspection job</strong>
                <code>{websiteJob.job_id || "Starting..."}</code>
              </div>
              <div>
                <strong>Website</strong>
                <span>{websiteJob.url || websiteUrl}</span>
              </div>
              <div>
                <strong>Progress</strong>
                <Status value={websiteJob.status} />
              </div>
              {websiteJob.run_id && (
                <div>
                  <strong>Run ID</strong>
                  <code>{websiteJob.run_id}</code>
                </div>
              )}
            </div>
          )}
        </section>

        <section id="overview">
          <div className="section-heading">
            <div>
              <span className="eyebrow">LIVE PROJECT DATA</span>
              <h2>System overview</h2>
            </div>
            <Status value={browser.overall_status} />
          </div>

          <div className="stats-grid">
            <article className="stat-card">
              <span>Viewport tests passed</span>
              <strong>{passedCount}/{viewportList.length}</strong>
              <small>Responsive browser verification</small>
            </article>

            <article className="stat-card">
              <span>Detected defects</span>
              <strong>{inspection.defects_found ?? "N/A"}</strong>
              <small>UI inspection results</small>
            </article>

            <article className="stat-card">
              <span>Recommendations</span>
              <strong>{recommendations.recommendations_count ?? "N/A"}</strong>
              <small>Suggested repair actions</small>
            </article>

            <article className="stat-card">
              <span>AI vision</span>
              <strong className="small-value">
                {inspection.ai_vision_used ? "Enabled" : "Not used"}
              </strong>
              <small>{inspection.inspection_method || "No inspection"}</small>
            </article>
          </div>
        </section>

        <section id="viewports" className="panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">PLAYWRIGHT AUTOMATION</span>
              <h2>Viewport verification</h2>
            </div>
            <span className="muted">{viewportList.length} viewports</span>
          </div>

          {viewportList.length === 0 ? (
            <p className="empty-state">No viewport verification data available.</p>
          ) : (
            <div className="viewport-grid">
              {viewportList.map(([name, item]) => (
                <article className="viewport-card" key={name}>
                  <div className="viewport-top">
                    <h3>{name.replaceAll("_", " ")}</h3>
                    <Status value={item.status} />
                  </div>

                  <strong>
                    {item.dimensions?.width} x {item.dimensions?.height}
                  </strong>

                  <div className="check-list">
                    {Object.entries(item.checks || {}).map(([check, passed]) => (
                      <div className="check-row" key={check}>
                        <span>{check.replaceAll("_", " ")}</span>
                        <span className={passed ? "check-pass" : "check-fail"}>
                          {passed ? "PASS" : "FAIL"}
                        </span>
                      </div>
                    ))}
                  </div>

                  <small className="muted">
                    Browser errors: {item.browser_errors?.length ?? 0}
                  </small>

                  {item.component_boxes &&
                    Object.keys(item.component_boxes).length > 0 && (
                      <details>
                        <summary>Component coordinates</summary>
                        {Object.entries(item.component_boxes).map(
                          ([component, box]) => (
                            <p key={component}>
                              <strong>{component}</strong>: {box.x}, {box.y},
                              {` ${box.width} x ${box.height}`}
                            </p>
                          )
                        )}
                      </details>
                    )}
                </article>
              ))}
            </div>
          )}
        </section>

        {isWebsiteRun && (
          <section id="screenshots" className="panel">
            <div className="section-heading">
              <div>
                <span className="eyebrow">PLAYWRIGHT CAPTURES</span>
                <h2>Website screenshots</h2>
              </div>
              <span className="muted">Capture and verification</span>
            </div>

            <div className="screenshot-grid">
              {SCREENSHOTS.map((filename) => (
                <article className="screenshot-card" key={filename}>
                  <h3>{filename.replaceAll("_", " ").replace(".png", "")}</h3>
                  <a
                    href={`${screenshotBase}/${filename}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <img
                      src={`${screenshotBase}/${filename}`}
                      alt={filename}
                      loading="lazy"
                      onError={(event) => {
                        event.currentTarget.style.display = "none";
                      }}
                    />
                  </a>
                </article>
              ))}
            </div>
          </section>
        )}

        <section id="inspection" className="panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">VISUAL QUALITY ANALYSIS</span>
              <h2>Detected UI defects</h2>
            </div>
            <strong>{defects.length} found</strong>
          </div>

          {defects.length === 0 ? (
            <p className="empty-state">No UI defects detected in this report.</p>
          ) : (
            defects.map((defect, index) => {
              const cropName = `defect_${String(index + 1).padStart(2, "0")}`;
              const crop = browser.defect_crops?.[cropName];
              const cropUrl = jobId
                ? `${API_URL}/api/qa/runs/${encodeURIComponent(jobId)}/defect-crops/${cropName}.png`
                : "";

              return (
                <article className="issue-card" key={index}>
                  <h3>{defect.element}</h3>
                  <p>{defect.issue}</p>
                  <span className="severity">{defect.severity}</span>
                  <p><strong>Evidence:</strong> {defect.evidence || "Not provided"}</p>
                  <p><strong>Suggested fix:</strong> {defect.suggested_fix || "Not provided"}</p>

                  {crop?.status === "created" && cropUrl ? (
                    <div className="defect-crop">
                      <h4>Defect screenshot</h4>
                      <a href={cropUrl} target="_blank" rel="noreferrer">
                        <img
                          src={cropUrl}
                          alt={`Screenshot crop for ${cropName}`}
                          loading="lazy"
                          onError={(event) => {
                            event.currentTarget.style.display = "none";
                          }}
                        />
                      </a>
                    </div>
                  ) : (
                    <p className="muted">
                      Crop unavailable: {crop?.reason || "No screenshot crop generated for this defect."}
                    </p>
                  )}
                </article>
              );
            })
          )}
        </section>

        <section id="recommendations" className="panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">SELF-HEALING ENGINE</span>
              <h2>Repair recommendations</h2>
            </div>
            <strong>{fixes.length} recommendations</strong>
          </div>

          {fixes.length === 0 ? (
            <p className="empty-state">No repair recommendations available.</p>
          ) : (
            fixes.map((fix, index) => (
              <article className="issue-card" key={index}>
                <h3>{fix.element}</h3>
                <p>{fix.issue}</p>
                <p><strong>Action:</strong> {fix.recommended_action}</p>
                <span className="muted">
                  Automatic changes applied: {String(fix.automatic_changes_applied)}
                </span>
              </article>
            ))
          )}
        </section>

        <section id="repair-preview" className="panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">APPROVED URL REPAIR</span>
              <h2>Self-healing preview</h2>
            </div>
            <strong>
              {repairResult?.verification_status || "Preview pending"}
            </strong>
          </div>

          {!hasOverflowDefect ? (
            <p className="empty-state">
              URL repair is unavailable because this run has no detected overflow defect.
            </p>
          ) : decision.decision !== "approved" ? (
            <p className="empty-state">
              QA approval is required before generating a repair preview.
            </p>
          ) : (
            <>
              <p>
                OmniSight AI will generate a targeted CSS patch from the
                detected defect and test it against the captured page at a
                320 x 720 viewport. This creates a temporary browser preview;
                it does not modify the external website or project source files.
              </p>

              <button
                className="approve-btn"
                onClick={previewApprovedRepair}
                disabled={!canRepair || repairing}
              >
                {repairing ? "Generating preview..." : "Generate AI repair preview"}
              </button>
            </>
          )}

          {repairError && (
            <p className="error-message">{repairError}</p>
          )}

          {repairResult && (
            <div className="issue-card">
              <h3>Repair verification: {repairResult.verification_status}</h3>
              <p>
                Horizontal overflow before:{" "}
                {String(repairResult.before?.horizontal_overflow)}
              </p>
              <p>
                Horizontal overflow after:{" "}
                {String(repairResult.after?.horizontal_overflow)}
              </p>
              <p>
                Source modified: {String(repairResult.source_code_modified)}
              </p>
              <p>
                External website modified:{" "}
                {String(repairResult.external_website_modified)}
              </p>

              {repairResult.ai_repair && (
                <div className="issue-card">
                  <h3>AI-generated repair</h3>
                  <p>{repairResult.ai_repair.explanation}</p>
                  <p>
                    Provider: {repairResult.ai_repair.provider} |
                    Model: {repairResult.ai_repair.model}
                  </p>
                  <pre style={{
                    whiteSpace: "pre-wrap",
                    overflowX: "auto",
                    padding: "12px",
                    borderRadius: "8px",
                  }}>
                    {repairResult.ai_repair.generated_css}
                  </pre>
                </div>
              )}

              <div className="screenshot-grid">
                <article className="screenshot-card">
                  <h3>Before repair</h3>
                  <img
                    src={`${repairPreviewBase}/url_repair_before.png`}
                    alt="Website before repair"
                    loading="lazy"
                  />
                </article>
                <article className="screenshot-card">
                  <h3>After repair</h3>
                  <img
                    src={`${repairPreviewBase}/url_repair_after.png`}
                    alt="Website after repair"
                    loading="lazy"
                  />
                </article>
              </div>
            </div>
          )}
        </section>

        <section id="approval" className="panel approval-panel">
          <span className="eyebrow">HUMAN-IN-THE-LOOP</span>
          <h2>QA manager decision</h2>
          <p>
            Review the current browser verification run and record your
            approval or rejection.
          </p>

          <div className="run-details">
            <span>Run ID</span>
            <code>{runId || "No run available"}</code>

            <span>Verified at</span>
            <strong>{formatDate(browser.verified_at)}</strong>

            <span>Current decision</span>
            <strong>{decision.decision || "Pending review"}</strong>
          </div>

          <div className="decision-actions">
            <button
              className="approve-btn"
              disabled={saving || !runId || inspecting}
              onClick={() => submitDecision("approved", runId)}
            >
              Approve
            </button>

            <button
              className="reject-btn"
              disabled={saving || !runId || inspecting}
              onClick={() => submitDecision("rejected", runId)}
            >
              Reject
            </button>
          </div>

          {saving && <p className="muted">Saving decision...</p>}

          <small className="muted">
            Decisions are recorded locally in project artifacts.
            They do not merge or create GitHub pull requests.
          </small>
        </section>

        <footer>
          OmniSight-AI | Multimodal UI Self-Healing & RPA Agent
        </footer>
      </section>
    </main>
  );
}

export default App;
