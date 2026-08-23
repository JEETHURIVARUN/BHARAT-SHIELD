import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import Controls from './components/Controls';
import DirectiveDossierModal from './components/DirectiveDossierModal';
import { motion, AnimatePresence } from 'framer-motion';

const PRICE_MOCK = { Brent_USD_bbl: 80.50, Dubai_USD_bbl: 79.20, WTI_USD_bbl: 77.80, JKM_USD_MMBtu: 14.25, TTF_USD_MMBtu: 11.80, HenryHub_USD_MMBtu: 2.85 };
const TICKER_ITEMS = [
  { label: 'Brent', key: 'Brent_USD_bbl', unit: '$/bbl', up: true },
  { label: 'Dubai', key: 'Dubai_USD_bbl', unit: '$/bbl', up: true },
  { label: 'WTI',   key: 'WTI_USD_bbl',   unit: '$/bbl', up: false },
  { label: 'JKM',   key: 'JKM_USD_MMBtu', unit: '$/MMBtu', up: true },
  { label: 'TTF',   key: 'TTF_USD_MMBtu', unit: '$/MMBtu', up: false },
  { label: 'Henry Hub', key: 'HenryHub_USD_MMBtu', unit: '$/MMBtu', up: false },
];

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  const [isLoading, setIsLoading]           = useState(false);
  const [simResult, setSimResult]           = useState(null);
  const [auditResult, setAuditResult]       = useState(null);
  const [activeTab, setActiveTab]           = useState('chat');
  const [intelData, setIntelData]           = useState(null);
  const [portwatchData, setPortwatchData]   = useState(null);
  const [isIntelLoading, setIsIntelLoading] = useState(false);
  const [isPortLoading, setIsPortLoading]   = useState(false);
  const [vessels, setVessels]               = useState([]);
  const [prices, setPrices]                 = useState(PRICE_MOCK);

  // ── Upgrade 5: State Hydration ─────────────────────────────────────────────
  const [snapshots, setSnapshots]           = useState([]);
  const [restoreToast, setRestoreToast]     = useState(null); // { snapshot_id, label, age_min }

  // Check for recent active session on initial mount
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/snapshots`)
      .then(r => r.json())
      .then(d => {
        if (d.snapshots?.length) {
          setSnapshots(d.snapshots);
          // If latest snapshot is younger than 30 minutes, offer restore toast
          if (d.latest_age_seconds !== null && d.latest_age_seconds < 1800) {
            const latest = d.snapshots[0];
            setRestoreToast({
              snapshot_id: latest.snapshot_id,
              label: latest.label,
              age_min: Math.max(1, Math.round(d.latest_age_seconds / 60)),
            });
          }
        }
      })
      .catch(() => {});
  }, []);

  const handleReplay = async (snapshotId) => {
    try {
      const r = await fetch(`${API_BASE}/api/v1/snapshots/${snapshotId}`);
      const d = await r.json();
      if (d.snapshot) {
        setSimResult(d.snapshot);
        setActiveTab('chat');
        setRestoreToast(null);
      }
    } catch(e) { console.error(e); }
  };

  // Fetch vessels on mount and auto-refresh with stateful MMSI merge
  useEffect(() => {
    const fetchVessels = () => {
      fetch(`${API_BASE}/api/v1/vessels`)
        .then(r => r.json())
        .then(d => {
          if (d.vessels && d.vessels.length > 0) {
            setVessels(prev => {
              const map = new Map(prev.map(v => [v.mmsi, v]));
              d.vessels.forEach(v => map.set(v.mmsi, { ...map.get(v.mmsi), ...v }));
              return Array.from(map.values());
            });
          }
        })
        .catch(() => {});
    };
    fetchVessels();
    const interval = setInterval(fetchVessels, 10000); // 10s poll
    return () => clearInterval(interval);
  }, []);

  // Fetch prices on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/prices`)
      .then(r => r.json())
      .then(d => { if (d.prices) setPrices(d.prices); })
      .catch(() => {});
  }, []);

  const handleChatSubmit = async (message) => {
    setIsLoading(true); setAuditResult(null);
    try {
      const res  = await fetch(`${API_BASE}/api/v1/chat-simulate`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ message })
      });
      const data = await res.json();
      setSimResult(data);
      // Refresh snapshots list after new simulation
      fetch(`${API_BASE}/api/v1/snapshots`)
        .then(r => r.json())
        .then(d => { if (d.snapshots?.length) setSnapshots(d.snapshots); })
        .catch(() => {});
    } catch(e) { console.error(e); }
    setIsLoading(false);
  };

  const handleAuthorize = async () => {
    const drawdown = simResult?.crude?.agent4_drawdown_plan || simResult?.gas?.agent4_gas_drawdown || {};
    try {
      const res = await fetch(`${API_BASE}/api/v1/generate-audit`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          authorization_token: 'AUTHORIZE_DIRECTIVE',
          deficit_mmt: simResult?.crude?.scenario_parsed?.deficit_mmt || simResult?.gas?.scenario_parsed?.deficit_mmscmd || 0,
          phase: 1, 
          drawdown_plan: drawdown,
          sim_result: simResult
        })
      });
      setAuditResult(await res.json());
    } catch(e) { console.error(e); }
  };

  const fetchIntel = async (query) => {
    setIsIntelLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/cloud-llm-intel`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ query: query || 'India crude oil Red Sea maritime attack' })
      });
      if (!r.ok) {
        console.error('Intel API error:', r.status, await r.text());
        setIsIntelLoading(false);
        return;
      }
      const d = await r.json();
      setIntelData({
        ...d.raw_intelligence,
        incident_chains: d.incident_chains || [],
      });
    } catch(e) { console.error('Intel fetch failed:', e); }
    setIsIntelLoading(false);
  };

  const fetchPortwatch = async (portId, metric = 'transit_calls') => {
    setIsPortLoading(true);
    try {
      const today = new Date();
      const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
      const end_date = today.toISOString().split('T')[0];
      const start_date = thirtyDaysAgo.toISOString().split('T')[0];

      const r = await fetch(`${API_BASE}/api/v1/portwatch`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ port_id: portId || 'Paradip', start_date, end_date, metric })
      });
      setPortwatchData((await r.json()).data);
    } catch(e) { console.error(e); }
    setIsPortLoading(false);
  };

  // KPI bar derives from crude or gas or both
  const crude = simResult?.crude;
  const gas   = simResult?.gas;
  const scri  = simResult?.supply_risk_index;
  const SCRI_COLOR = { LOW:'text-green-400', MODERATE:'text-yellow-400', HIGH:'text-orange-400', CRITICAL:'text-red-400' };
  const SCRI_BG    = { LOW:'bg-green-500/10 border-green-500/30', MODERATE:'bg-yellow-500/10 border-yellow-500/30', HIGH:'bg-orange-500/10 border-orange-500/30', CRITICAL:'bg-red-500/10 border-red-500/40' };

  const kpis = [
    { label:'Crude Deficit',   value: crude ? `${crude.scenario_parsed?.deficit_mmt} MMT`    : '—', color:'text-red-400'    },
    { label:'Gas Deficit',     value: gas   ? `${gas.scenario_parsed?.deficit_mmscmd} MMSCMD` : '—', color:'text-purple-400' },
    { label:'Best Crude Alt',  value: crude?.agent3_crude_alternatives?.[0]?.Crude_Name || '—', color:'text-yellow-400' },
    { label:'Best LNG Suppl.', value: gas?.agent3_lng_suppliers?.top_suppliers?.[0]?.name || '—', color:'text-cyan-400'   },
    { label:'Price Shock',     value: simResult?.price_shock ? `+$${simResult.price_shock.brent_shock_usd_bbl}/bbl` : '—', color:'text-orange-400' },
  ];

  return (
    <div className="flex h-full w-full bg-background text-white font-sans overflow-hidden">
      <Controls
        onChatSubmit={handleChatSubmit} isLoading={isLoading} simResult={simResult}
        onAuthorize={handleAuthorize} activeTab={activeTab} onTabChange={setActiveTab}
        onIntelSearch={fetchIntel} onPortwatchSearch={fetchPortwatch}
        intelData={intelData} portwatchData={portwatchData}
        isIntelLoading={isIntelLoading} isPortwatchLoading={isPortLoading}
        snapshots={snapshots} onReplay={handleReplay}
      />

      <div className="flex-1 p-4 flex flex-col gap-3 overflow-hidden">

        {/* Price Ticker */}
        <div className="flex items-center gap-2 flex-shrink-0 bg-panel border border-white/8 rounded-xl px-4 py-2 overflow-hidden">
          <span className="text-[9px] text-gray-600 uppercase tracking-widest mr-2 flex-shrink-0">LIVE PRICES</span>
          <div className="flex gap-5 overflow-x-auto scrollbar-hide">
            {TICKER_ITEMS.map(item => (
              <div key={item.key} className="flex items-center gap-1.5 flex-shrink-0">
                <span className="text-[10px] text-gray-500">{item.label}</span>
                <span className="text-[11px] font-mono font-bold text-white">{prices[item.key]}</span>
                <span className="text-[9px] text-gray-600">{item.unit}</span>
                <span className={`text-[10px] ${item.up ? 'text-green-400' : 'text-red-400'}`}>
                  {item.up ? '▲' : '▼'}
                </span>
              </div>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-3 flex-shrink-0">
            {/* National Reserve Health Indicator */}
            <div className="flex items-center gap-2 text-[10px] font-bold px-3 py-1 rounded-full border border-blue-500/30 bg-blue-500/10">
              <span className="text-gray-500 text-[9px] font-normal uppercase">Strategic Reserve Cover</span>
              <span className={`font-mono ${simResult?.crude?.agent4_drawdown_plan?.Total_Covered > 0 ? 'text-red-400' : 'text-blue-400'}`}>
                {simResult?.crude?.agent4_drawdown_plan?.Total_Covered 
                  ? (9.5 - (simResult.crude.agent4_drawdown_plan.Total_Covered / 0.7)).toFixed(1)
                  : "9.5"} Days
              </span>
            </div>
            
            {scri && (
              <div className={`flex items-center gap-2 text-[10px] font-bold px-3 py-1 rounded-full border ${SCRI_BG[scri.band] || 'bg-white/5 border-white/20'}`}>
                <span className="text-gray-500 text-[9px] font-normal">SCRI</span>
                <span className={SCRI_COLOR[scri.band] || 'text-white'}>{scri.score}/100</span>
                <span className={`text-[9px] ${SCRI_COLOR[scri.band] || 'text-white'}`}>{scri.band}</span>
              </div>
            )}
          </div>
        </div>

        {/* KPI Bar */}
        <div className="flex gap-2 flex-shrink-0">
          {kpis.map(k => (
            <div key={k.label} className="flex-1 bg-panel border border-white/8 rounded-xl px-3 py-2">
              <p className="text-[9px] text-gray-600 uppercase tracking-widest">{k.label}</p>
              <p className={`text-[12px] font-bold font-mono mt-0.5 ${k.color} truncate`}>{k.value}</p>
            </div>
          ))}
        </div>

        {/* Map */}
        <div className="flex-1 min-h-0">
          <Dashboard simulationData={simResult} vessels={vessels} onPortClick={null} />
        </div>
      </div>

      {/* Upgrade 5: State Hydration — Restore Last Session Toast */}
      <AnimatePresence>
        {restoreToast && !simResult && (
          <motion.div
            initial={{opacity:0, y:80}} animate={{opacity:1, y:0}} exit={{opacity:0, y:80}}
            transition={{type:'spring', damping:20}}
            className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-black/90 backdrop-blur border border-purple-500/50 p-4 rounded-2xl shadow-2xl z-50 w-[400px] flex items-center gap-4"
          >
            <div className="w-9 h-9 rounded-full bg-purple-500/20 border border-purple-500/40 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-purple-300 font-bold text-[11px]">Restore Last Session?</p>
              <p className="text-gray-400 text-[10px] mt-0.5 truncate">{restoreToast.label}</p>
              <p className="text-gray-600 text-[9px] mt-px">{restoreToast.age_min} min ago</p>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <button onClick={() => handleReplay(restoreToast.snapshot_id)}
                className="text-[10px] bg-purple-600 hover:bg-purple-500 text-white px-3 py-1.5 rounded-lg font-bold transition-all">
                Restore
              </button>
              <button onClick={() => setRestoreToast(null)}
                className="text-[10px] text-gray-500 hover:text-white px-2 py-1.5 transition-all">
                Dismiss
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sovereign Strategic Directive Dossier Modal */}
      <AnimatePresence>
        {auditResult && (
          <DirectiveDossierModal 
            auditResult={auditResult} 
            onClose={() => setAuditResult(null)} 
          />
        )}
      </AnimatePresence>
    </div>
  );
}
