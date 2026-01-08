import React from 'react';
import { VerificationResult } from '../types';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { IconShieldCheck, IconAlertTriangle } from './Icons';

interface ResultViewProps {
  result: VerificationResult;
  onReset: () => void;
}

const ResultView: React.FC<ResultViewProps> = ({ result, onReset }) => {
  const isAuthentic = result.verdict === 'Authentic';
  const isSuspicious = result.verdict === 'Fake/Generated' || result.verdict === 'Suspicious';
  
  const color = isAuthentic ? '#10b981' : isSuspicious ? '#ef4444' : '#f59e0b';
  const verdictColorClass = isAuthentic ? 'text-emerald-500' : isSuspicious ? 'text-red-500' : 'text-amber-500';
  const bgBadgeClass = isAuthentic ? 'bg-emerald-500/10 border-emerald-500/20' : isSuspicious ? 'bg-red-500/10 border-red-500/20' : 'bg-amber-500/10 border-amber-500/20';

  const data = [
    { name: 'Confidence', value: result.confidence },
    { name: 'Remaining', value: 100 - result.confidence },
  ];

  return (
    <div className="w-full max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header Banner */}
      <div className={`p-6 rounded-2xl border ${bgBadgeClass} mb-8 flex items-center justify-between`}>
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-full ${isAuthentic ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'}`}>
             {isAuthentic ? <IconShieldCheck className="w-8 h-8" /> : <IconAlertTriangle className="w-8 h-8" />}
          </div>
          <div>
            <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Analysis Verdict</h2>
            <h1 className={`text-3xl font-bold ${verdictColorClass}`}>{result.verdict}</h1>
          </div>
        </div>
        
        {/* Confidence Gauge */}
        <div className="relative w-24 h-24 hidden sm:block">
           <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={40}
                startAngle={90}
                endAngle={-270}
                dataKey="value"
                stroke="none"
              >
                <Cell fill={color} />
                <Cell fill="#334155" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-sm font-bold text-white">{result.confidence}%</span>
            <span className="text-[10px] text-slate-400">Trust</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Main Findings */}
        <div className="md:col-span-2 space-y-6">
          <section className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
            <h3 className="text-lg font-semibold text-white mb-3">Executive Summary</h3>
            <p className="text-slate-300 leading-relaxed">
              {result.summary}
            </p>
          </section>

          <section className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
            <h3 className="text-lg font-semibold text-white mb-4">Key Findings</h3>
            <ul className="space-y-3">
              {result.reasoning.map((reason, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-veritas-400 shrink-0" />
                  <span className="text-slate-300">{reason}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* Technical Details Sidebar */}
        <div className="space-y-6">
          <section className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
            <h3 className="text-lg font-semibold text-white mb-4">Technical Analysis</h3>
            <div className="space-y-4">
              {result.technicalDetails.map((item, idx) => (
                <div key={idx} className="flex flex-col gap-1 pb-3 border-b border-slate-700 last:border-0 last:pb-0">
                  <span className="text-xs text-slate-400 uppercase">{item.label}</span>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-200 font-medium">{item.value}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      item.status === 'pass' ? 'bg-emerald-500/20 text-emerald-400' :
                      item.status === 'fail' ? 'bg-red-500/20 text-red-400' :
                      'bg-amber-500/20 text-amber-400'
                    }`}>
                      {item.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {result.sources && result.sources.length > 0 && (
             <section className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
               <h3 className="text-lg font-semibold text-white mb-3">Verified Sources</h3>
               <ul className="space-y-2">
                 {result.sources.map((source, idx) => (
                   <li key={idx}>
                     <a href={source.uri} target="_blank" rel="noopener noreferrer" className="text-xs text-veritas-400 hover:text-veritas-300 hover:underline truncate block">
                       {source.title || source.uri}
                     </a>
                   </li>
                 ))}
               </ul>
             </section>
          )}

          <button 
            onClick={onReset}
            className="w-full py-3 px-4 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors font-medium text-sm"
          >
            Start New Analysis
          </button>
        </div>
      </div>
    </div>
  );
};

export default ResultView;
