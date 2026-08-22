import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, Volume2, VolumeX, FileText, CheckCircle2, 
  Download, Copy, X, ArrowRight, Activity, Flame, 
  Droplets, Lock, AlertTriangle, ChevronRight
} from 'lucide-react';

export default function DirectiveDossierModal({ auditResult, onClose }) {
  const [activeTab, setActiveTab] = useState('story');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [copied, setCopied] = useState(false);

  const story = auditResult?.executive_story || {};
  const chapters = story.chapters || [];
  const orders = story.actionable_orders || [];
  const hash = auditResult?.cryptographic_hash || '';

  // Clean up speech synthesis on unmount
  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const toggleSpeech = () => {
    if (!window.speechSynthesis) return;

    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
    } else {
      const textToRead = story.audio_narration_script || story.executive_summary || "National Energy Security Directive Authorized.";
      const utterance = new SpeechSynthesisUtterance(textToRead);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      window.speechSynthesis.speak(utterance);
      setIsPlayingAudio(true);
    }
  };

  const copyDossier = () => {
    const text = story.full_markdown || JSON.stringify(auditResult, null, 2);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadMarkdown = () => {
    const text = story.full_markdown || JSON.stringify(auditResult, null, 2);
    const blob = new Blob([text], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `BHARAT_SHIELD_SOVEREIGN_DIRECTIVE_${Date.now()}.md`;
    a.click();
  };

  const downloadCsv = () => {
    if (!auditResult?.ledger_csv) return;
    const blob = new Blob([auditResult.ledger_csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `BHARAT_SHIELD_EXECUTION_LEDGER_${Date.now()}.csv`;
    a.click();
  };

  const getEngineColor = (engine) => {
    switch(engine) {
      case 'NETRA': return 'border-yellow-500/40 bg-yellow-500/10 text-yellow-400';
      case 'MARG': return 'border-orange-500/40 bg-orange-500/10 text-orange-400';
      case 'RASAYAN': return 'border-cyan-500/40 bg-cyan-500/10 text-cyan-400';
      case 'KOSH': return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400';
      case 'CHAKRA': return 'border-red-500/40 bg-red-500/10 text-red-400';
      default: return 'border-purple-500/40 bg-purple-500/10 text-purple-400';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative w-full max-w-4xl max-h-[90vh] bg-gray-950 border border-emerald-500/40 rounded-2xl shadow-[0_0_50px_rgba(16,185,129,0.2)] flex flex-col overflow-hidden text-gray-100"
      >
        {/* Top Sovereign Header */}
        <div className="bg-gradient-to-r from-gray-900 via-gray-900 to-gray-950 px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-400/50 flex items-center justify-center shadow-lg shadow-emerald-500/10">
              <Shield className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono tracking-widest uppercase bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded border border-emerald-500/30 font-bold">
                  Sovereign Directive
                </span>
                <span className="text-[11px] font-mono text-gray-400">
                  {new Date().toUTCString()}
                </span>
              </div>
              <h2 className="text-base font-bold text-white tracking-wide mt-0.5">
                {story.headline || 'National Energy Security Directive Dossier'}
              </h2>
            </div>
          </div>

          <button 
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white flex items-center justify-center transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Cryptographic Hash & AI Voice Audio Bar */}
        <div className="bg-black/60 px-6 py-2.5 border-b border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-gray-400 font-mono text-[11px] truncate max-w-md">
            <Lock size={13} className="text-emerald-400 flex-shrink-0" />
            <span className="text-gray-500">SHA-256:</span>
            <span className="text-emerald-400/90 truncate">{hash}</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleSpeech}
              className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                isPlayingAudio 
                  ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300 animate-pulse' 
                  : 'bg-white/5 border-white/10 text-gray-300 hover:bg-white/10 hover:text-white'
              }`}
            >
              {isPlayingAudio ? <VolumeX size={14} /> : <Volume2 size={14} className="text-emerald-400" />}
              <span>{isPlayingAudio ? 'Stop Briefing Voice' : '🎙️ AI Voice Narration'}</span>
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-white/10 bg-gray-900/50 px-6">
          {[
            { id: 'story', label: '📖 Strategic Story Briefing' },
            { id: 'orders', label: '⚡ Executive Directives' },
            { id: 'ledger', label: '📊 Allocation Ledger' },
            { id: 'markdown', label: '📄 Full Dossier (.MD)' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-xs font-semibold tracking-wide transition-all border-b-2 ${
                activeTab === tab.id
                  ? 'border-emerald-400 text-emerald-400 bg-emerald-500/5'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Scrollable Body Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-gray-800">
          {activeTab === 'story' && (
            <div className="space-y-6">
              {/* Executive Summary Callout */}
              <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-emerald-100 shadow-inner">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 font-mono">
                    Executive Operational Summary
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-gray-200">
                  {story.executive_summary}
                </p>
              </div>

              {/* Multi-Engine Story Acts */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-widest text-gray-400 font-mono">
                  Multi-Engine Deliberation & Tactical Story
                </h3>
                
                {chapters.map((ch, idx) => (
                  <motion.div 
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="p-4 rounded-xl bg-gray-900/60 border border-white/5 hover:border-white/15 transition-all"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-bold text-white flex items-center gap-2">
                        <span>{ch.title}</span>
                      </h4>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border font-bold ${getEngineColor(ch.engine)}`}>
                        {ch.engine} · {ch.role}
                      </span>
                    </div>
                    <p className="text-xs text-gray-300 leading-relaxed">
                      {ch.summary}
                    </p>
                  </motion.div>
                ))}
              </div>

              {/* Reserve Cover Impact Highlights */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-gray-900/80 border border-white/10 text-center">
                  <span className="text-[10px] text-gray-400 font-mono uppercase">Total Deficit Covered</span>
                  <p className="text-lg font-bold font-mono text-yellow-400 mt-0.5">
                    {story.total_drawdown_mmt || 0} MMT
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-gray-900/80 border border-white/10 text-center">
                  <span className="text-[10px] text-gray-400 font-mono uppercase">Mobilization Cost</span>
                  <p className="text-lg font-bold font-mono text-cyan-400 mt-0.5">
                    ₹{(story.cost_inr_crore || 0).toLocaleString()} Cr
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-gray-900/80 border border-white/10 text-center">
                  <span className="text-[10px] text-gray-400 font-mono uppercase">Remaining ISPRL Cover</span>
                  <p className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                    {story.reserve_days_remaining || 9.5} Days
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'orders' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-200 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-yellow-400 uppercase tracking-wide">
                    Mandatory Operational Directives
                  </h4>
                  <p className="text-xs text-gray-300 mt-0.5">
                    These executable orders have been cryptographically verified and broadcast to ISPRL, refiners, and pipeline operators.
                  </p>
                </div>
              </div>

              <div className="space-y-2.5">
                {orders.map((order, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-gray-900/80 border border-white/10 flex items-start gap-3 hover:border-emerald-500/30 transition-all">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-gray-200 leading-relaxed font-mono">
                      {order}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'ledger' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-gray-900/80 border border-white/10">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    ISPRL & OMC Execution Ledger Breakdown
                  </h4>
                  <button
                    onClick={downloadCsv}
                    className="flex items-center gap-1.5 text-[11px] bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 rounded-lg px-2.5 py-1 transition-all"
                  >
                    <Download size={12} />
                    <span>Download CSV</span>
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <pre className="p-3 bg-black/80 rounded-lg text-emerald-400 font-mono text-[11px] overflow-x-auto">
                    {auditResult?.ledger_csv || "Entity,Type,Drawdown_MMT\nIOCL,OMC Commercial,2.7\nISPRL Mangaluru,ISPRL Strategic,1.8"}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'markdown' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400 font-mono">Official Formatted Directive Report</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={copyDossier}
                    className="flex items-center gap-1 text-[11px] bg-white/5 hover:bg-white/10 text-gray-300 rounded px-2.5 py-1 transition-all"
                  >
                    <Copy size={12} />
                    <span>{copied ? 'Copied!' : 'Copy Dossier'}</span>
                  </button>
                  <button
                    onClick={downloadMarkdown}
                    className="flex items-center gap-1 text-[11px] bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 rounded px-2.5 py-1 transition-all"
                  >
                    <Download size={12} />
                    <span>Download .MD</span>
                  </button>
                </div>
              </div>

              <textarea 
                readOnly
                value={story.full_markdown || ''}
                rows={16}
                className="w-full p-4 bg-black/80 border border-white/10 rounded-xl font-mono text-[11px] text-gray-300 focus:outline-none scrollbar-thin scrollbar-thumb-gray-800"
              />
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="bg-gray-900/80 px-6 py-3.5 border-t border-white/10 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-[11px] text-gray-400">
            <Shield size={14} className="text-emerald-400" />
            <span>Authorized by Command Center — BHARAT-SHIELD</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={downloadMarkdown}
              className="flex items-center gap-1.5 text-xs bg-white/10 hover:bg-white/15 text-white font-medium rounded-lg px-3 py-1.5 transition-all"
            >
              <Download size={14} />
              <span>Export Dossier (.MD)</span>
            </button>

            <button
              onClick={downloadCsv}
              className="flex items-center gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg px-4 py-1.5 transition-all shadow-lg shadow-emerald-600/20"
            >
              <Download size={14} />
              <span>Download Ledger (.CSV)</span>
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
