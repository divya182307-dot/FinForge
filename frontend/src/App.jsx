import React, { useState, useEffect } from 'react';
import {
  getCompanies,
  getAllAudits,
  getDashboardSummary,
  getReviews,
  getAuditDetails,
  runAudit,
  submitReviewDecision
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [companies, setCompanies] = useState([]);
  const [audits, setAudits] = useState([]);
  const [selectedAuditId, setSelectedAuditId] = useState('');
  const [auditDetails, setAuditDetails] = useState(null);
  const [pendingReviews, setPendingReviews] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [comps, auds, sum, revs] = await Promise.all([
          getCompanies(),
          getAllAudits(),
          getDashboardSummary(),
          getReviews()
        ]);
        setCompanies(comps || []);
        setAudits(auds || []);
        setSummary(sum || null);
        setPendingReviews(revs || []);
        if (auds && auds.length > 0 && !selectedAuditId) {
          setSelectedAuditId(auds[0].audit_id);
        }
      } catch (e) {
        console.error("API error:", e);
      }
    }
    loadData();
  }, []);

  useEffect(() => {
    if (selectedAuditId) {
      getAuditDetails(selectedAuditId).then(setAuditDetails).catch(console.error);
    }
  }, [selectedAuditId]);

  return (
    <div className="flex h-screen bg-[#070b12] text-slate-100 font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-[#0b1120] border-r border-[#1e293b] flex flex-col justify-between">
        <div>
          <div className="px-6 py-5 border-b border-[#1e293b] flex items-center space-x-2">
            <span className="h-3 w-3 rounded-full bg-emerald-500 animate-pulse"></span>
            <h1 className="text-lg font-bold tracking-tight text-white">
              FINAUDIT<span className="text-teal-400">AI</span>
            </h1>
          </div>
          <nav className="p-3 space-y-1">
            {[
              { id: 'dashboard', label: 'Overview Dashboard', icon: '📊' },
              { id: 'companies', label: 'Company Selection', icon: '🏢' },
              { id: 'extraction', label: 'Financial Extraction', icon: '📑' },
              { id: 'validation', label: 'Validation Results', icon: '⚖️' },
              { id: 'reviews', label: 'Human Review Center', icon: '🛡️', badge: pendingReviews.length },
              { id: 'workflow', label: 'Workflow Monitoring', icon: '🔄' },
              { id: 'history', label: 'Audit History', icon: '📜' },
              { id: 'reports', label: 'Accuracy Reports', icon: '🎯' },
            ].map(item => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition ${
                  activeTab === item.id
                    ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-white'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </div>
                {item.badge > 0 && (
                  <span className="bg-amber-500/20 text-amber-300 text-xs px-2 py-0.5 rounded-full font-mono">
                    {item.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* Main View Area */}
      <main className="flex-1 overflow-y-auto p-8">
        <header className="mb-6 flex justify-between items-center border-b border-slate-800 pb-4">
          <div>
            <span className="text-xs font-mono text-slate-400 uppercase">Target Audit</span>
            <h2 className="text-lg font-bold text-white">
              {auditDetails ? `${auditDetails.company_name} (${auditDetails.ticker} ${auditDetails.period})` : 'Select Audit'}
            </h2>
          </div>
          <div className="text-xs font-mono px-3 py-1 bg-slate-800 rounded border border-slate-700">
            Audit ID: <strong className="text-teal-400">{selectedAuditId || 'None'}</strong>
          </div>
        </header>

        <div className="bg-[#0b1120] border border-[#1e293b] rounded-xl p-6">
          <p className="text-sm text-slate-300">
            FinAudit AI Active Dashboard. Running on view: <strong className="text-teal-400 uppercase">{activeTab}</strong>.
          </p>
        </div>
      </main>
    </div>
  );
}

