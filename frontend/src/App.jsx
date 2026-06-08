import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  TrendingUp, 
  UserCheck, 
  FileText, 
  Activity, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  DollarSign, 
  Clock, 
  Terminal, 
  ChevronRight, 
  ExternalLink,
  Info,
  Search,
  Filter,
  Lock,
  LogOut,
  ChevronDown,
  Check,
  Briefcase,
  BarChart2,
  BookOpen,
  AlertCircle,
  RefreshCw,
  Eye,
  Sliders,
  Award
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  BarChart, 
  Bar, 
  Legend, 
  PieChart, 
  Pie, 
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';

// --- FALLBACK MOCK DATABASE FOR SIMULATION & DEMO EFFICIENCY ---
const MOCK_AUM_DATA = [
  { month: 'Jan', AUM: 42000000 },
  { month: 'Feb', AUM: 42500000 },
  { month: 'Mar', AUM: 43100000 },
  { month: 'Apr', AUM: 43800000 },
  { month: 'May', AUM: 44200000 },
  { month: 'Jun', AUM: 45000000 }
];

const MOCK_DRIFT_DIST = [
  { range: '< 2%', count: 3200 },
  { range: '2% - 5%', count: 1250 },
  { range: '> 5%', count: 550 }
];

const MOCK_AUDIT_TRAIL = [
  {
    id: "aud-001",
    portfolio_id: "p-uuid-00042",
    account_number: "WP-000042",
    client_name: "Sarah Jenkins",
    event_type: "OrderExecution",
    details: "Rebalance orders successfully executed at custodian. Approved by manager@wealthpilot.ai.",
    timestamp: "2026-06-08T14:22:15Z",
    state_before: JSON.stringify({ cash: 45000.0, holdings: { SPY: 150, AGG: 400, GLD: 50 } }),
    state_after: JSON.stringify({ cash: 12000.0, holdings: { SPY: 210, AGG: 350, GLD: 65 } })
  },
  {
    id: "aud-002",
    portfolio_id: "p-uuid-00109",
    account_number: "WP-000109",
    client_name: "Marcus Aurelius Group",
    event_type: "OrderApproval",
    details: "Rebalance order rejected by manager. Reason: Overridden due to client-requested tax-deferral.",
    timestamp: "2026-06-08T11:05:42Z",
    state_before: JSON.stringify({ cash: 85000.0, holdings: { SPY: 500, BIL: 120 } }),
    state_after: JSON.stringify({ cash: 85000.0, holdings: { SPY: 500, BIL: 120 } })
  },
  {
    id: "aud-003",
    portfolio_id: "p-uuid-00251",
    account_number: "WP-000251",
    client_name: "Eleanor Vance",
    event_type: "ComplianceFailure",
    details: "Compliance warning triggered: Wash sale window risk on QQQ proxy buy mapping.",
    timestamp: "2026-06-07T16:40:00Z",
    state_before: null,
    state_after: null
  },
  {
    id: "aud-004",
    portfolio_id: "p-uuid-00812",
    account_number: "WP-000812",
    client_name: "David Davidson",
    event_type: "AgentRun",
    details: "Agent assessment council completed. Rebalancing recommended: drift index 8.42%.",
    timestamp: "2026-06-07T09:12:00Z",
    state_before: null,
    state_after: null
  }
];

const MOCK_COMPLIANCE_RULES = [
  { id: 1, rule: "SEBI Single Asset Exposure Ceiling", desc: "No holding besides CASH/BIL should exceed 25% of total portfolio value.", status: "PASS", limit: "25.00%", actual: "21.40%" },
  { id: 2, rule: "SEBI Sector Allocation Limit", desc: "Aggregate concentration in any single sector must remain under 25%.", status: "PASS", limit: "25.00%", actual: "18.50%" },
  { id: 3, rule: "Risk Suitability Checks", desc: "Portfolio category must align with client documented risk tolerance profile.", status: "PASS", limit: "Match Profile", actual: "Balanced / Moderate" },
  { id: 4, rule: "Wash Sale Wash Window Mitigation", desc: "Flag tax-loss sales of assets with purchase of similar assets within 30 days.", status: "WARNING", limit: "30-day block", actual: "3 lot warning flags" }
];

const MOCK_XAI_REPORTS = {
  shap_waterfall: [
    { attribute: "Asset Class Drift Index", impact: 0.65, color: "#00f2fe" },
    { attribute: "Tax Loss Harvesting Savings", impact: 0.38, color: "#10b981" },
    { attribute: "Cash Flow Deviation", impact: 0.12, color: "#0072ff" },
    { attribute: "Market Index Volatility (VIX)", impact: 0.08, color: "#8a2be2" },
    { attribute: "Trading Commission Overhead", impact: -0.15, color: "#ef4444" }
  ],
  client_explanation: "Your portfolio has drifted from its target Balanced allocation because your S&P 500 ETF (SPY) grew substantially while bonds lost value. The AI has recommended selling $28,000 worth of SPY to purchase corporate bonds. By doing so, we restore your target risk profile, locking in gains. Furthermore, by using HIFO (Highest-In, First-Out) matching, we are harvesting $3,450 in tax losses, which reduces your tax liability this quarter.",
  advisor_explanation: "Portfolio drift has triggered on SPY relative allocation (+7.4% absolute weight drift) exceeding the 5% system threshold. Recommended trades involve liquidating 54 shares of SPY and buying 284 shares of AGG. Expected tracking error reduction: 42 bps. Estimated transaction cost: $12.50, representing an immaterial drag of 0.03% total AUM. HIFO tax harvesting yields $3,450 in realized capital losses to shield STCG elsewhere.",
  compliance_explanation: "Rebalancing proposals pass all pre-trade SEBI guidelines. Post-rebalance projections: SPY exposure will drop to 45.0% (target), well below the 25% single-security concentration ceiling (note: SPY as diversified ETF is exempt, but passes). Tech sector exposure is projected at 12.4%. Sells are mapped to AGG, which maintains clean separation from any restricted asset ticker lists. No Wash Sale overlap was identified on any executed proxies."
};

const AGENT_MOCK_LOGS = [
  "[Orchestrator] Initiating automated drift evaluation council.",
  "[Portfolio Monitor] Scanning account WP-000042. Calculated drift index: 7.82%. Status: Drifted.",
  "[Market Analyst] Fetching latest market feeds. SPY price: $515.20, QQQ: $438.50, AGG: $98.40.",
  "[Risk Assessor] Rebalancing required. Target Balanced (SPY 45%, QQQ 10%, AGG 30%, BIL 10%, GLD 5%).",
  "[Tax Optimizer] Commencing HIFO tax lot matching. Found 3 tax lots of SPY with cost basis > $530.00.",
  "[Tax Optimizer] Strategy: Tax loss harvesting. Estimated STCG savings: $3,450.00.",
  "[Compliance Auditor] Running validation. Rule checks: Concentration (PASS), Restricted List (PASS), Sector limits (PASS).",
  "[Explanation Agent] Generating SHAP attributions. Primary trigger: Drift Magnitude (+0.65), Tax Savings (+0.38).",
  "[Orchestrator] Proposal generated successfully. Dispatched to Human-in-the-Loop Approval Queue."
];

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  
  // App States
  const [metrics, setMetrics] = useState({
    total_portfolios: 5000,
    total_aum: 45000000,
    average_drift: 0.042,
    drifted_count: 550,
    pending_approvals: 3,
    tax_savings_harvested: 124500.0
  });
  
  const [portfolios, setPortfolios] = useState([]);
  const [portfolioPage, setPortfolioPage] = useState(1);
  const [portfolioTotal, setPortfolioTotal] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRisk, setFilterRisk] = useState('');
  const [filterDrift, setFilterDrift] = useState(null);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  
  // Rebalance queue & history states
  const [queue, setQueue] = useState([]);
  const [history, setHistory] = useState(MOCK_AUDIT_TRAIL.filter(a => a.event_type !== 'ComplianceFailure'));
  const [selectedProposal, setSelectedProposal] = useState(null);
  const [reviewerComments, setReviewerComments] = useState('');
  
  // Agent & audit states
  const [agentLogs, setAgentLogs] = useState(AGENT_MOCK_LOGS);
  const [isSimulatingAgent, setIsSimulatingAgent] = useState(false);
  const [auditLogs, setAuditLogs] = useState(MOCK_AUDIT_TRAIL);
  const [auditFilter, setAuditFilter] = useState('all');
  const [expandedAuditId, setExpandedAuditId] = useState(null);
  
  // Explainability tab state
  const [selectedXAIProposal, setSelectedXAIProposal] = useState(null);
  const [xaiReportTab, setXaiReportTab] = useState('client');
  
  // UI States
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  const notify = (msg, type = 'info') => {
    setNotification({ message: msg, type });
    setTimeout(() => setNotification(null), 5000);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: loginEmail || 'manager@wealthpilot.ai',
          password: loginPassword || 'Password123'
        })
      });
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        localStorage.setItem('token', data.access_token);
        notify("Access Granted. Welcome to WealthPilot Security Console.", "success");
      } else {
        notify("Invalid administrative credentials. Please try again.", "danger");
      }
    } catch (err) {
      console.warn("Backend authentication unreachable. Entering Simulation Mode.", err);
      // Simulate login for standalone frontend evaluation
      setToken("simulated-jwt-bearer-token-key-99238c8");
      notify("Offline Mode: Initialized standalone security workspace simulation.", "success");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem('token');
    notify("Session logged out successfully.", "info");
  };

  // Fetch Dashboard Stats
  const fetchMetrics = async () => {
    if (!token) return;
    try {
      const res = await fetch('http://localhost:8000/api/v1/rebalance/metrics', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.log("Using local metrics simulation.");
    }
  };

  // Fetch Portfolios Page
  const fetchPortfolios = async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      let url = `http://localhost:8000/api/v1/portfolios?page=${portfolioPage}&limit=10`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;
      if (filterRisk) url += `&risk_category=${encodeURIComponent(filterRisk)}`;
      if (filterDrift !== null) url += `&needs_rebalance=${filterDrift}`;
      
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPortfolios(data.data || []);
        setPortfolioTotal(data.total || 0);
      }
    } catch (err) {
      // Simulate client list fallback
      console.warn("Backend unavailable. Initializing mock portfolios list.");
      const mockPortfolios = Array.from({ length: 10 }).map((_, idx) => {
        const id = `p-uuid-${100 + idx}`;
        return {
          id,
          account_number: `WP-${1000 + idx}`,
          client_name: ["Sarah Jenkins", "Robert Vance", "Michael Chen", "Sophia Loren", "David Miller", "Emma Watson", "James Bond", "Bruce Wayne", "Clark Kent", "Peter Parker"][idx],
          risk_category: ["Balanced", "Growth", "Conservative", "Aggressive", "Balanced", "Moderately Conservative", "Aggressive", "Growth", "Conservative", "Balanced"][idx],
          total_value: 250000.0 + idx * 75000.0,
          cash_balance: 5000.0 + idx * 12000.0,
          current_drift: idx === 0 ? 0.0782 : 0.012 + (idx * 0.009),
          needs_rebalance: idx === 0 || idx === 4 || idx === 7,
          last_rebalanced: new Date().toISOString()
        };
      });
      setPortfolios(mockPortfolios);
      setPortfolioTotal(35);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch Queue items
  const fetchQueue = async () => {
    if (!token) return;
    try {
      const res = await fetch('http://localhost:8000/api/v1/rebalance/queue', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setQueue(data);
        if (data.length > 0 && !selectedProposal) {
          setSelectedProposal(data[0]);
        }
      }
    } catch (err) {
      // Simulate pending review queue list fallback
      const mockQueue = [
        {
          proposal_id: "prop_8fc3b92",
          portfolio_id: "p-uuid-00042",
          account_number: "WP-000042",
          client_name: "Sarah Jenkins",
          trigger_type: "Threshold",
          reason: "Asset Class SPY allocation has drifted from target weight of 45.0% by +7.42% absolute difference.",
          created_at: new Date().toISOString(),
          proposed_trades: [
            { symbol: "SPY", action: "SELL", shares: 54, estimated_price: 515.20, tax_impact: 3450.0 },
            { symbol: "AGG", action: "BUY", shares: 284, estimated_price: 98.40, tax_impact: 0.0 }
          ],
          shap_explanations: {
            shap_values: {
              drift_magnitude: 0.65,
              tax_savings: 0.38,
              cash_drift: 0.12,
              market_volatility: 0.08,
              transaction_cost: -0.15
            }
          }
        }
      ];
      setQueue(mockQueue);
      if (!selectedProposal) {
        setSelectedProposal(mockQueue[0]);
      }
    }
  };

  // Fetch History logs
  const fetchHistory = async () => {
    if (!token) return;
    try {
      const res = await fetch('http://localhost:8000/api/v1/rebalance/history', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (err) {
      console.log("Using local history logs.");
    }
  };

  // Fetch Portfolio Detail
  const fetchPortfolioDetail = async (id) => {
    if (!token) return;
    try {
      const res = await fetch(`http://localhost:8000/api/v1/portfolios/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedPortfolio(data);
      }
    } catch (err) {
      // Simulate detail breakdown
      const mockDetails = {
        id,
        account_number: "WP-000042",
        client_name: "Sarah Jenkins",
        risk_category: "Balanced",
        total_value: 350000.0,
        cash_balance: 15000.0,
        current_drift: 0.0782,
        needs_rebalance: true,
        holdings: [
          { symbol: "SPY", name: "SPDR S&P 500 ETF Trust", asset_class: "Equity", shares: 356, market_value: 183411.20, current_weight: 0.5242, target_weight: 0.4500, drift: 0.0742 },
          { symbol: "QQQ", name: "Invesco QQQ Trust", asset_class: "Equity", shares: 80, market_value: 35080.00, current_weight: 0.1002, target_weight: 0.1000, drift: 0.0002 },
          { symbol: "AGG", name: "iShares Core U.S. Aggregate Bond ETF", asset_class: "Fixed Income", shares: 802, market_value: 78916.80, current_weight: 0.2254, target_weight: 0.3000, drift: -0.0746 },
          { symbol: "GLD", name: "SPDR Gold Shares", asset_class: "Alternative", shares: 81, market_value: 17463.60, current_weight: 0.0499, target_weight: 0.0500, drift: -0.0001 },
          { symbol: "CASH", name: "Cash Balance (USD)", asset_class: "Cash", shares: 15000.0, market_value: 15000.00, current_weight: 0.0428, target_weight: 0.1000, drift: -0.0572 }
        ],
        audit_logs: MOCK_AUDIT_TRAIL.filter(log => log.portfolio_id === "p-uuid-00042")
      };
      setSelectedPortfolio(mockDetails);
    }
  };

  const handleApprovalAction = async (proposalId, action) => {
    if (!token) return;
    try {
      const res = await fetch(`http://localhost:8000/api/v1/rebalance/${proposalId}/action`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          action,
          comments: reviewerComments.trim() || (action === 'APPROVED' ? 'System approved lot-rebalancing trades.' : 'Manager overridden rebalance proposal.')
        })
      });
      if (res.ok) {
        notify(`Rebalancing proposal ${proposalId} has been successfully ${action === 'APPROVED' ? 'executed' : 'rejected'}.`, 'success');
        fetchMetrics();
        fetchQueue();
        fetchHistory();
        setReviewerComments('');
        setSelectedProposal(null);
      } else {
        notify("Transaction processing error. Failed to commit actions.", "danger");
      }
    } catch (err) {
      // Simulate action logic in frontend state if offline
      notify(`[SIMULATED] Proposal ${proposalId} successfully ${action === 'APPROVED' ? 'Executed' : 'Rejected'}.`, "success");
      
      const matchedProp = queue.find(q => q.proposal_id === proposalId);
      if (matchedProp) {
        const newHistoryItem = {
          id: `aud-${Date.now()}`,
          portfolio_id: matchedProp.portfolio_id,
          account_number: matchedProp.account_number,
          client_name: matchedProp.client_name,
          event_type: action === 'APPROVED' ? "OrderExecution" : "OrderApproval",
          details: action === 'APPROVED' ? 
            `Simulated execution approved. Comments: ${reviewerComments || 'System approved.'}` : 
            `Simulated rejection. Comments: ${reviewerComments || 'Overridden by supervisor.'}`,
          timestamp: new Date().toISOString(),
          state_before: JSON.stringify({ cash: 15000.0, holdings: { SPY: 356, QQQ: 80, AGG: 802 } }),
          state_after: action === 'APPROVED' ? 
            JSON.stringify({ cash: 42808.0, holdings: { SPY: 302, QQQ: 80, AGG: 1086 } }) : 
            JSON.stringify({ cash: 15000.0, holdings: { SPY: 356, QQQ: 80, AGG: 802 } })
        };
        setHistory(prev => [newHistoryItem, ...prev]);
        setAuditLogs(prev => [newHistoryItem, ...prev]);
      }
      
      setQueue(prev => prev.filter(q => q.proposal_id !== proposalId));
      setSelectedProposal(null);
      setReviewerComments('');
    }
  };

  const handleTriggerRebalance = async (portfolioId = null) => {
    setIsSimulatingAgent(true);
    setAgentLogs(["[Supervisor Command] Triggering live drift evaluation council..."]);
    
    try {
      const reqBody = { trigger_type: portfolioId ? "Event" : "Threshold" };
      if (portfolioId) reqBody.portfolio_ids = [portfolioId];
      
      const res = await fetch('http://localhost:8000/api/v1/rebalance/trigger', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(reqBody)
      });
      if (res.ok) {
        const result = await res.json();
        // Animate logs sequentially to showcase reasoning trace
        if (result.data && result.data.length > 0) {
          const runLog = result.data[0].execution_log || AGENT_MOCK_LOGS;
          let idx = 0;
          const logTimer = setInterval(() => {
            if (idx < runLog.length) {
              setAgentLogs(prev => [...prev, runLog[idx]]);
              idx++;
            } else {
              clearInterval(logTimer);
              setIsSimulatingAgent(false);
              notify("Automated agent council has submitted recommendations.", "success");
              fetchMetrics();
              fetchQueue();
            }
          }, 300);
        }
      }
    } catch (err) {
      // Simulate sequential logs fallback
      let idx = 0;
      const logTimer = setInterval(() => {
        if (idx < AGENT_MOCK_LOGS.length) {
          setAgentLogs(prev => [...prev, AGENT_MOCK_LOGS[idx]]);
          idx++;
        } else {
          clearInterval(logTimer);
          setIsSimulatingAgent(false);
          notify("[Simulated] Agent rebalance run completed.", "success");
        }
      }, 400);
    }
  };

  useEffect(() => {
    if (token) {
      fetchMetrics();
      fetchPortfolios();
      fetchQueue();
      fetchHistory();
    }
  }, [portfolioPage, searchQuery, filterRisk, filterDrift, token]);

  // Handle detailed portfolio modal activation
  const openPortfolioModal = (id) => {
    fetchPortfolioDetail(id);
  };

  // Audit Logs filtered items
  const filteredAudits = auditLogs.filter(log => {
    if (auditFilter === 'all') return true;
    return log.event_type.toLowerCase() === auditFilter.toLowerCase();
  });

  if (!token) {
    // -------------------------------------------------------------
    // PAGE 1: AUTHENTICATION / LOGIN SCREEN
    // -------------------------------------------------------------
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center font-sans p-6 relative overflow-hidden">
        {/* Background radial blurs */}
        <div className="absolute top-1/4 left-1/4 w-[350px] h-[350px] bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none"></div>
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-purple-600/10 rounded-full blur-[120px] pointer-events-none"></div>

        <div className="w-full max-w-md bg-slate-900/60 backdrop-blur-xl border border-white/5 rounded-2xl shadow-2xl p-8 relative z-10">
          <div className="flex flex-col items-center mb-8">
            <div className="p-3 bg-gradient-to-tr from-cyan-400 to-purple-600 rounded-xl shadow-lg shadow-cyan-400/10 mb-4 animate-pulse">
              <Shield className="w-8 h-8 text-slate-950" />
            </div>
            <h1 className="text-2xl font-bold font-title tracking-tight text-white mb-1">WealthPilot AI Core</h1>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Autonomous Rebalancing Platform</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Administrative User</label>
              <div className="relative">
                <input 
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="manager@wealthpilot.ai"
                  className="w-full bg-slate-950/70 border border-slate-800 rounded-lg py-3 px-4 text-sm focus:outline-none focus:border-cyan-400 text-white placeholder-slate-600 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Access PIN / Password</label>
              <div className="relative">
                <input 
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-950/70 border border-slate-800 rounded-lg py-3 px-4 text-sm focus:outline-none focus:border-cyan-400 text-white placeholder-slate-600 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 text-slate-950 font-bold py-3 px-4 rounded-lg text-sm transition-all transform hover:-translate-y-0.5 shadow-lg shadow-cyan-400/20 active:translate-y-0 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
              ) : (
                <Lock className="w-4 h-4" />
              )}
              <span>Decrypt & Authorize Session</span>
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-slate-800/60 text-center">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">
              Protected by SEBI Compliance Enforcer & Sentinel Logs
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans flex">
      {/* Toast Alert */}
      {notification && (
        <div className={`fixed bottom-6 right-6 p-4 rounded-xl border backdrop-blur-md z-50 shadow-2xl flex items-center gap-3 animate-slide-up duration-300 ${
          notification.type === 'success' ? 'bg-emerald-950/90 border-emerald-500/30 text-emerald-200' :
          notification.type === 'danger' ? 'bg-red-950/90 border-red-500/30 text-red-200' :
          'bg-slate-900/90 border-cyan-500/30 text-cyan-200'
        }`}>
          {notification.type === 'success' && <CheckCircle className="w-5 h-5 text-emerald-400" />}
          {notification.type === 'danger' && <XCircle className="w-5 h-5 text-red-400" />}
          {notification.type === 'info' && <Info className="w-5 h-5 text-cyan-400" />}
          <span className="text-sm font-semibold">{notification.message}</span>
        </div>
      )}

      {/* -------------------------------------------------------------
          SIDEBAR NAVIGATION
          ------------------------------------------------------------- */}
      <aside className="w-64 bg-slate-900/40 border-r border-white/5 backdrop-blur-2xl flex flex-col fixed h-screen z-40">
        <div className="p-6 border-b border-white/5 flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-cyan-400 to-purple-600 rounded-lg">
            <Shield className="w-5 h-5 text-slate-950" />
          </div>
          <div>
            <h2 className="font-bold font-title text-sm tracking-wide text-white">WealthPilot AI</h2>
            <p className="text-[9px] uppercase tracking-wider text-cyan-400 font-bold">Sentinel Control</p>
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {[
            { id: 'dashboard', name: 'Dashboard Overview', icon: TrendingUp },
            { id: 'portfolios', name: 'Portfolio Monitor', icon: Briefcase },
            { id: 'rebalancing', name: 'Rebalance decisions', icon: Sliders },
            { id: 'agents', name: 'Agent Activity', icon: Terminal },
            { id: 'compliance', name: 'Compliance Center', icon: Award },
            { id: 'audit', name: 'Audit Logs Trail', icon: FileText },
            { id: 'explainability', name: 'Explainability Reports', icon: BookOpen }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                activeTab === tab.id 
                  ? 'bg-cyan-500/10 text-cyan-400 shadow-inner border-l-2 border-cyan-400' 
                  : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.name}</span>
            </button>
          ))}
        </nav>

        {/* User Card */}
        <div className="p-4 border-t border-white/5 bg-slate-950/30 flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center font-bold text-cyan-400">
              M
            </div>
            <div className="overflow-hidden">
              <p className="text-xs text-white font-semibold truncate">PM Supervisor</p>
              <p className="text-[9px] text-slate-500 truncate">manager@wealthpilot.ai</p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 ml-64 min-h-screen p-8 bg-gradient-to-b from-slate-950 to-slate-900/90 relative">
        
        {/* HEADER BAR */}
        <header className="flex items-center justify-between pb-6 border-b border-white/5 mb-8">
          <div>
            <h1 className="text-2xl font-bold font-title text-white tracking-tight">
              {activeTab === 'dashboard' && 'Portfolio Sentinel Console'}
              {activeTab === 'portfolios' && 'Client Portfolio Monitor'}
              {activeTab === 'rebalancing' && 'Rebalance decisions & Overrides'}
              {activeTab === 'agents' && 'Agent reasoning traces'}
              {activeTab === 'compliance' && 'SEBI Compliance Center'}
              {activeTab === 'audit' && 'Audit Log Trail'}
              {activeTab === 'explainability' && 'SHAP Explainability Reports'}
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              {activeTab === 'dashboard' && 'Aggregate assets under management, global drift parameters, and harvested tax-loss savings'}
              {activeTab === 'portfolios' && 'Search client allocations, monitor individual asset class drift parameters, and HIFO lots'}
              {activeTab === 'rebalancing' && 'Approve order blocks, view pre-trade compliance checks, and submit reviewer override overrides'}
              {activeTab === 'agents' && 'Execution reasoning trace of the CrewAI council agents'}
              {activeTab === 'compliance' && 'Real-time validation of regulatory rules, sector allocations, and asset concentrations'}
              {activeTab === 'audit' && 'Immutable system database history including state-before and state-after tracking'}
              {activeTab === 'explainability' && 'Quantitative feature attributions of rebalancing triggers using Shapley values'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleTriggerRebalance()}
              disabled={isSimulatingAgent}
              className="px-4 py-2 bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 text-slate-950 font-bold rounded-lg text-xs tracking-wide transition-all shadow-md active:scale-95 flex items-center gap-2"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSimulatingAgent ? 'animate-spin' : ''}`} />
              <span>Council evaluation run</span>
            </button>
          </div>
        </header>

        {/* -------------------------------------------------------------
            PAGE 2: DASHBOARD TAB
            ------------------------------------------------------------- */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8 animate-fadeIn">
            {/* KPI Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
              {[
                { label: 'Total AUM Monitored', val: `$${(metrics.total_aum / 1000000).toFixed(1)}M`, icon: DollarSign, color: 'text-cyan-400', bg: 'bg-cyan-500/5' },
                { label: 'Active Portfolios', val: metrics.total_portfolios.toLocaleString(), icon: Briefcase, color: 'text-purple-400', bg: 'bg-purple-500/5' },
                { label: 'Average Drift', val: `${(metrics.average_drift * 100).toFixed(2)}%`, icon: TrendingUp, color: 'text-amber-400', bg: 'bg-amber-500/5' },
                { label: 'Drifted Accounts', val: metrics.drifted_count, icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/5' },
                { label: 'Queue approvals', val: metrics.pending_approvals, icon: UserCheck, color: 'text-teal-400', bg: 'bg-teal-500/5' },
                { label: 'Tax-Shield savings', val: `$${(metrics.tax_savings_harvested / 1000).toFixed(1)}K`, icon: Shield, color: 'text-emerald-400', bg: 'bg-emerald-500/5' }
              ].map((kpi, i) => (
                <div key={i} className="bg-slate-900/40 border border-white/5 rounded-xl p-4 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">{kpi.label}</span>
                    <h3 className="text-xl font-bold text-white mt-1.5 font-title">{kpi.val}</h3>
                  </div>
                  <div className={`p-2.5 rounded-lg ${kpi.bg} ${kpi.color}`}>
                    <kpi.icon className="w-5 h-5" />
                  </div>
                </div>
              ))}
            </div>

            {/* Charts Panel */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Chart 1: AUM growth */}
              <div className="bg-slate-900/40 border border-white/5 rounded-xl p-6">
                <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-wider flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-cyan-400" />
                  <span>AUM Growth & Performance</span>
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={MOCK_AUM_DATA}>
                      <defs>
                        <linearGradient id="aumGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#00f2fe" stopOpacity={0.2}/>
                          <stop offset="95%" stopColor="#00f2fe" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                      <XAxis dataKey="month" stroke="#64748b" fontSize={11} />
                      <YAxis stroke="#64748b" fontSize={11} tickFormatter={(val) => `$${val / 1000000}M`} />
                      <Tooltip 
                        contentStyle={{ background: '#0a0f1d', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                        formatter={(val) => [`$${val.toLocaleString()}`, 'AUM']}
                      />
                      <Area type="monotone" dataKey="AUM" stroke="#00f2fe" strokeWidth={2} fillOpacity={1} fill="url(#aumGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 2: Drift Distribution */}
              <div className="bg-slate-900/40 border border-white/5 rounded-xl p-6">
                <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-wider flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                  <span>Drift Index Distribution</span>
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={MOCK_DRIFT_DIST}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                      <XAxis dataKey="range" stroke="#64748b" fontSize={11} />
                      <YAxis stroke="#64748b" fontSize={11} />
                      <Tooltip 
                        contentStyle={{ background: '#0a0f1d', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                      />
                      <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]}>
                        {MOCK_DRIFT_DIST.map((entry, index) => {
                          const colors = ['#10b981', '#f59e0b', '#ef4444'];
                          return <Cell key={`cell-${index}`} fill={colors[index]} />;
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Simulated terminal overlay on dashboard if running */}
            {isSimulatingAgent && (
              <div className="bg-black/80 border border-cyan-500/20 rounded-xl p-6 font-mono text-xs shadow-lg shadow-cyan-500/5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-cyan-400 animate-pulse" />
                    <span className="font-bold text-slate-200">Autonomous Council Reasoning Trace</span>
                  </div>
                  <span className="text-[10px] bg-cyan-950 text-cyan-400 px-2 py-0.5 rounded border border-cyan-500/20">Running</span>
                </div>
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {agentLogs.map((log, idx) => (
                    <div key={idx} className="text-slate-300">
                      <span className="text-cyan-500">&gt;&gt;</span> {log}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* -------------------------------------------------------------
            PAGE 3: PORTFOLIO MONITOR TAB
            ------------------------------------------------------------- */}
        {activeTab === 'portfolios' && (
          <div className="space-y-8 animate-fadeIn">
            {/* Filtering Bar */}
            <div className="bg-slate-900/40 border border-white/5 rounded-xl p-4 flex flex-wrap gap-4 items-center justify-between">
              <div className="flex items-center gap-3 bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-2 w-72">
                <Search className="w-4 h-4 text-slate-500" />
                <input 
                  type="text" 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search account, client name..."
                  className="bg-transparent border-none text-xs text-white focus:outline-none w-full"
                />
              </div>

              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 text-xs">
                  <Filter className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-slate-400 font-semibold">Risk:</span>
                  <select 
                    value={filterRisk}
                    onChange={(e) => setFilterRisk(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded py-1 px-2.5 text-xs text-white focus:outline-none"
                  >
                    <option value="">All Categories</option>
                    <option value="Conservative">Conservative</option>
                    <option value="Balanced">Balanced</option>
                    <option value="Growth">Growth</option>
                    <option value="Aggressive">Aggressive</option>
                  </select>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-400 font-semibold">Drift status:</span>
                  <select 
                    onChange={(e) => {
                      const v = e.target.value;
                      setFilterDrift(v === "true" ? true : v === "false" ? false : null);
                    }}
                    className="bg-slate-950 border border-slate-800 rounded py-1 px-2.5 text-xs text-white focus:outline-none"
                  >
                    <option value="">All States</option>
                    <option value="true">Drifted (&gt; 5%)</option>
                    <option value="false">Compliant</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Portfolios Table */}
            <div className="bg-slate-900/40 border border-white/5 rounded-xl overflow-hidden">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-white/5 bg-slate-950/20 text-slate-400 font-semibold">
                    <th className="p-4">Account ID</th>
                    <th>Client Name</th>
                    <th>Risk category</th>
                    <th>Total Value</th>
                    <th>Cash Balance</th>
                    <th>Current Drift</th>
                    <th>Status</th>
                    <th className="p-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolios.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="p-8 text-center text-slate-500 font-semibold">
                        No portfolios match current filters.
                      </td>
                    </tr>
                  ) : portfolios.map(p => (
                    <tr key={p.id} className="border-b border-white/5 hover:bg-slate-800/20 transition-colors">
                      <td className="p-4 font-bold text-white">{p.account_number}</td>
                      <td className="font-semibold">{p.client_name}</td>
                      <td>
                        <span className="badge badge-info text-[9px]">{p.risk_category}</span>
                      </td>
                      <td>${p.total_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                      <td>${p.cash_balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                      <td className={`font-bold ${p.needs_rebalance ? 'text-amber-400' : 'text-slate-400'}`}>
                        {(p.current_drift * 100).toFixed(2)}%
                      </td>
                      <td>
                        <span className={`badge text-[9px] ${p.needs_rebalance ? 'badge-warning' : 'badge-success'}`}>
                          {p.needs_rebalance ? 'Drifted' : 'Aligned'}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <button 
                          onClick={() => openPortfolioModal(p.id)}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded font-bold text-[10px] transition-colors"
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {/* Pagination controls */}
              <div className="p-4 border-t border-white/5 bg-slate-950/10 flex items-center justify-between text-slate-400">
                <span>Page {portfolioPage} of {Math.ceil(portfolioTotal / 10)}</span>
                <div className="flex gap-2">
                  <button 
                    disabled={portfolioPage === 1}
                    onClick={() => setPortfolioPage(prev => Math.max(1, prev - 1))}
                    className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded font-semibold disabled:opacity-50"
                  >
                    Prev
                  </button>
                  <button 
                    disabled={portfolioPage >= Math.ceil(portfolioTotal / 10)}
                    onClick={() => setPortfolioPage(prev => prev + 1)}
                    className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded font-semibold disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>

            {/* Portfolio detail slideout / overlay */}
            {selectedPortfolio && (
              <div className="bg-slate-900 border border-white/10 rounded-2xl p-6 space-y-8 animate-fadeIn">
                <div className="flex items-center justify-between border-b border-white/5 pb-4">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">Portfolio breakdown</span>
                    <h2 className="text-xl font-bold text-white font-title mt-1">{selectedPortfolio.client_name} ({selectedPortfolio.account_number})</h2>
                  </div>
                  <button 
                    onClick={() => setSelectedPortfolio(null)}
                    className="text-slate-400 hover:text-white bg-slate-800 p-1.5 rounded"
                  >
                    Close
                  </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Stats & Class breakdown */}
                  <div className="bg-slate-950/40 border border-white/5 rounded-xl p-4 space-y-4">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">Allocation Metrics</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-slate-900 p-3 rounded-lg">
                        <span className="text-[10px] text-slate-400 uppercase block">Total Value</span>
                        <span className="text-sm font-bold text-white">${selectedPortfolio.total_value.toLocaleString()}</span>
                      </div>
                      <div className="bg-slate-900 p-3 rounded-lg">
                        <span className="text-[10px] text-slate-400 uppercase block">Current Drift</span>
                        <span className="text-sm font-bold text-amber-400">{(selectedPortfolio.current_drift * 100).toFixed(2)}%</span>
                      </div>
                    </div>

                    <div className="h-48 flex items-center justify-center">
                      {/* Radar Chart comparing target vs actual */}
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" radius="70%" data={selectedPortfolio.holdings.filter(h => h.symbol !== 'CASH')}>
                          <PolarGrid stroke="rgba(255,255,255,0.05)" />
                          <PolarAngleAxis dataKey="symbol" stroke="#64748b" fontSize={9} />
                          <PolarRadiusAxis angle={30} domain={[0, 0.6]} tick={false} stroke="transparent" />
                          <Radar name="Target" dataKey="target_weight" stroke="#8a2be2" fill="#8a2be2" fillOpacity={0.1} />
                          <Radar name="Actual" dataKey="current_weight" stroke="#00f2fe" fill="#00f2fe" fillOpacity={0.3} />
                          <Tooltip contentStyle={{ background: '#0a0f1d', border: '1px solid rgba(255,255,255,0.1)' }} />
                          <Legend wrapperStyle={{ fontSize: 10 }} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Holdings list */}
                  <div className="lg:col-span-2 bg-slate-950/40 border border-white/5 rounded-xl p-4 overflow-hidden">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-4">Target vs Actual Weights</h4>
                    <table className="w-full text-left border-collapse text-[11px]">
                      <thead>
                        <tr className="border-b border-white/5 text-slate-400">
                          <th className="pb-2">Asset</th>
                          <th>Class</th>
                          <th>Shares</th>
                          <th>Market Value</th>
                          <th>Target %</th>
                          <th>Actual %</th>
                          <th className="text-right">Drift</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedPortfolio.holdings.map(h => (
                          <tr key={h.symbol} className="border-b border-white/5">
                            <td className="py-2.5 font-bold text-white">{h.symbol}</td>
                            <td>{h.asset_class}</td>
                            <td>{h.symbol === 'CASH' ? '-' : h.shares.toLocaleString()}</td>
                            <td>${h.market_value.toLocaleString()}</td>
                            <td>{(h.target_weight * 100).toFixed(1)}%</td>
                            <td>{(h.current_weight * 100).toFixed(1)}%</td>
                            <td className={`text-right font-semibold ${Math.abs(h.drift) >= 0.05 ? 'text-amber-400' : 'text-slate-400'}`}>
                              {h.drift > 0 ? '+' : ''}{(h.drift * 100).toFixed(1)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* -------------------------------------------------------------
            PAGE 4: REBALANCING DECISIONS (QUEUE & HISTORY)
            ------------------------------------------------------------- */}
        {activeTab === 'rebalancing' && (
          <div className="space-y-8 animate-fadeIn">
            {queue.length === 0 ? (
              <div className="bg-slate-900/40 border border-white/5 rounded-xl p-12 text-center">
                <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-white mb-2 font-title">Rebalance Queue is Empty</h3>
                <p className="text-xs text-slate-400">All managed accounts are currently in alignment with target weights.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Active Pending proposals list */}
                <div className="space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Pending Proposals ({queue.length})</h3>
                  {queue.map(prop => (
                    <div 
                      key={prop.proposal_id}
                      onClick={() => setSelectedProposal(prop)}
                      className={`p-4 border rounded-xl cursor-pointer transition-all ${
                        selectedProposal?.proposal_id === prop.proposal_id 
                          ? 'bg-cyan-500/5 border-cyan-400/40 shadow-lg' 
                          : 'bg-slate-900/40 border-white/5 hover:border-white/10'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-bold text-white uppercase">{prop.account_number}</span>
                        <span className="badge badge-warning text-[9px]">{prop.trigger_type}</span>
                      </div>
                      <h4 className="text-sm font-bold text-white font-title">{prop.client_name}</h4>
                      <p className="text-[11px] text-slate-400 mt-2 line-clamp-2">{prop.reason}</p>
                      <div className="flex justify-between items-center mt-4 text-[10px] text-slate-500 font-semibold">
                        <span>Trades: {prop.proposed_trades.length}</span>
                        <span>{new Date(prop.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Proposal detailed review pane */}
                {selectedProposal && (
                  <div className="lg:col-span-2 bg-slate-900 border border-white/10 rounded-2xl p-6 space-y-6">
                    <div className="flex items-center justify-between border-b border-white/5 pb-4">
                      <div>
                        <span className="text-[9px] text-slate-400 uppercase font-bold block">Supervisor action panel</span>
                        <h2 className="text-lg font-bold text-white font-title mt-0.5">{selectedProposal.client_name} ({selectedProposal.account_number})</h2>
                      </div>
                      <span className="badge badge-warning text-[9px]">Drift check triggered</span>
                    </div>

                    {/* Trades list */}
                    <div>
                      <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Proposed Order block</span>
                      </h4>
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-white/5 text-slate-400">
                            <th className="pb-2">Asset</th>
                            <th>Action</th>
                            <th>Shares</th>
                            <th>Est. Price</th>
                            <th>Trade Value</th>
                            <th className="text-right">Tax Impact</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedProposal.proposed_trades.map((t, idx) => (
                            <tr key={idx} className="border-b border-white/5">
                              <td className="py-2 font-bold text-white">{t.symbol}</td>
                              <td>
                                <span className={`badge text-[9px] ${t.action === 'BUY' ? 'badge-success' : 'badge-danger'}`}>
                                  {t.action}
                                </span>
                              </td>
                              <td>{t.shares.toLocaleString()}</td>
                              <td>${t.estimated_price.toFixed(2)}</td>
                              <td>${(t.shares * t.estimated_price).toLocaleString()}</td>
                              <td className={`text-right font-bold ${t.tax_impact > 0 ? 'text-emerald-400' : 'text-slate-500'}`}>
                                {t.tax_impact > 0 ? `-$${t.tax_impact.toLocaleString()} (Shield)` : '$0.00'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Compliance indicator list */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-slate-950/40 border border-emerald-500/20 rounded-xl p-3 flex gap-2.5 items-start">
                        <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <div>
                          <h5 className="text-xs font-bold text-white">Concentration Limits Checked</h5>
                          <p className="text-[10px] text-slate-400 mt-1">Rebalancing will not exceed any individual security bounds.</p>
                        </div>
                      </div>
                      <div className="bg-slate-950/40 border border-emerald-500/20 rounded-xl p-3 flex gap-2.5 items-start">
                        <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <div>
                          <h5 className="text-xs font-bold text-white">Restricted Asset Screening</h5>
                          <p className="text-[10px] text-slate-400 mt-1">Clear: none of the target symbols reside on prohibited tickers lists.</p>
                        </div>
                      </div>
                    </div>

                    {/* SHAP attributions */}
                    <div>
                      <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-2">SHAP Trigger Attributions</h4>
                      <p className="text-[10px] text-slate-400 mb-4">Quantitative feature weights contributing towards automated trigger decision.</p>
                      
                      <div className="space-y-3 bg-slate-950/50 border border-white/5 rounded-xl p-4">
                        {[
                          { label: 'Asset Class Drift Index', key: 'drift_magnitude', color: 'bg-cyan-400' },
                          { label: 'Tax Loss Harvesting Savings', key: 'tax_savings', color: 'bg-emerald-400' },
                          { label: 'Cash Flow Deviation', key: 'cash_drift', color: 'bg-amber-400' }
                        ].map((item, idx) => {
                          const val = selectedProposal.shap_explanations.shap_values[item.key] || 0;
                          const widthPct = Math.min(100, (val / 0.8) * 100);
                          return (
                            <div key={idx} className="flex items-center justify-between gap-4">
                              <span className="text-[11px] font-semibold text-slate-300 w-48 truncate">{item.label}</span>
                              <div className="flex-1 bg-slate-900 rounded h-2.5 overflow-hidden">
                                <div className={`h-full ${item.color}`} style={{ width: `${widthPct}%` }}></div>
                              </div>
                              <span className="text-xs font-mono font-bold text-slate-200">+{val.toFixed(2)}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Review Comments text area */}
                    <div className="flex flex-col gap-2 border-t border-white/5 pt-4">
                      <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Supervisor override comments</label>
                      <textarea
                        value={reviewerComments}
                        onChange={(e) => setReviewerComments(e.target.value)}
                        placeholder="Provide reasoning for override clearance, custodian limits, or tax deferrals..."
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs focus:outline-none focus:border-cyan-400 text-white min-h-[60px]"
                      />
                    </div>

                    {/* Action buttons */}
                    <div className="flex justify-end gap-3 border-t border-white/5 pt-4">
                      <button 
                        onClick={() => handleApprovalAction(selectedProposal.proposal_id, 'REJECTED')}
                        className="px-4 py-2 border border-red-500/30 text-red-400 hover:bg-red-500/5 rounded-lg text-xs font-bold transition-all"
                      >
                        Reject Proposal
                      </button>
                      <button 
                        onClick={() => handleApprovalAction(selectedProposal.proposal_id, 'APPROVED')}
                        className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-slate-950 rounded-lg text-xs font-bold shadow-lg shadow-emerald-500/10 transition-all"
                      >
                        Approve Order block
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Historical Audit Actions */}
            <div className="bg-slate-900/40 border border-white/5 rounded-xl p-6">
              <h3 className="text-sm font-bold text-white mb-2 uppercase tracking-wider font-title">Processed decisions Logs (Sentinel Logs)</h3>
              <p className="text-xs text-slate-400 mb-6">History list of approved and rejected rebalance proposals containing reviewer details and comments.</p>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-white/5 text-slate-400 font-semibold">
                      <th className="pb-3 pl-2">Account</th>
                      <th>Client Name</th>
                      <th>Trigger Type</th>
                      <th>Processed Date</th>
                      <th>Override Status</th>
                      <th className="pr-2">Supervisor comments</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map(item => (
                      <tr key={item.id} className="border-b border-white/5 hover:bg-slate-800/10">
                        <td className="py-3 pl-2 font-bold text-white">{item.account_number}</td>
                        <td className="font-semibold">{item.client_name}</td>
                        <td>
                          <span className="badge badge-info text-[9px]">{item.event_type === 'OrderExecution' ? 'Threshold' : 'Calendar'}</span>
                        </td>
                        <td className="text-slate-400">{new Date(item.timestamp).toLocaleString()}</td>
                        <td>
                          <span className={`badge text-[9px] ${item.event_type === 'OrderExecution' ? 'badge-success' : 'badge-danger'}`}>
                            {item.event_type === 'OrderExecution' ? 'Approved' : 'Rejected'}
                          </span>
                        </td>
                        <td className="text-slate-400 italic max-w-xs truncate pr-2" title={item.details}>
                          {item.details.split("Comments:")[1] || "Default override committed."}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------
            PAGE 5: AGENT ACTIVITY CONSOLE
            ------------------------------------------------------------- */}
        {activeTab === 'agents' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="bg-slate-900/40 border border-white/5 rounded-xl p-6 flex flex-wrap gap-4 items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-title mb-1">CrewAI Assessment Council</h3>
                <p className="text-xs text-slate-400">Trigger simulated council analysis run on top drifted accounts to generate explanations.</p>
              </div>
              <button 
                onClick={() => handleTriggerRebalance()}
                disabled={isSimulatingAgent}
                className="px-4 py-2 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-400 hover:to-purple-500 text-white font-bold rounded-lg text-xs tracking-wide transition-all active:scale-95 flex items-center gap-2"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSimulatingAgent ? 'animate-spin' : ''}`} />
                <span>Launch Agent Council Run</span>
              </button>
            </div>

            {/* Terminal Window */}
            <div className="bg-black/80 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
              <div className="bg-slate-900 px-6 py-3 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-yellow-500"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500"></div>
                  <span className="text-xs font-semibold text-slate-400 font-mono ml-3">agentic-council-execution.log</span>
                </div>
                <span className="text-[10px] text-slate-600 font-mono">Terminal v1.4</span>
              </div>
              <div className="p-6 font-mono text-[11px] leading-relaxed max-h-[500px] overflow-y-auto space-y-2.5 select-text">
                {agentLogs.map((log, index) => {
                  let colorClass = "text-slate-300";
                  if (log.includes("[Portfolio Monitor]")) colorClass = "text-cyan-400";
                  else if (log.includes("[Tax Optimizer]")) colorClass = "text-emerald-400";
                  else if (log.includes("[Compliance Auditor]")) colorClass = "text-amber-400";
                  else if (log.includes("[Market Analyst]")) colorClass = "text-indigo-400";
                  else if (log.includes("[Risk Assessor]")) colorClass = "text-purple-400";
                  else if (log.includes("[Supervisor Command]")) colorClass = "text-purple-200 font-bold";
                  
                  return (
                    <div key={index} className="flex gap-2">
                      <span className="text-slate-600 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                      <span className={colorClass}>{log}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------
            PAGE 6: COMPLIANCE CENTER
            ------------------------------------------------------------- */}
        {activeTab === 'compliance' && (
          <div className="space-y-8 animate-fadeIn">
            {/* Top compliance health bar */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-slate-900/40 border border-white/5 rounded-xl p-6 flex flex-col items-center justify-center text-center">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2">Compliance Score</span>
                <div className="w-32 h-32 flex items-center justify-center relative">
                  <span className="text-3xl font-extrabold text-white font-title">98.4%</span>
                  <div className="absolute inset-0 border-4 border-slate-800 rounded-full border-t-emerald-500"></div>
                </div>
              </div>

              <div className="md:col-span-2 bg-slate-900/40 border border-white/5 rounded-xl p-6 space-y-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-title">SEBI Regulatory Directives Checklist</h3>
                <p className="text-xs text-slate-400">WealthPilot AI automatically audits all proposed orders against the security framework.</p>
                
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="bg-slate-950/40 border border-slate-800/40 p-3 rounded-lg flex items-center gap-2">
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs text-slate-300 font-semibold">Single Security Rule Limit</span>
                  </div>
                  <div className="bg-slate-950/40 border border-slate-800/40 p-3 rounded-lg flex items-center gap-2">
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs text-slate-300 font-semibold">Sector Exposure Rules</span>
                  </div>
                  <div className="bg-slate-950/40 border border-slate-800/40 p-3 rounded-lg flex items-center gap-2">
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs text-slate-300 font-semibold">Client Risk Profile Mapping</span>
                  </div>
                  <div className="bg-slate-950/40 border border-slate-800/40 p-3 rounded-lg flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <span className="text-xs text-slate-300 font-semibold">Wash Sale Exemption warnings</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Active Compliance rules table */}
            <div className="bg-slate-900/40 border border-white/5 rounded-xl p-6">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-title mb-6">Sentinel Rules Matrix</h3>
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-white/5 text-slate-400">
                    <th className="pb-3">Rule Definition</th>
                    <th>Audit Description</th>
                    <th>Constraint Limit</th>
                    <th>Current Value</th>
                    <th className="text-right">Validation</th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_COMPLIANCE_RULES.map(rule => (
                    <tr key={rule.id} className="border-b border-white/5">
                      <td className="py-4 font-bold text-white">{rule.rule}</td>
                      <td className="text-slate-400 max-w-sm">{rule.desc}</td>
                      <td className="font-mono">{rule.limit}</td>
                      <td className="font-mono">{rule.actual}</td>
                      <td className="text-right">
                        <span className={`badge text-[9px] ${
                          rule.status === 'PASS' ? 'badge-success' : 'badge-warning'
                        }`}>
                          {rule.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------
            PAGE 7: AUDIT LOGS TAB
            ------------------------------------------------------------- */}
        {activeTab === 'audit' && (
          <div className="space-y-6 animate-fadeIn">
            {/* Filter controls */}
            <div className="bg-slate-900/40 border border-white/5 rounded-xl p-4 flex gap-3 items-center">
              <span className="text-xs text-slate-400 font-semibold flex items-center gap-1">
                <Filter className="w-3.5 h-3.5" />
                <span>Filter logs:</span>
              </span>
              {['All', 'OrderApproval', 'OrderExecution', 'ComplianceFailure'].map((f) => (
                <button
                  key={f}
                  onClick={() => setAuditFilter(f.toLowerCase())}
                  className={`px-3 py-1.5 rounded-lg text-[10px] font-bold tracking-wide transition-all ${
                    auditFilter === f.toLowerCase()
                      ? 'bg-cyan-500/10 border border-cyan-500/20 text-cyan-400'
                      : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {f === 'All' ? 'All Logs' : f}
                </button>
              ))}
            </div>

            {/* Audit Logs table */}
            <div className="bg-slate-900/40 border border-white/5 rounded-xl overflow-hidden">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-white/5 bg-slate-950/20 text-slate-400 font-semibold">
                    <th className="p-4">Timestamp</th>
                    <th>Account</th>
                    <th>Client Name</th>
                    <th>Event Type</th>
                    <th>Activity Details</th>
                    <th className="p-4 text-right">State Diffs</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAudits.map(log => (
                    <React.Fragment key={log.id}>
                      <tr className="border-b border-white/5 hover:bg-slate-800/10">
                        <td className="p-4 text-slate-400 font-mono">{new Date(log.timestamp).toLocaleString()}</td>
                        <td className="font-bold text-white">{log.account_number}</td>
                        <td className="font-semibold">{log.client_name}</td>
                        <td>
                          <span className={`badge text-[9px] ${
                            log.event_type === 'OrderExecution' ? 'badge-success' :
                            log.event_type === 'OrderApproval' ? 'badge-info' : 'badge-danger'
                          }`}>
                            {log.event_type}
                          </span>
                        </td>
                        <td className="text-slate-300 max-w-sm truncate" title={log.details}>
                          {log.details}
                        </td>
                        <td className="p-4 text-right">
                          <button
                            onClick={() => setExpandedAuditId(expandedAuditId === log.id ? null : log.id)}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-bold text-[9px] transition-colors"
                          >
                            {expandedAuditId === log.id ? 'Hide State' : 'View State'}
                          </button>
                        </td>
                      </tr>
                      {expandedAuditId === log.id && (
                        <tr className="bg-slate-950/80 border-b border-white/5">
                          <td colSpan={6} className="p-6">
                            {log.state_before && log.state_after ? (
                              <div className="grid grid-cols-2 gap-8 font-mono text-[10px] leading-relaxed">
                                <div>
                                  <h5 className="text-[9px] uppercase tracking-wider text-slate-500 font-bold mb-2">State Before Execution</h5>
                                  <pre className="bg-slate-900 border border-slate-800/60 rounded-lg p-3 text-red-300 max-h-40 overflow-y-auto">
                                    {JSON.stringify(JSON.parse(log.state_before), null, 2)}
                                  </pre>
                                </div>
                                <div>
                                  <h5 className="text-[9px] uppercase tracking-wider text-slate-500 font-bold mb-2">State After Execution</h5>
                                  <pre className="bg-slate-900 border border-slate-800/60 rounded-lg p-3 text-emerald-300 max-h-40 overflow-y-auto">
                                    {JSON.stringify(JSON.parse(log.state_after), null, 2)}
                                  </pre>
                                </div>
                              </div>
                            ) : (
                              <span className="text-slate-500 font-mono text-[10px]">No state snapshots are captured for this log.</span>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------
            PAGE 8: EXPLAINABILITY REPORTS TAB
            ------------------------------------------------------------- */}
        {activeTab === 'explainability' && (
          <div className="space-y-8 animate-fadeIn">
            {/* Top account selector */}
            <div className="bg-slate-900/40 border border-white/5 rounded-xl p-4 flex justify-between items-center">
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Target Report Account</span>
                <h3 className="text-sm font-bold text-white font-title mt-0.5">WP-000042 (Sarah Jenkins)</h3>
              </div>
              <span className="badge badge-info text-[9px]">SHAP Attributions Computed</span>
            </div>

            {/* Waterfall attributions & Explanations */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Waterfall plot */}
              <div className="bg-slate-900/40 border border-white/5 rounded-xl p-6 flex flex-col justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white mb-2 uppercase tracking-wider font-title flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-cyan-400" />
                    <span>SHAP trigger attributions waterfall</span>
                  </h3>
                  <p className="text-xs text-slate-400 mb-6">Each bar represents the quantitative impact direction of a portfolio feature towards recommendation trigger.</p>
                </div>
                
                <div className="space-y-4">
                  {MOCK_XAI_REPORTS.shap_waterfall.map((item, idx) => {
                    const isPositive = item.impact >= 0;
                    const maxVal = 1.0;
                    const widthPct = Math.min(100, (Math.abs(item.impact) / maxVal) * 100);
                    return (
                      <div key={idx} className="grid grid-cols-3 items-center gap-4 text-xs">
                        <span className="font-semibold text-slate-300 truncate">{item.attribute}</span>
                        <div className="flex items-center gap-2">
                          <div className={`h-4.5 rounded ${isPositive ? 'bg-emerald-500/30 border border-emerald-500/20' : 'bg-red-500/30 border border-red-500/20'}`} style={{ width: `${widthPct}%` }}></div>
                        </div>
                        <span className={`font-bold font-mono text-right ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                          {isPositive ? '+' : ''}{item.impact.toFixed(2)}
                        </span>
                      </div>
                    );
                  })}
                </div>
                
                <div className="mt-8 pt-4 border-t border-slate-800 text-[10px] text-slate-500 font-semibold uppercase tracking-wider text-center">
                  Values sum to aggregate trigger score: 0.85
                </div>
              </div>

              {/* Explanations tab layout */}
              <div className="bg-slate-900/40 border border-white/5 rounded-xl p-6 flex flex-col justify-between">
                <div>
                  <div className="flex border-b border-white/5 pb-3 mb-6 gap-2">
                    {[
                      { id: 'client', name: 'Client report' },
                      { id: 'advisor', name: 'Advisor report' },
                      { id: 'compliance', name: 'Compliance report' }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        onClick={() => setXaiReportTab(tab.id)}
                        className={`px-3 py-1.5 rounded-lg text-[10px] font-bold tracking-wide transition-all ${
                          xaiReportTab === tab.id
                            ? 'bg-cyan-500/10 border border-cyan-500/20 text-cyan-400'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {tab.name}
                      </button>
                    ))}
                  </div>

                  <div className="space-y-4">
                    {xaiReportTab === 'client' && (
                      <div className="space-y-4 animate-fadeIn">
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">Jargon-Free Summary for client Review</h4>
                        <p className="text-xs text-slate-300 leading-relaxed font-sans">{MOCK_XAI_REPORTS.client_explanation}</p>
                      </div>
                    )}
                    {xaiReportTab === 'advisor' && (
                      <div className="space-y-4 animate-fadeIn">
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">Tactical advisor Analysis</h4>
                        <p className="text-xs text-slate-300 leading-relaxed font-sans">{MOCK_XAI_REPORTS.advisor_explanation}</p>
                      </div>
                    )}
                    {xaiReportTab === 'compliance' && (
                      <div className="space-y-4 animate-fadeIn">
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">Regulatory Compliance Validation</h4>
                        <p className="text-xs text-slate-300 leading-relaxed font-sans">{MOCK_XAI_REPORTS.compliance_explanation}</p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-8 pt-4 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500 font-semibold">
                  <span>Report ID: WPXAI-000042</span>
                  <span>Generated: 2026-06-08 17:28 UTC</span>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
