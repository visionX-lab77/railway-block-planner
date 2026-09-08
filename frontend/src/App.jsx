import { useEffect, useState } from "react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [maintenance, setMaintenance] = useState([]);
  const [blocks, setBlocks] = useState([]);
  const [weeklyPlan, setWeeklyPlan] = useState([]);
  const [monthlyPlan, setMonthlyPlan] = useState([]);

  const [generating, setGenerating] = useState(false);
  const [generatingMonthly, setGeneratingMonthly] = useState(false);

  const [department, setDepartment] = useState("TMS");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");

  const loadDashboardData = async () => {
  try {
    const responses = await Promise.all([
      fetch(`${API}/maintenance`),
      fetch(`${API}/blocks`),
      fetch(`${API}/weekly-plan`),
      fetch(`${API}/monthly-plan`)
    ]);

    const [
      maintenanceData,
      blocksData,
      weeklyData,
      monthlyData
    ] = await Promise.all(
      responses.map((response) => response.json())
    );

    setMaintenance(
      Array.isArray(maintenanceData)
        ? maintenanceData
        : maintenanceData.data || []
    );

    setBlocks(
      Array.isArray(blocksData)
        ? blocksData
        : blocksData.data || []
    );

    setWeeklyPlan(
      Array.isArray(weeklyData)
        ? weeklyData
        : weeklyData.data || []
    );

    setMonthlyPlan(
      Array.isArray(monthlyData)
        ? monthlyData
        : monthlyData.data || []
    );

    console.log("Maintenance:", maintenanceData);
    console.log("Blocks:", blocksData);
    console.log("Weekly:", weeklyData);
    console.log("Monthly:", monthlyData);

  } catch (error) {
    console.error("Dashboard data loading failed:", error);
  }
};
  useEffect(() => {
    loadDashboardData();
  }, []);

  const departmentData = [
    {
      department: "TMS",
      tasks: maintenance.filter((x) => x.department === "TMS").length
    },
    {
      department: "SMMS",
      tasks: maintenance.filter((x) => x.department === "SMMS").length
    },
    {
      department: "TDMS",
      tasks: maintenance.filter((x) => x.department === "TDMS").length
    }
  ];

  const criticalTasks = maintenance.filter(
    (x) => x.ai_priority === "CRITICAL"
  ).length;

  const highTasks = maintenance.filter(
    (x) => x.ai_priority === "HIGH"
  ).length;

  const usedBlocks = new Set(monthlyPlan.map((x) => x.block_id)).size;

  const blockUtilization =
    blocks.length > 0
      ? Math.round((usedBlocks / blocks.length) * 100)
      : 0;

  const plannedDepartmentData = [
    {
      department: "TMS",
      tasks: monthlyPlan.filter((x) => x.department === "TMS").length
    },
    {
      department: "SMMS",
      tasks: monthlyPlan.filter((x) => x.department === "SMMS").length
    },
    {
      department: "TDMS",
      tasks: monthlyPlan.filter((x) => x.department === "TDMS").length
    }
  ];

  const handleFileChange = (event) => {
    const file = event.target.files[0];

    setUploadMessage("");
    setUploadError("");

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const allowedExtensions = [".csv", ".xlsx", ".xls"];
    const fileName = file.name.toLowerCase();

    const validFile = allowedExtensions.some((extension) =>
      fileName.endsWith(extension)
    );

    if (!validFile) {
      setSelectedFile(null);
      setUploadError("Please select a CSV or Excel file.");
      return;
    }

    setSelectedFile(file);
  };

  const uploadMaintenanceData = async () => {
    if (!selectedFile) {
      setUploadError("Please select a maintenance data file first.");
      return;
    }

    setUploading(true);
    setUploadMessage("");
    setUploadError("");

    try {
      const formData = new FormData();
      formData.append("department", department);
      formData.append("file", selectedFile);

      const response = await fetch(`${API}/upload-maintenance-data`, {
        method: "POST",
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setUploadMessage(
        data.message ||
          `${department} maintenance data uploaded successfully.`
      );

      setSelectedFile(null);

      const fileInput = document.getElementById("maintenance-file");
      if (fileInput) {
        fileInput.value = "";
      }

      await loadDashboardData();
    } catch (error) {
      console.error("Maintenance upload failed:", error);
      setUploadError(
        error.message || "Upload failed. Please check backend."
      );
    } finally {
      setUploading(false);
    }
  };

  const generatePlan = async () => {
    setGenerating(true);

    try {
      const response = await fetch(`${API}/generate-plan`, {
        method: "POST"
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Weekly plan generation failed."
        );
      }

      setWeeklyPlan(data.data || []);
      await loadDashboardData();
    } catch (error) {
      console.error("Plan generation failed:", error);
      alert("Plan generation failed. Please check backend.");
    } finally {
      setGenerating(false);
    }
  };

  const generateMonthlyPlan = async () => {
    setGeneratingMonthly(true);

    try {
      const response = await fetch(`${API}/generate-monthly-plan`, {
        method: "POST"
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Monthly plan generation failed."
        );
      }

      setMonthlyPlan(data.data || []);
      await loadDashboardData();
    } catch (error) {
      console.error("Monthly plan generation failed:", error);
      alert(
        "Monthly plan generation failed. Please check backend."
      );
    } finally {
      setGeneratingMonthly(false);
    }
  };

  const chartTooltipStyle = {
    borderRadius: "10px",
    border: "1px solid #e4e7ec",
    boxShadow: "0 8px 24px rgba(16, 24, 40, 0.08)"
  };

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>🚆 Railway AI Block Planner</h1>
          <p>AI-Powered Automatic Block Planning System</p>
        </div>

        <div className="status">
          <span></span>
          System Online
        </div>
      </header>

      <main className="container">
        <section className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-icon">🛠️</div>
            <div>
              <p>Total Maintenance</p>
              <h2>{maintenance.length}</h2>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-icon">🚧</div>
            <div>
              <p>Available Blocks</p>
              <h2>{blocks.length}</h2>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-icon">🔴</div>
            <div>
              <p>Critical Tasks</p>
              <h2>{criticalTasks}</h2>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-icon">📅</div>
            <div>
              <p>Weekly Planned</p>
              <h2>{weeklyPlan.length}</h2>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-icon">📆</div>
            <div>
              <p>Monthly Planned</p>
              <h2>{monthlyPlan.length}</h2>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-icon">📈</div>
            <div>
              <p>Block Utilization</p>
              <h2>{blockUtilization}%</h2>
            </div>
          </div>
        </section>

        <section className="card upload-card">
          <div className="card-header">
            <div>
              <h2>📤 Upload Maintenance Data</h2>
              <p>Upload TMS, SMMS or TDMS maintenance records</p>
            </div>
          </div>

          <div className="upload-row">
            <div className="upload-field">
              <label>Department</label>
              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              >
                <option value="TMS">TMS</option>
                <option value="SMMS">SMMS</option>
                <option value="TDMS">TDMS</option>
              </select>
            </div>

            <div className="upload-field">
              <label>Maintenance File</label>
              <input
                id="maintenance-file"
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileChange}
              />
            </div>

            <button
              className="generate-btn"
              onClick={uploadMaintenanceData}
              disabled={uploading || !selectedFile}
            >
              {uploading ? "⏳ Uploading..." : "📤 Upload Data"}
            </button>
          </div>

          {selectedFile && (
            <p className="upload-file-name">
              📄 Selected file: <strong>{selectedFile.name}</strong>
            </p>
          )}

          {uploadMessage && (
            <div className="upload-success">✅ {uploadMessage}</div>
          )}

          {uploadError && (
            <div className="upload-error">❌ {uploadError}</div>
          )}

          <div className="upload-info">
            <strong>ℹ️ How it works:</strong>
            <span>
              Upload maintenance data → Database → AI Priority → Generate
              Plan
            </span>
          </div>
        </section>

        <section className="card chart-card">
          <div className="card-header">
            <div>
              <h2>📊 Planned Tasks by Department</h2>
              <p>AI optimized tasks by department</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={plannedDepartmentData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="department"
                tick={{ fill: "#344054", fontSize: 14, fontWeight: 600 }}
              />
              <YAxis tick={{ fill: "#344054", fontSize: 13 }} />
              <Tooltip contentStyle={chartTooltipStyle} />
              <Bar dataKey="tasks" name="Planned Tasks" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="dashboard-grid">
          <div className="card chart-card">
            <div className="card-header">
              <div>
                <h2>📊 Department Overview</h2>
                <p>Maintenance records by department</p>
              </div>
            </div>

            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={departmentData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="department"
                  tick={{ fill: "#344054", fontSize: 14, fontWeight: 600 }}
                />
                <YAxis tick={{ fill: "#344054", fontSize: 13 }} />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Bar dataKey="tasks" name="Tasks" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card ai-card">
            <h2>🤖 AI Planning Status</h2>

            <div className="ai-status-item">
              <span>Data Integration</span>
              <strong>✓ Complete</strong>
            </div>

            <div className="ai-status-item">
              <span>AI Priority Engine</span>
              <strong>✓ Active</strong>
            </div>

            <div className="ai-status-item">
              <span>Train Conflict Check</span>
              <strong>✓ Active</strong>
            </div>

            <div className="ai-status-item">
              <span>OR-Tools Optimization</span>
              <strong>✓ Active</strong>
            </div>

            <div className="ai-status-item">
              <span>Weekly Planning</span>
              <strong>✓ Generated</strong>
            </div>

            <div className="priority-summary">
              <div>
                <span>Critical</span>
                <b>{criticalTasks}</b>
              </div>

              <div>
                <span>High</span>
                <b>{highTasks}</b>
              </div>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h2>📅 Weekly Block Plan</h2>
              <p>AI optimized maintenance schedule</p>
            </div>

            <div className="plan-actions">
              <div className="plan-count">
                {weeklyPlan.length} Tasks Planned
              </div>

              <button
                className="generate-btn"
                onClick={generatePlan}
                disabled={generating}
              >
                {generating
                  ? "⏳ Generating..."
                  : "⚡ Generate Optimized Plan"}
              </button>
            </div>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Block</th>
                  <th>Time</th>
                  <th>Record ID</th>
                  <th>Department</th>
                  <th>Duration</th>
                  <th>Priority</th>
                </tr>
              </thead>

              <tbody>
                {weeklyPlan.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: "center", padding: "30px" }}>
                      No weekly plan available
                    </td>
                  </tr>
                ) : (
                  weeklyPlan.map((task, index) => (
                    <tr key={index}>
                      <td>{task.block_date}</td>
                      <td><strong>{task.block_id}</strong></td>
                      <td>
                        {task.start_time} - {task.end_time}
                      </td>
                      <td>{task.record_id}</td>
                      <td>
                        <span className="department-badge">
                          {task.department}
                        </span>
                      </td>
                      <td>{task.maintenance_duration_minutes} min</td>
                      <td>
                        <span
                          className={`priority-badge ${
                            task.ai_priority === "CRITICAL"
                              ? "critical"
                              : "high"
                          }`}
                        >
                          {task.ai_priority}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h2>📆 Monthly Block Plan</h2>
              <p>AI optimized monthly maintenance schedule</p>
            </div>

            <div className="plan-actions">
              <div className="plan-count">
                {monthlyPlan.length} Tasks Planned
              </div>

              <button
                className="generate-btn"
                onClick={generateMonthlyPlan}
                disabled={generatingMonthly}
              >
                {generatingMonthly
                  ? "⏳ Generating..."
                  : "📆 Generate Monthly Plan"}
              </button>
            </div>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Block</th>
                  <th>Time</th>
                  <th>Asset</th>
                  <th>Department</th>
                  <th>Duration</th>
                  <th>Priority</th>
                </tr>
              </thead>

              <tbody>
                {monthlyPlan.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: "center", padding: "30px" }}>
                      No monthly plan available
                    </td>
                  </tr>
                ) : (
                  monthlyPlan.map((plan, index) => (
                    <tr key={index}>
                      <td>{plan.block_date}</td>
                      <td><strong>{plan.block_id}</strong></td>
                      <td>
                        {plan.start_time} - {plan.end_time}
                      </td>
                      <td>{plan.asset_id}</td>
                      <td>
                        <span className="department-badge">
                          {plan.department}
                        </span>
                      </td>
                      <td>{plan.maintenance_duration_minutes} min</td>
                      <td>
                        <span
                          className={`priority-badge ${
                            plan.ai_priority === "CRITICAL"
                              ? "critical"
                              : "high"
                          }`}
                        >
                          {plan.ai_priority}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="summary-grid">
          <div className="summary-card">
            <span>📊</span>
            <div>
              <h3>{maintenance.length}</h3>
              <p>Integrated Records</p>
            </div>
          </div>

          <div className="summary-card">
            <span>🚆</span>
            <div>
              <h3>10</h3>
              <p>Train Services</p>
            </div>
          </div>

          <div className="summary-card">
            <span>⚙️</span>
            <div>
              <h3>OR-Tools</h3>
              <p>Optimization Engine</p>
            </div>
          </div>

          <div className="summary-card">
            <span>🧠</span>
            <div>
              <h3>AI</h3>
              <p>Priority Prediction</p>
            </div>
          </div>
        </section>
      </main>

      <footer>
        Railway AI Block Planner • Smart Maintenance Scheduling System
      </footer>
    </div>
  );
}

export default App;
