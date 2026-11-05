
import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function formatDate(value) {
  if (!value) return "Not available";

  return new Date(value).toLocaleString();
}

function Status({ value }) {
  const passed = value === "passed";

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

  async function submitDecision(decision) {
    const runId = reports?.browser?.run_id;

    if (!runId) {
      setMessage("No browser run is available for review.");
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
      await loadReports();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <main className="loading">Loading OmniSight QA reports...</main>;
  }

  const browser = reports?.browser || {};
  const inspection = reports?.inspection || {};
  const recommendations = reports?.recommendations || {};
  const viewports = browser.viewports || {};
  const defects = inspection.defects || [];
  const fixes = recommendations.recommendations || [];
  const decision = reports?.decision || {};

  const viewportList = Object.entries(viewports);
  const passedCount = viewportList.filter(
    ([, item]) => item.status === "passed"
  ).length;

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
          <a href="#overview" className="active">▦ Overview</a>
          <a href="#viewports">◫ Viewport tests</a>
          <a href="#inspection">⌕ UI inspection</a>
          <a href="#recommendations">⚙ Recommendations</a>
          <a href="#approval">✓ QA approval</a>
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
            ↻ Refresh reports
          </button>
        </header>

        {error && (
          <div className="alert error-alert">
            {error}
            <button onClick={loadReports}>Retry</button>
          </div>
        )}

        {message && <div className="alert">{message}</div>}

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
              <strong>{inspection.defects_found ?? "—"}</strong>
              <small>UI inspection results</small>
            </article>

            <article className="stat-card">
              <span>Recommendations</span>
              <strong>{recommendations.recommendations_count ?? "—"}</strong>
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

          <div className="viewport-grid">
            {viewportList.map(([name, item]) => (
              <article className="viewport-card" key={name}>
                <div className="viewport-top">
                  <h3>{name.replace("_", " ")}</h3>
                  <Status value={item.status} />
                </div>

                <strong>
                  {item.dimensions?.width} × {item.dimensions?.height}
                </strong>

                <div className="check-list">
                  {Object.entries(item.checks || {}).map(([check, passed]) => (
                    <div className="check-row" key={check}>
                      <span>{check.replaceAll("_", " ")}</span>
                      <span className={passed ? "check-pass" : "check-fail"}>
                        {passed ? "✓" : "✕"}
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
                            {` ${box.width} × ${box.height}`}
                          </p>
                        )
                      )}
                    </details>
                  )}
              </article>
            ))}
          </div>
        </section>

        <section id="inspection" className="panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">VISUAL QUALITY ANALYSIS</span>
              <h2>Detected UI defects</h2>
            </div>
            <strong>{defects.length} found</strong>
          </div>

          {defects.length === 0 ? (
            <p className="empty-state">✓ No UI defects detected in this report.</p>
          ) : (
            defects.map((defect, index) => (
              <article className="issue-card" key={index}>
                <h3>{defect.element}</h3>
                <p>{defect.issue}</p>
                <span className="severity">{defect.severity}</span>
                <p><strong>Evidence:</strong> {defect.evidence}</p>
                <p><strong>Suggested fix:</strong> {defect.suggested_fix}</p>
              </article>
            ))
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

        <section id="approval" className="panel approval-panel">
          <span className="eyebrow">HUMAN-IN-THE-LOOP</span>
          <h2>QA manager decision</h2>
          <p>
            Review the current browser verification run and record your
            approval or rejection.
          </p>

          <div className="run-details">
            <span>Run ID</span>
            <code>{browser.run_id || "No run available"}</code>

            <span>Verified at</span>
            <strong>{formatDate(browser.verified_at)}</strong>

            <span>Current decision</span>
            <strong>{decision.decision || "Pending review"}</strong>
          </div>

          <div className="decision-actions">
            <button
              className="approve-btn"
              disabled={saving || !browser.run_id}
              onClick={() => submitDecision("approved")}
            >
              ✓ Approve
            </button>

            <button
              className="reject-btn"
              disabled={saving || !browser.run_id}
              onClick={() => submitDecision("rejected")}
            >
              ✕ Reject
            </button>
          </div>

          {saving && <p className="muted">Saving decision...</p>}

          <small className="muted">
            Decisions are recorded locally in the project artifacts.
            They do not merge or create GitHub pull requests.
          </small>
        </section>

        <footer>
          OmniSight-AI · Multimodal UI Self-Healing & RPA Agent
        </footer>
      </section>
    </main>
  );
}

export default App;
