import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity, ShieldAlert, Zap, Lock, AlertTriangle, Ship, Database,
  MessageSquare, Globe, Radar, Search, Info, Flame, TrendingDown,
  TrendingUp, Clock, MapPin, ExternalLink, BarChart2, ChevronDown,
  ChevronUp, AlertCircle, Wind, Droplets, Calendar, Shield, CheckCircle2
} from 'lucide-react';

// ─── Utilities ────────────────────────────────────────────────────────────────
const SEV_STYLE = {
  CRITICAL: 'bg-red-500/15 text-red-400 border-red-500/40',
  HIGH:     'bg-orange-500/15 text-orange-400 border-orange-500/40',
  MEDIUM:   'bg-yellow-500/15 text-yellow-400 border-yellow-500/40',
  LOW:      'bg-green-500/15 text-green-400 border-green-500/40',
};

const RISK_COLOR = {
  LOW:      'text-green-400',
  MODERATE: 'text-yellow-400',
  HIGH:     'text-orange-400',
  CRITICAL: 'text-red-400',
};

// ─── Sub-Components ───────────────────────────────────────────────────────────
const Tooltip = ({ text, children }) => (
  <div className="group relative">
    {children}
    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-[#070b10] border border-white/20 text-[10px] p-2.5 rounded-xl opacity-0 group-hover:opacity-100 z-50 pointer-events-none shadow-2xl leading-relaxed text-gray-300 whitespace-pre-line transition-opacity">
      {text}
    </div>
  </div>
);

const MiniBar = ({ value, max, color = 'bg-accent' }) => {
  const pct = Math.min(100, Math.round((value / (max || 1)) * 100));
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-white/8 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[9px] font-mono text-gray-500 w-7 text-right">{pct}%</span>
    </div>
  );
};

const RiskGauge = ({ score, band }) => {
  const pct = Math.min(100, score);
  const color = band === 'LOW' ? '#22c55e' : band === 'MODERATE' ? '#eab308' : band === 'HIGH' ? '#f97316' : '#ef4444';
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-14 h-7 overflow-hidden">
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-14 h-14 rounded-full border-4 border-white/10" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-14 h-14 rounded-full border-4"
          style={{ borderColor: `${color}40`, borderTopColor: color,
            transform: `translateX(-50%) rotate(${(pct/100)*180 - 90}deg)`, transition: 'transform 1s ease-out' }} />
      </div>
      <span className="text-[11px] font-mono font-bold" style={{ color }}>{score}/100</span>
    </div>
  );
};

const SectionLabel = ({ icon: Icon, label, color = 'text-primary' }) => (
  <h3 className={`text-[10px] font-bold uppercase tracking-widest mb-3 flex items-center gap-2 ${color}`}>
    <Icon size={11}/>{label}
  </h3>
);

const RankBadge = ({ idx }) => (
  <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold flex-shrink-0 border
    ${idx===0?'bg-yellow-500/20 text-yellow-400 border-yellow-500/40':idx===1?'bg-gray-500/20 text-gray-300 border-gray-500/40':'bg-orange-900/20 text-orange-400 border-orange-800/40'}`}>
    {idx+1}
  </div>
);

const IncidentCard = ({ inc, idx }) => {
  const [open, setOpen] = useState(false);
  const Icon = inc.type === 'Attack' ? Flame : inc.type === 'Boarding' ? Ship : AlertCircle;
  return (
    <motion.div initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:idx*0.07}}
      className="bg-white/[0.04] border border-white/8 rounded-xl overflow-hidden hover:border-white/18 transition-all mb-2">
      <button className="w-full text-left p-4" onClick={() => setOpen(o => !o)}>
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <Icon size={13} className="text-orange-400" />
            <span className="text-xs font-bold text-white">{inc.type}</span>
          </div>
          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase ${SEV_STYLE[inc.severity] || SEV_STYLE.MEDIUM}`}>{inc.severity}</span>
        </div>
        <div className="flex items-center justify-between text-[10px] text-gray-500">
          <span className="flex items-center gap-1"><MapPin size={9}/>{inc.location}</span>
          <span>{open ? <ChevronUp size={11}/> : <ChevronDown size={11}/>}</span>
        </div>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{height:0,opacity:0}} animate={{height:'auto',opacity:1}} exit={{height:0,opacity:0}} className="overflow-hidden">
            <div className="px-4 pb-4 pt-3 border-t border-white/8">
              <p className="text-[11px] text-gray-300 leading-relaxed">{inc.raw_details}</p>
              <p className="text-[10px] text-accent mt-2 flex items-center gap-1"><MapPin size={9}/>Corridor: {inc.corridor}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// ── Upgrade 1: Escalation Chain Card ─────────────────────────────────────────
const EscalationChainCard = ({ chain, idx }) => {
  const [open, setOpen] = useState(false);
  const riskPct = Math.round(chain.decayed_risk * 100);
  const riskColor =
    riskPct >= 75 ? 'text-red-400 border-red-500/30 bg-red-500/10'
    : riskPct >= 50 ? 'text-orange-400 border-orange-500/30 bg-orange-500/10'
    : riskPct >= 25 ? 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10'
    : 'text-green-400 border-green-500/30 bg-green-500/10';
  return (
    <motion.div initial={{opacity:0,x:-10}} animate={{opacity:1,x:0}} transition={{delay:idx*0.08}}
      className="border border-white/10 rounded-xl overflow-hidden mb-2 hover:border-white/20 transition-all">
      <button className="w-full text-left p-3" onClick={() => setOpen(o => !o)}>
        <div className="flex items-center gap-2 mb-1">
          <div className={`text-[9px] font-bold px-2 py-px rounded-full border font-mono ${riskColor}`}>
            RISK {riskPct}%
          </div>
          {chain.is_escalating && (
            <span className="text-[8px] text-red-400 font-bold animate-pulse">▲ ESCALATING</span>
          )}
          <span className={`text-[8px] font-bold px-1.5 py-px rounded-full border uppercase ml-auto ${SEV_STYLE[chain.peak_severity] || SEV_STYLE.MEDIUM}`}>
            {chain.peak_severity}
          </span>
        </div>
        <p className="text-[11px] font-bold text-white truncate">{chain.corridor}</p>
        <div className="flex items-center gap-3 mt-1 text-[9px] text-gray-500">
          <span>{chain.event_count} linked events</span>
          {chain.time_span_hours > 0 && <span>over {chain.time_span_hours.toFixed(1)}h</span>}
          {open ? <ChevronUp size={9} className="ml-auto"/> : <ChevronDown size={9} className="ml-auto"/>}
        </div>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{height:0,opacity:0}} animate={{height:'auto',opacity:1}} exit={{height:0,opacity:0}} className="overflow-hidden">
            <div className="border-t border-white/8 px-3 pb-3 pt-2 flex flex-col gap-1.5">
              {chain.events?.map((ev, i) => (
                <div key={i} className="flex items-start gap-2 text-[10px]">
                  <span className={`mt-0.5 text-[8px] font-bold px-1.5 py-px rounded-full border flex-shrink-0 ${SEV_STYLE[ev.severity] || SEV_STYLE.MEDIUM}`}>{ev.source}</span>
                  <span className="text-gray-300 leading-relaxed">{ev.title}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// ── Upgrade 3: AII Badge ──────────────────────────────────────────────────────
const AIIBadge = ({ band, penalty, note }) => {
  const style = {
    NONE:     'text-green-400 border-green-500/30 bg-green-500/5',
    MILD:     'text-yellow-400 border-yellow-500/30 bg-yellow-500/5',
    MODERATE: 'text-orange-400 border-orange-500/30 bg-orange-500/5',
    SEVERE:   'text-red-400 border-red-500/40 bg-red-500/10',
  };
  if (!band || band === 'NONE') return (
    <span className="text-[8px] text-green-500/70 border border-green-500/20 px-1.5 py-px rounded-full font-mono">⚗ COMPATIBLE</span>
  );
  return (
    <Tooltip text={note || 'Asphaltene Instability Index assessment'}>
      <span className={`text-[8px] font-bold border px-1.5 py-px rounded-full font-mono cursor-help ${style[band] || style.MODERATE}`}>
        ⚗ AII {band} {penalty > 0 ? `+${penalty.toFixed(1)}` : ''}
      </span>
    </Tooltip>
  );
};

// ── Upgrade 4: Capacity Gap Alert ─────────────────────────────────────────────
const CapacityGapAlert = ({ drawdown }) => {
  const unmet = drawdown?.Unmet_Deficit_MMT || drawdown?.Unmet_Deficit_MMSCMD || 0;
  const covered = drawdown?.Total_Covered || drawdown?.Total_Covered_MMSCMD || 0;
  if (!unmet || unmet < 0.01) return null;
  return (
    <motion.div initial={{opacity:0,scale:0.95}} animate={{opacity:1,scale:1}}
      className="bg-red-500/10 border border-red-500/40 rounded-xl p-3 mb-3">
      <div className="flex items-center gap-2 mb-1.5">
        <AlertTriangle size={12} className="text-red-400 flex-shrink-0"/>
        <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">Physical Capacity Gap Detected</span>
      </div>
      <p className="text-[10px] text-gray-300 leading-relaxed">
        Strategic reserve capacity exhausted. Max drawdown computed: <span className="text-white font-bold">{covered.toFixed(2)}</span> MMT.
        Unmet deficit: <span className="text-red-300 font-bold">{unmet.toFixed(2)}</span> MMT — requires emergency spot procurement on open market.
      </p>
      <div className="flex gap-3 mt-2 text-[9px] text-gray-500">
        <span>Covered: <span className="text-emerald-400 font-mono">{covered.toFixed(2)}</span></span>
        <span>Unmet: <span className="text-red-400 font-mono">{unmet.toFixed(2)}</span></span>
        <span>Capacity: <span className="text-gray-300 font-mono">{drawdown?.Total_Capacity_MMT || drawdown?.Total_Capacity_MMSCMD || '—'}</span></span>
      </div>
    </motion.div>
  );
};

// ── Upgrade 5: War Games Archive ──────────────────────────────────────────────
const WarGamesArchive = ({ snapshots, onReplay }) => {
  if (!snapshots?.length) return null;
  const BAND_COLOR = { LOW:'text-green-400', MODERATE:'text-yellow-400', HIGH:'text-orange-400', CRITICAL:'text-red-400' };
  return (
    <div className="mb-4">
      <SectionLabel icon={Database} label="War Games Archive" color="text-purple-400"/>
      <div className="flex flex-col gap-1.5">
        {snapshots.map((s) => (
          <button key={s.snapshot_id} onClick={() => onReplay(s.snapshot_id)}
            className="w-full flex items-center gap-2 p-2.5 bg-white/[0.03] border border-white/8 rounded-xl hover:bg-purple-500/5 hover:border-purple-500/30 transition-all text-left">
            <Database size={10} className="text-purple-400 flex-shrink-0"/>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-gray-300 truncate">{s.label}</p>
              <p className="text-[9px] text-gray-600 mt-px">{new Date(s.created_at).toLocaleTimeString()} — {new Date(s.created_at).toLocaleDateString()}</p>
            </div>
            {s.scri_score && (
              <span className={`text-[9px] font-mono font-bold flex-shrink-0 ${BAND_COLOR[s.scri_band] || 'text-gray-400'}`}>
                {s.scri_score}
              </span>
            )}
            <span className="text-[8px] text-purple-400 font-bold flex-shrink-0">REPLAY</span>
          </button>
        ))}
      </div>
    </div>
  );
};

const RecoveryTimeline = ({ timeline }) => {
  if (!timeline?.length) return null;
  const PHASE_COLORS = {
    ALERT:    'bg-red-500',
    MOBILIZE: 'bg-orange-500',
    PROCURE:  'bg-yellow-500',
    TRANSIT:  'bg-blue-500',
    MONITOR:  'bg-cyan-500',
    RECEIPT:  'bg-emerald-500',
    NORMALIZE:'bg-green-400',
  };
  return (
    <div className="flex flex-col gap-0">
      {timeline.map((step, i) => (
        <div key={i} className="flex gap-3">
          {/* Left: day + line */}
          <div className="flex flex-col items-center flex-shrink-0 w-8">
            <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${PHASE_COLORS[step.phase] || 'bg-gray-500'}`} />
            {i < timeline.length - 1 && <div className="w-px flex-1 bg-white/10 my-1 min-h-[20px]" />}
          </div>
          {/* Right: content */}
          <div className="pb-4">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-[9px] font-mono font-bold text-gray-600">Day {step.day}</span>
              <span className={`text-[8px] font-bold px-1.5 py-px rounded-full text-black ${PHASE_COLORS[step.phase] || 'bg-gray-500'}`}>{step.phase}</span>
            </div>
            <p className="text-[10px] text-gray-400 leading-relaxed">{step.action}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

const Collapsible = ({ title, icon: Icon, color, count, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-white/8 rounded-xl overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/[0.03] transition-colors">
        <Icon size={12} className={color || 'text-gray-400'} />
        <span className={`text-[11px] font-bold uppercase tracking-wider flex-1 ${color || 'text-gray-300'}`}>{title}</span>
        {count != null && <span className="text-[9px] font-mono bg-white/10 rounded-full px-2 py-0.5">{count}</span>}
        {open ? <ChevronUp size={11} className="text-gray-600"/> : <ChevronDown size={11} className="text-gray-600"/>}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{height:0,opacity:0}} animate={{height:'auto',opacity:1}} exit={{height:0,opacity:0}} className="overflow-hidden">
            <div className="px-4 pb-4 border-t border-white/8 pt-3">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};



// ─── Main Controls ────────────────────────────────────────────────────────────
export default function Controls({
  onChatSubmit, isLoading, simResult, onAuthorize,
  activeTab, onTabChange,
  onIntelSearch, onPortwatchSearch,
  intelData, portwatchData, isIntelLoading, isPortwatchLoading,
  snapshots = [], onReplay,
}) {
  const [chatMsg, setChatMsg]   = useState('');
  const [intelQ, setIntelQ]     = useState('');
  const [portQ, setPortQ]       = useState('');
  const [portMetric, setPortMetric] = useState('transit_calls');
  const [whatIfEnabled, setWhatIfEnabled] = useState(false);
  const [whatIfOmcPct, setWhatIfOmcPct]   = useState(60);
  const logRef = useRef(null);

  const crude = simResult?.crude;
  const gas   = simResult?.gas;
  const critic = simResult?.agent6_critic;
  const scri   = simResult?.supply_risk_index;

  // Auto-scroll deliberation log
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [simResult?.deliberation_log]);

  const QUICK_SCENARIOS = [
    "Houthi missiles close Red Sea — 5 MMT crude deficit at Paradip",
    "Hormuz threat — 8 MMT crude at Jamnagar + 12 MMSCMD gas at Dahej",
    "Russia sanctions — 4 MMT Urals replacement needed at MRPL",
    "Qatar LNG supply cut — 15 MMSCMD deficit at Dahej and Hazira",
  ];

  return (
    <motion.div initial={{x:-440,opacity:0}} animate={{x:0,opacity:1}} transition={{type:'spring',damping:22}}
      className="w-[460px] bg-panel border-r border-white/5 h-full flex flex-col overflow-hidden">

      {/* Header */}
      <div className="px-6 pt-5 pb-0 flex-shrink-0">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 bg-primary/10 rounded-xl text-primary border border-primary/20 shadow-[0_0_20px_rgba(16,185,129,0.12)]">
            <ShieldAlert size={21}/>
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-widest text-white">BHARAT-SHIELD</h1>
            <p className="text-[9px] text-gray-500 uppercase tracking-widest">Strategic Command Center · v3.0</p>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"/>
            <span className="text-[9px] text-emerald-400 uppercase tracking-wider">Live</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/8">
          {[
            {id:'chat',     label:'Simulation',  icon:Activity},
            {id:'intel',    label:'Intel Feed',   icon:Radar},
            {id:'portwatch',label:'PortWatch',    icon:BarChart2},
          ].map(({id,label,icon:Icon}) => (
            <button key={id} onClick={() => onTabChange(id)}
              className={`flex items-center gap-1.5 pb-3 px-3 text-[11px] font-semibold border-b-2 uppercase tracking-wider transition-all flex-1 justify-center
                ${activeTab===id ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
              <Icon size={11}/>{label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-hide px-5 py-5 flex flex-col gap-5">

        {/* ── SIMULATION ─────────────────────────────── */}
        {activeTab === 'chat' && (
          <motion.div key="chat" initial={{opacity:0}} animate={{opacity:1}} className="flex flex-col gap-4">

            {/* Quick scenarios */}
            {!simResult && !isLoading && (
              <div>
                <p className="text-[9px] text-gray-600 uppercase tracking-widest mb-2">Quick Scenarios</p>
                <div className="flex flex-col gap-1.5">
                  {QUICK_SCENARIOS.map(s => (
                    <button key={s} onClick={() => { setChatMsg(s); }}
                      className="text-left text-[10px] text-gray-500 hover:text-gray-200 bg-white/[0.02] hover:bg-white/[0.06] border border-white/8 hover:border-white/20 rounded-lg px-3 py-2 transition-all">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

                {/* Upgrade 5: War Games Archive */}
                <WarGamesArchive snapshots={snapshots} onReplay={onReplay}/>

                {/* Input */}
            <div className="bg-white/[0.03] rounded-2xl p-5 border border-white/8">
              <SectionLabel icon={MessageSquare} label="Dynamic Scenario Input" color="text-accent"/>
              <textarea
                className="w-full bg-black/40 border border-white/8 rounded-xl p-3 text-[12px] text-white placeholder-gray-600 focus:outline-none focus:border-accent/60 min-h-[100px] resize-none leading-relaxed mb-3"
                placeholder={"Describe any energy crisis — crude, gas, or both…\n\nE.g. Houthi attacks blocked Red Sea. 5 MMT crude deficit at Paradip and 8 MMSCMD gas shortage at Dahej."}
                value={chatMsg} onChange={e => setChatMsg(e.target.value)}
                onKeyDown={e => { if (e.ctrlKey && e.key === 'Enter') { onChatSubmit(chatMsg); } }}
              />
              <button onClick={() => { onChatSubmit(chatMsg); setChatMsg(''); }}
                disabled={isLoading || !chatMsg.trim()}
                className="w-full bg-accent hover:bg-blue-400 text-white font-semibold py-2.5 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-40 hover:shadow-[0_0_20px_rgba(59,130,246,0.3)] text-sm">
                {isLoading
                  ? <><Activity size={14} className="animate-spin"/>Running Autonomous Agent Mesh (NETRA, MARG, RASAYAN, KOSH, KAUTILYA, CHAKRA)…</>
                  : <><Zap size={14}/>Execute Directive</>}
              </button>
              {chatMsg && <p className="text-[9px] text-gray-600 text-center mt-2">Ctrl+Enter to submit</p>}
            </div>

            {simResult && (
              <motion.div initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} className="flex flex-col gap-4">

                {/* Deliberation Terminal */}
                {simResult.deliberation_log?.length > 0 && (
                  <div className="bg-black/90 border border-gray-700/60 rounded-xl overflow-hidden">
                    <div className="flex items-center gap-2 px-3 py-1.5 border-b border-gray-700/60">
                      <div className="flex gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-red-500/70"/>
                        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70"/>
                        <div className="w-2.5 h-2.5 rounded-full bg-green-500/70"/>
                      </div>
                      <span className="text-[9px] text-gray-500 font-mono flex-1 text-center">SOVEREIGN AGENT DELIBERATION TERMINAL</span>
                    </div>
                    <div ref={logRef} className="p-3 font-mono text-[9.5px] text-green-400 max-h-36 overflow-y-auto scrollbar-hide">
                      {simResult.deliberation_log.map((log, i) => {
                        const agent = log.match(/\[(.*?)\]/)?.[1] || '';
                        const msg   = log.replace(/\[.*?\]\s*/, '');
                        const color = (agent.includes('CHAKRA') || agent.includes('Critic')) ? 'text-red-400' :
                                      (agent.includes('NETRA') || agent.includes('Sentinel')) ? 'text-yellow-400' :
                                      (agent.includes('RASAYAN') || agent.includes('Trader')) ? 'text-cyan-400' :
                                      (agent.includes('KOSH') || agent.includes('Governor')) ? 'text-emerald-400' :
                                      (agent.includes('KAUTILYA') || agent.includes('War Room')) ? 'text-purple-400' : 
                                      (agent.includes('MARG') || agent.includes('Quant')) ? 'text-orange-400' : 'text-blue-400';
                        return (
                          <p key={i} className="mb-1 leading-relaxed">
                            <span className="text-gray-600">{String(i+1).padStart(2,'0')} </span>
                            <span className={`font-bold ${color}`}>[{agent}]</span>
                            <span className="text-gray-300"> {msg}</span>
                          </p>
                        );
                      })}
                      <span className="animate-pulse text-green-400">█</span>
                    </div>
                  </div>
                )}

                {/* Supply Risk Index */}
                {scri && (
                  <div className={`rounded-2xl p-4 border ${
                    scri.band === 'CRITICAL' ? 'bg-red-950/20 border-red-500/40' :
                    scri.band === 'HIGH'     ? 'bg-orange-950/20 border-orange-500/30' :
                    scri.band === 'MODERATE' ? 'bg-yellow-950/20 border-yellow-500/30' :
                                               'bg-emerald-950/20 border-emerald-500/30'}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <SectionLabel icon={Shield} label="Supply Chain Risk Index" color={`${RISK_COLOR[scri.band]}`}/>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1">
                          {Object.entries(scri.breakdown).map(([k, v]) => (
                            <div key={k} className="text-[10px]">
                              <span className="text-gray-600">{k.replace(/_/g,' ')}: </span>
                              <span className="font-mono font-bold text-gray-300">{v}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <RiskGauge score={scri.score} band={scri.band}/>
                    </div>
                  </div>
                )}

                {/* Price Shock */}
                {simResult.price_shock && (
                  <div className="bg-orange-950/20 border border-orange-500/25 rounded-2xl p-4">
                    <div className="flex items-start justify-between">
                      <SectionLabel icon={TrendingUp} label="Price Shock Estimate" color="text-orange-400"/>
                      <Tooltip text={`Source: VECM Statistical Math Model\nConfidence: ${simResult.price_shock.confidence_interval}`}>
                        <span className="text-[9px] text-gray-600 border border-white/10 rounded-full px-2 py-0.5 cursor-help hover:text-gray-300 transition-colors">ⓘ Source</span>
                      </Tooltip>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        {l:'Base Brent',     v:`$${simResult.price_shock.base_brent_usd_bbl}/bbl`,    c:'text-gray-300'},
                        {l:'Stressed Brent', v:`$${simResult.price_shock.stressed_brent_usd_bbl}/bbl`, c:'text-orange-400 font-bold'},
                        {l:'Brent Shock',    v:`+$${simResult.price_shock.brent_shock_usd_bbl}/bbl`,   c:'text-red-400'},
                        {l:'JKM Shock',      v:`+$${simResult.price_shock.jkm_shock_usd_mmbtu}/MMBtu`, c:'text-purple-400'},
                      ].map(row => (
                        <div key={row.l} className="bg-black/20 rounded-xl p-2.5">
                          <p className="text-[9px] text-gray-500 uppercase tracking-wider">{row.l}</p>
                          <p className={`text-[13px] font-mono font-bold mt-0.5 ${row.c}`}>{row.v}</p>
                        </div>
                      ))}
                    </div>
                    {simResult.price_shock.macroeconomic_impact && (
                      <div className="mt-3 pt-3 border-t border-orange-500/20">
                        <div className="flex justify-between items-center mb-1.5">
                          <p className="text-[10px] text-orange-400/80 font-bold uppercase tracking-wider">Macroeconomic Impact (India)</p>
                          <Tooltip text={`Source: ${simResult.price_shock.macroeconomic_impact.provenance}`}>
                            <span className="text-[8px] text-gray-500 border border-white/5 rounded px-1.5 cursor-help">ⓘ</span>
                          </Tooltip>
                        </div>
                        <div className="flex gap-4">
                          <div className="flex-1">
                            <p className="text-[9px] text-gray-500">GDP Growth</p>
                            <p className="text-[11px] font-mono font-bold text-red-400">
                              {simResult.price_shock.macroeconomic_impact.gdp_growth_impact_pct}%
                            </p>
                          </div>
                          <div className="flex-1">
                            <p className="text-[9px] text-gray-500">Inflation</p>
                            <p className="text-[11px] font-mono font-bold text-orange-400">
                              +{simResult.price_shock.macroeconomic_impact.inflation_impact_pct}%
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* CRUDE Results */}
                {crude && (
                  <Collapsible title="Crude Oil Response" icon={Droplets} color="text-yellow-400"
                    count={`${crude.scenario_parsed?.deficit_mmt} MMT`} defaultOpen={true}>
                    <div className="flex flex-col gap-4">

                      {/* Infrastructure */}
                      <div>
                        <div className="flex items-start justify-between">
                          <SectionLabel icon={AlertTriangle} label="MARG · Port & Pipeline Infrastructure" color="text-orange-400"/>
                          <Tooltip text={`Source: ${crude.agent2_infrastructure_check?.provenance}`}>
                            <span className="text-[9px] text-gray-600 border border-white/10 rounded-full px-2 py-0.5 cursor-help hover:text-gray-300 transition-colors -mt-1">ⓘ</span>
                          </Tooltip>
                        </div>
                        {[
                          {l:'Port',         v: crude.agent2_infrastructure_check?.port,              c:'text-white'},
                          {l:'Requested',    v:`${crude.agent2_infrastructure_check?.requested_volume} MMT/d`, c:'text-red-400'},
                          {l:'SPM Cap',      v:`${crude.agent2_infrastructure_check?.spm_capacity} MMT/d`,     c:'text-green-400'},
                          {l:'Pipeline Cap', v:`${crude.agent2_infrastructure_check?.pipeline_capacity} MMT/d`,c:'text-blue-400'},
                        ].map(r => (
                          <div key={r.l} className="flex justify-between text-[11px] mb-1">
                            <span className="text-gray-500">{r.l}</span>
                            <span className={`font-mono font-bold ${r.c}`}>{r.v}</span>
                          </div>
                        ))}
                        {crude.agent2_infrastructure_check?.is_bottlenecked && (
                          <div className="mt-2 bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-[10px] text-red-400">
                            ⚠ {crude.agent2_infrastructure_check?.reasons?.join(' · ')}
                          </div>
                        )}
                        {crude.rerouting && (
                          <Tooltip text={`Source: ${crude.rerouting.provenance}\nConfidence: ${crude.rerouting.confidence}`}>
                            <div className="mt-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-2 text-[10px] text-yellow-300 cursor-help">
                              🔁 Cape rerouting: +{crude.rerouting.extra_days} days · +{(crude.rerouting.extra_nm||0).toLocaleString()} nm · ${((crude.rerouting.extra_cost_usd||0)/1e6).toFixed(1)}M
                              <span className="ml-2 text-yellow-500/60">({crude.rerouting.confidence})</span>
                            </div>
                          </Tooltip>
                        )}
                      </div>

                      {/* Run-Rate Impact */}
                      {crude.run_rate_impact && (
                        <div>
                          <SectionLabel icon={Activity} label="Refinery Run-Rate Impact" color="text-red-400"/>
                          <div className="bg-black/20 rounded-xl p-3 space-y-1.5">
                            <div className="flex justify-between text-[11px]">
                              <span className="text-gray-500">{crude.run_rate_impact.refinery} ({crude.run_rate_impact.operator})</span>
                              <span className="text-white font-mono">{crude.run_rate_impact.daily_capacity_mmt} MMT/d capacity</span>
                            </div>
                            <div className="flex justify-between text-[11px]">
                              <span className="text-gray-500">Forward buffer</span>
                              <span className="text-emerald-400 font-mono">{crude.run_rate_impact.buffer_days} days ({crude.run_rate_impact.forward_buffer_mmt} MMT)</span>
                            </div>
                            {crude.run_rate_impact.days_before_rationing && (
                              <div className="mt-2 bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-[10px] text-red-300">
                                ⏱ Rationing begins in <span className="font-bold">{crude.run_rate_impact.days_before_rationing} days</span> without emergency drawdown.
                                {crude.run_rate_impact.run_rate_cut_pct > 0 && ` Estimated run-rate cut: ${crude.run_rate_impact.run_rate_cut_pct}%.`}
                              </div>
                            )}
                            {crude.run_rate_impact.products_at_risk?.length > 0 && (
                              <div className="mt-2 space-y-1">
                                {crude.run_rate_impact.products_at_risk.map((p, i) => (
                                  <p key={i} className="text-[10px] text-orange-300 flex items-start gap-1">
                                    <span className="text-orange-500 mt-0.5 flex-shrink-0">→</span>{p}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Replacement Crudes */}
                      <div>
                        <SectionLabel icon={Ship} label="RASAYAN · Replacement Crudes" color="text-blue-400"/>
                        {crude.agent3_crude_alternatives?.map((c, i) => (
                          <div key={i} className="flex items-center gap-2 bg-black/25 rounded-xl p-2.5 mb-2">
                            <RankBadge idx={i}/>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap mb-1">
                                <p className="text-[12px] font-semibold text-white">{c.Crude_Name}</p>
                                <AIIBadge band={c.AII_Risk_Band} penalty={c.AII_Penalty} note={c.AII_Note}/>
                                {c.Route_Risk !== undefined && (
                                  <span className={`text-[9px] px-1.5 py-0.5 rounded border ${c.Route_Risk > 0.5 ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-green-500/10 border-green-500/30 text-green-400'}`}>
                                    Route Risk: {(c.Route_Risk * 100).toFixed(0)}%
                                  </span>
                                )}
                              </div>
                              <MiniBar value={10-Math.min(c.Viability_Score,10)} max={10}
                                color={i===0?'bg-yellow-400':i===1?'bg-gray-400':'bg-orange-600'}/>
                            </div>
                            <span className="text-[11px] font-mono text-gray-400">
                              {c.Viability_Score?.toFixed(2)}
                            </span>
                          </div>
                        ))}
                      </div>

                      {/* ISPRL Drawdown with What-If */}
                      <div>
                        {/* Upgrade 4: Capacity Gap Alert */}
                        <CapacityGapAlert drawdown={crude.agent4_drawdown_plan}/>
                        <div className="flex items-center justify-between mb-3">
                          <SectionLabel icon={Database} label="KOSH · Strategic Reserve Drawdown" color="text-emerald-400"/>
                          <button onClick={() => setWhatIfEnabled(!whatIfEnabled)}
                            className={`text-[9px] border px-2 py-0.5 rounded-full transition-all ${whatIfEnabled ? 'bg-primary/20 border-primary text-primary' : 'bg-white/5 border-white/20 text-gray-500 hover:text-white'}`}>
                            {whatIfEnabled ? 'What-If: ON' : 'What-If'}
                          </button>
                        </div>
                        {whatIfEnabled && (
                          <div className="mb-3 bg-primary/10 border border-primary/20 p-3 rounded-xl">
                            <p className="text-[10px] text-primary mb-2 flex justify-between">
                              <span>Adjust OMC / ISPRL split</span>
                              <span className="font-mono">OMC: {whatIfOmcPct}% / ISPRL: {100-whatIfOmcPct}%</span>
                            </p>
                            <input type="range" min="0" max="100" value={whatIfOmcPct}
                              onChange={e => setWhatIfOmcPct(parseInt(e.target.value))}
                              className="w-full accent-primary h-1 bg-white/20 rounded-lg cursor-pointer"/>
                          </div>
                        )}
                        <div className="grid grid-cols-2 gap-2">
                          <div className="bg-black/30 p-2.5 rounded-xl border border-white/5 text-center">
                            <p className="text-gray-500 text-[9px] uppercase">ISPRL Caverns</p>
                            <p className="text-emerald-400 font-mono font-bold text-sm mt-0.5">
                              {whatIfEnabled
                                ? (crude.scenario_parsed.deficit_mmt * (1 - whatIfOmcPct/100)).toFixed(2)
                                : (crude.agent4_drawdown_plan?.Total_Covered * 0.4 || 1.8).toFixed(2)} MMT
                            </p>
                            <p className="text-[9px] text-gray-600">Padur · Mangaluru · Vizag</p>
                          </div>
                          <div className="bg-black/30 p-2.5 rounded-xl border border-white/5 text-center">
                            <p className="text-gray-500 text-[9px] uppercase">OMC Commercial</p>
                            <p className="text-blue-400 font-mono font-bold text-sm mt-0.5">
                              {whatIfEnabled
                                ? (crude.scenario_parsed.deficit_mmt * (whatIfOmcPct/100)).toFixed(2)
                                : (crude.agent4_drawdown_plan?.Total_Covered * 0.6 || 2.7).toFixed(2)} MMT
                            </p>
                            <p className="text-[9px] text-gray-600">IOCL · BPCL · HPCL</p>
                          </div>
                        </div>
                      </div>

                      {/* Recovery Timeline */}
                      {crude.recovery_timeline && (
                        <Collapsible title="Recovery Timeline" icon={Calendar} color="text-amber-400"
                          count={`${crude.recovery_timeline.length} steps`}>
                          <RecoveryTimeline timeline={crude.recovery_timeline}/>
                        </Collapsible>
                      )}
                    </div>
                  </Collapsible>
                )}

                {/* GAS Results */}
                {gas && (
                  <Collapsible title={`Natural Gas / LNG Disruption · ${gas.scenario_parsed?.deficit_mmscmd} MMSCMD`}
                    icon={Flame} color="text-purple-400" defaultOpen={true}>
                    <div className="p-4 space-y-4">

                      {/* Scenario Summary */}
                      <div className="bg-purple-950/20 border border-purple-500/20 rounded-xl p-3">
                        <div className="grid grid-cols-3 gap-2 text-center text-[10px]">
                          <div><p className="text-gray-500 text-[9px]">Deficit</p><p className="text-purple-300 font-mono font-bold">{gas.scenario_parsed?.deficit_mmscmd} MMSCMD</p></div>
                          <div><p className="text-gray-500 text-[9px]">Terminal</p><p className="text-white font-semibold">{gas.scenario_parsed?.terminal}</p></div>
                          <div><p className="text-gray-500 text-[9px]">Distance</p><p className="text-cyan-300 font-mono">{gas.scenario_parsed?.distance_nm?.toLocaleString()} NM</p></div>
                        </div>
                        {gas.rerouting && (
                          <Tooltip text={`Source: ${gas.rerouting.provenance}\nConfidence: ${gas.rerouting.confidence}`}>
                            <div className="mt-2 bg-purple-500/10 border border-purple-500/30 rounded-lg p-2 text-[10px] text-purple-300 cursor-help">
                              🔁 LNG rerouting: +{gas.rerouting.extra_days} days · ${((gas.rerouting.extra_cost_usd||0)/1e6).toFixed(1)}M/cargo
                            </div>
                          </Tooltip>
                        )}
                      </div>

                      <div>
                        <SectionLabel icon={Ship} label="RASAYAN · LNG Suppliers" color="text-cyan-400"/>
                        {gas.agent3_lng_suppliers?.top_suppliers?.map((s,i) => (
                          <div key={i} className="flex items-center gap-2 bg-black/25 rounded-xl p-2.5 mb-2">
                            <RankBadge idx={i}/>
                            <div className="flex-1 min-w-0">
                              <p className="text-[12px] font-semibold text-white truncate">{s.name}</p>
                              <p className="text-[10px] text-gray-500">{s.country} · {s.contract}</p>
                            </div>
                            <div className="text-right flex-shrink-0">
                              <p className="text-[10px] font-mono text-cyan-400">CH₄ {s.methane_pct}%</p>
                              <p className="text-[9px] text-gray-500">Score {s.Viability_Score?.toFixed(2)}</p>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div>
                        <SectionLabel icon={Database} label="KOSH · Regasification Plan" color="text-emerald-400"/>
                        {gas.agent4_regasification_plan?.terminal_plan?.map((t,i) => (
                          <div key={i} className="mb-1.5">
                            <div className="flex justify-between text-[11px]">
                              <span className="text-gray-400">{t.terminal}</span>
                              <span className="font-mono text-purple-400 font-bold">{t.allocated_mmscmd} MMSCMD</span>
                            </div>
                            <MiniBar value={t.allocated_mmscmd} max={gas.scenario_parsed?.deficit_mmscmd||10} color="bg-purple-500"/>
                            <p className="text-[9px] text-gray-600 mt-0.5">→ {t.pipeline} · Utilization: {t.new_utilization_pct}%</p>
                          </div>
                        ))}
                        {(gas.agent4_regasification_plan?.shortfall_mmscmd||0) > 0 && (
                          <div className="mt-2 bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-[10px] text-red-400">
                            ⚠ Unmet shortfall: {gas.agent4_regasification_plan?.shortfall_mmscmd} MMSCMD — domestic field ramp-up required
                          </div>
                        )}
                      </div>

                      {gas.prices && (
                        <div className="bg-black/20 rounded-xl p-3">
                          <SectionLabel icon={TrendingUp} label="Current LNG Benchmarks" color="text-purple-300"/>
                          <div className="flex gap-4 text-[11px]">
                            <div><p className="text-gray-500 text-[9px]">JKM (Asia)</p><p className="text-purple-300 font-mono font-bold">${gas.prices.JKM_USD_MMBtu}/MMBtu</p></div>
                            <div><p className="text-gray-500 text-[9px]">TTF (EU)</p><p className="text-blue-300 font-mono font-bold">${gas.prices.TTF_USD_MMBtu}/MMBtu</p></div>
                            <div><p className="text-gray-500 text-[9px]">Henry Hub</p><p className="text-green-300 font-mono font-bold">${gas.prices.HenryHub_USD_MMBtu}/MMBtu</p></div>
                          </div>
                        </div>
                      )}

                      {gas.recovery_timeline && (
                        <Collapsible title="Recovery Timeline" icon={Calendar} color="text-cyan-400"
                          count={`${gas.recovery_timeline.length} steps`}>
                          <RecoveryTimeline timeline={gas.recovery_timeline}/>
                        </Collapsible>
                      )}
                    </div>
                  </Collapsible>
                )}

                {/* Agent 6 – Red Team Assessment */}
                {critic && (critic.warnings?.length > 0 || critic.historical_analog) && (
                  <div className="bg-red-950/15 border border-red-500/35 rounded-2xl p-4">
                    <SectionLabel icon={ShieldAlert} label="CHAKRA · Red Team Vulnerability Assessment" color="text-red-400"/>

                    {critic.warnings?.map((w, i) => (
                      <div key={i} className="flex gap-3 bg-black/30 p-3 rounded-xl border border-red-500/20 mb-2">
                        <AlertTriangle size={14} className="text-red-400 flex-shrink-0 mt-0.5"/>
                        <div>
                          <p className="text-[10px] font-bold text-red-400 uppercase tracking-widest mb-1">
                            {w.type.replace(/_/g,' ')}
                            <span className={`ml-2 text-[8px] ${SEV_STYLE[w.severity]} px-1.5 py-0.5 rounded-full border`}>{w.severity}</span>
                          </p>
                          <p className="text-[10px] text-gray-300 leading-relaxed">{w.message}</p>
                        </div>
                      </div>
                    ))}

                    {critic.historical_analog && (
                      <div className="flex gap-3 bg-blue-900/15 p-3 rounded-xl border border-blue-500/25 mt-3">
                        <Database size={14} className="text-blue-400 flex-shrink-0 mt-0.5"/>
                        <div>
                          <p className="text-[10px] font-bold text-blue-400 mb-1">
                            Historical Analog: {critic.historical_analog.event}
                            <span className="ml-2 text-[9px] font-mono text-blue-300">{critic.historical_analog.similarity_score}% match</span>
                          </p>
                          <div className="flex gap-4 text-[10px] text-gray-400 mb-1.5">
                            {critic.historical_analog.brent_spike_usd > 0 && <span>Brent spike: <span className="text-red-300 font-mono">+${critic.historical_analog.brent_spike_usd}/bbl</span></span>}
                            {critic.historical_analog.transit_delay_days > 0 && <span>Delay: <span className="text-yellow-300 font-mono">+{critic.historical_analog.transit_delay_days}d</span></span>}
                            {critic.historical_analog.duration_days && <span>Duration: <span className="text-gray-300 font-mono">{critic.historical_analog.duration_days}d</span></span>}
                          </div>
                          <p className="text-[10px] text-gray-300 leading-relaxed">{critic.historical_analog.outcome}</p>
                        </div>
                      </div>
                    )}

                    {(!critic.warnings || critic.warnings.length === 0) && !critic.historical_analog && (
                      <div className="flex items-center gap-2 text-emerald-400 text-[11px]">
                        <CheckCircle2 size={14}/> Plan verified — no critical vulnerabilities detected.
                      </div>
                    )}
                  </div>
                )}

                {/* Authorize */}
                {(crude || gas) && (
                  <div className="pb-4">
                    {critic?.warnings?.some(w => w.severity === 'CRITICAL') && (
                      <div className="mb-3 bg-red-500/10 border border-red-500/40 rounded-xl p-3 text-[10px] text-red-300 text-center">
                        ⚠ Critical vulnerabilities detected. Review CHAKRA assessment before authorizing.
                      </div>
                    )}
                    <p className="text-[10px] text-gray-600 text-center mb-3 px-2 leading-relaxed">
                      Authorization generates a <span className="text-gray-400">SHA-256 signed JSON payload</span> and a downloadable <span className="text-gray-400">CSV execution ledger</span> via <span className="text-purple-400 font-semibold">KAUTILYA</span>.
                    </p>
                    <button onClick={onAuthorize}
                      className="w-full bg-danger hover:bg-red-400 text-white font-bold py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(239,68,68,0.2)] hover:shadow-[0_0_28px_rgba(239,68,68,0.4)] text-sm">
                      <Lock size={15}/>AUTHORIZE DIRECTIVE
                    </button>
                  </div>
                )}
              </motion.div>
            )}
          </motion.div>
        )}

        {/* ── INTEL ─────────────────────────────────────── */}
        {activeTab === 'intel' && (
          <motion.div key="intel" initial={{opacity:0}} animate={{opacity:1}} className="flex flex-col gap-4">
            <form onSubmit={e => { e.preventDefault(); onIntelSearch(intelQ); }} className="relative">
              <Radar size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600"/>
              <input value={intelQ} onChange={e => setIntelQ(e.target.value)}
                placeholder="Search global maritime intelligence…"
                className="w-full bg-black/40 border border-white/10 rounded-xl py-2.5 pl-9 pr-10 text-[12px] text-white placeholder-gray-600 focus:outline-none focus:border-primary/60"/>
              <button type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"><Search size={13}/></button>
            </form>

            {/* Quick tags */}
            {!intelData && !isIntelLoading && (
              <div className="flex flex-wrap gap-2">
                {['Red Sea','Houthi','Suez Canal','Hormuz','Qatar LNG','VLCC Attack'].map(s => (
                  <button key={s} onClick={() => { setIntelQ(s); onIntelSearch(s); }}
                    className="text-[10px] bg-white/5 hover:bg-white/10 border border-white/10 text-gray-400 px-3 py-1.5 rounded-full transition-all">
                    {s}
                  </button>
                ))}
              </div>
            )}

            {isIntelLoading ? (
              <div className="flex flex-col items-center py-12 gap-3">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"/>
                <p className="text-xs text-gray-500 animate-pulse">Scanning global intelligence feeds…</p>
              </div>
            ) : (
              <>
                {intelData?.UKMTO?.length > 0 && (
                  <div>
                    {/* Upgrade 1: Escalation Chains */}
                    {intelData.incident_chains?.length > 0 && (
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-3">
                          <Activity size={11} className="text-red-400"/>
                          <span className="text-[10px] text-red-400 uppercase tracking-widest font-bold">Escalation Chains</span>
                          <span className="ml-auto bg-red-500/15 text-red-400 text-[9px] font-bold px-2 py-0.5 rounded-full border border-red-500/30">{intelData.incident_chains.length}</span>
                        </div>
                        {intelData.incident_chains.map((chain, i) => (
                          <EscalationChainCard key={chain.chain_id} chain={chain} idx={i}/>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle size={11} className="text-orange-400"/>
                      <span className="text-[10px] text-orange-400 uppercase tracking-widest font-bold">Maritime Security Alerts</span>
                      <span className="ml-auto bg-orange-500/15 text-orange-400 text-[9px] font-bold px-2 py-0.5 rounded-full border border-orange-500/30">{intelData.UKMTO.length}</span>
                    </div>
                    {intelData.UKMTO.map((inc, i) => <IncidentCard key={i} inc={inc} idx={i}/>)}
                  </div>
                )}
                {intelData?.GDELT?.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-3 mt-2">
                      <Globe size={11} className="text-primary"/>
                      <span className="text-[10px] text-primary uppercase tracking-widest font-bold">GDELT Global Signals</span>
                      <span className="ml-auto bg-primary/15 text-primary text-[9px] font-bold px-2 py-0.5 rounded-full border border-primary/30">{intelData.GDELT.length}</span>
                    </div>
                    {intelData.GDELT.map((art, i) => (
                      <motion.a key={i} href={art.url} target="_blank" rel="noreferrer"
                        initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:i*0.06}}
                        className="block bg-white/[0.04] border border-white/8 rounded-xl p-4 hover:border-accent/40 hover:bg-accent/5 transition-all group mb-2">
                        <p className="text-[11px] text-white group-hover:text-blue-300 transition-colors leading-snug font-medium">{art.title}</p>
                        <div className="flex items-center gap-3 text-[10px] text-gray-500 mt-2">
                          <span className="flex items-center gap-1"><Globe size={9}/>{art.domain||art.sourcecountry}</span>
                          {art.seendate && <span>{art.seendate}</span>}
                          {art.tone && (
                            <span className={`ml-auto font-mono font-bold flex items-center gap-0.5 ${parseFloat(art.tone)<0?'text-red-400':'text-green-400'}`}>
                              {parseFloat(art.tone)<0?<TrendingDown size={10}/>:<TrendingUp size={10}/>}{art.tone}
                            </span>
                          )}
                        </div>
                      </motion.a>
                    ))}
                  </div>
                )}
                {/* No results found */}
                {intelData && !intelData.UKMTO?.length && !intelData.GDELT?.length && (
                  <div className="flex flex-col items-center py-10 gap-3">
                    <Radar size={32} className="text-gray-700"/>
                    <p className="text-xs text-gray-500 text-center">No intelligence found for that query.<br/>Try: <span className="text-accent">Red Sea</span> or <span className="text-accent">Hormuz</span></p>
                    <button onClick={() => setIntelData(null)} className="text-[10px] text-gray-500 hover:text-white border border-white/10 px-3 py-1.5 rounded-full mt-1 transition-all">← Back to search</button>
                  </div>
                )}
                {!intelData && (
                  <div className="flex flex-col items-center py-12 gap-3">
                    <Radar size={32} className="text-gray-700"/>
                    <p className="text-xs text-gray-600 text-center">Use the search bar or quick tags above to scan global intelligence feeds</p>
                  </div>
                )}
              </>
            )}
          </motion.div>
        )}

        {/* ── PORTWATCH ──────────────────────────────────── */}
        {activeTab === 'portwatch' && (
          <motion.div key="portwatch" initial={{opacity:0}} animate={{opacity:1}} className="flex flex-col gap-4">
            <form onSubmit={e => { e.preventDefault(); onPortwatchSearch(portQ, portMetric); }} className="flex flex-col gap-2">
              <div className="relative">
                <MapPin size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600"/>
                <input value={portQ} onChange={e => setPortQ(e.target.value)} placeholder="Port code: INMUN, INPRD, AEJEA…"
                  className="w-full bg-black/40 border border-white/10 rounded-xl py-2.5 pl-9 pr-10 text-[12px] text-white placeholder-gray-600 focus:outline-none focus:border-accent/60"/>
                <button type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"><Search size={13}/></button>
              </div>
              <select value={portMetric} onChange={e => setPortMetric(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl py-2.5 px-3 text-[12px] text-white focus:outline-none cursor-pointer">
                {['transit_calls','congestion_index','vessel_count','cargo_volume'].map(m => (
                  <option key={m} value={m}>{m.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                ))}
              </select>
            </form>

            {!portwatchData && !isPortwatchLoading && (
              <div>
                <p className="text-[9px] text-gray-600 uppercase tracking-widest mb-2">Key Ports & Corridors — Quick Access</p>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    ['Paradip','INPRD','Odisha · SPM Hub'],
                    ['Mundra','INMUN','Gujarat · Crude/LPG'],
                    ['Vadinar','INVAD','Gujarat · IOCL/SMPL'],
                    ['Mangaluru','INMRPL','Karnataka · ISPRL'],
                    ['Dahej','INGEH','Gujarat · LNG Terminal'],
                    ['Kochi','INCOK','Kerala · BPCL/LNG'],
                    ['Strait of Hormuz','HORMUZ','Persian Gulf'],
                    ['Red Sea','REDSEA','Bab-el-Mandeb'],
                    ['Ras Laffan','QARLF','Qatar · LNG Source'],
                  ].map(([l,c,region]) => (
                    <button key={c} onClick={() => { setPortQ(l); onPortwatchSearch(l, portMetric); }}
                      className="bg-white/5 hover:bg-accent/10 hover:border-accent/40 border border-white/10 text-center p-2.5 rounded-xl transition-all">
                      <p className="text-[11px] font-bold text-white">{l}</p>
                      <p className="text-[8px] text-gray-500 font-mono">{c}</p>
                      <p className="text-[8px] text-gray-600">{region}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {isPortwatchLoading ? (
              <div className="flex flex-col items-center py-12 gap-3">
                <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin"/>
                <p className="text-xs text-gray-500 animate-pulse">Fetching MARG PortWatch Analytics…</p>
              </div>
            ) : portwatchData && (
              <motion.div initial={{opacity:0,y:12}} animate={{opacity:1,y:0}}
                className="bg-white/[0.04] rounded-2xl p-4 border border-white/8">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <p className="text-[9px] text-gray-500 uppercase tracking-widest">Port / Corridor</p>
                    <p className="text-lg font-bold font-mono text-accent">{portwatchData.port_id}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[9px] text-gray-500 uppercase tracking-widest">Metric</p>
                    <p className="text-[12px] font-semibold text-white">{portwatchData.metric_label || portwatchData.metric?.replace(/_/g,' ')}</p>
                    {portwatchData.unit && <p className="text-[9px] text-gray-500 font-mono">{portwatchData.unit}</p>}
                  </div>
                </div>

                {portwatchData.summary && (
                  <div className="grid grid-cols-3 gap-2 bg-black/40 p-2.5 rounded-xl border border-white/5 mb-3 text-center">
                    <div>
                      <p className="text-[8px] text-gray-500 uppercase">Peak</p>
                      <p className="text-xs font-mono font-bold text-emerald-400">{portwatchData.summary.peak}</p>
                    </div>
                    <div>
                      <p className="text-[8px] text-gray-500 uppercase">Crisis Trough</p>
                      <p className="text-xs font-mono font-bold text-red-400">{portwatchData.summary.trough}</p>
                    </div>
                    <div>
                      <p className="text-[8px] text-gray-500 uppercase">Traffic Shock</p>
                      <p className="text-xs font-mono font-bold text-orange-400">-{portwatchData.summary.crisis_drop_pct}%</p>
                    </div>
                  </div>
                )}

                {(() => {
                  const maxVal = Math.max(...(portwatchData.data?.map(d => d.value) || [1]), 1);
                  return (
                    <div className="max-h-56 overflow-y-auto pr-1 space-y-1.5 scrollbar-thin">
                      {portwatchData.data?.map((d, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <span className="text-[10px] text-gray-400 font-mono w-24 flex-shrink-0">{d.date}</span>
                          <div className="flex-1 h-1.5 bg-white/8 rounded-full overflow-hidden">
                            <div className="h-full bg-accent rounded-full transition-all duration-500" 
                              style={{width:`${Math.min(100, Math.max(5, (d.value / maxVal) * 100))}%`}}/>
                          </div>
                          <span className="text-[11px] font-mono font-bold text-emerald-400 w-10 text-right">{d.value}</span>
                        </div>
                      ))}
                    </div>
                  );
                })()}

                {portwatchData.summary?.note && (
                  <p className="text-[10px] text-gray-400 mt-3 flex items-start gap-1.5 pt-3 border-t border-white/5 leading-relaxed">
                    <Info size={11} className="text-accent flex-shrink-0 mt-0.5"/>
                    <span>{portwatchData.summary.note}</span>
                  </p>
                )}
              </motion.div>
            )}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
