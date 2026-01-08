import React, { useState } from 'react';
import { VerificationResult, MediaType } from '../types';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { 
  IconShieldCheck, 
  IconAlertTriangle, 
  IconFileText, 
  IconImage, 
  IconVideo, 
  IconMic, 
  IconInfo, 
  IconChevronDown 
} from './Icons';

interface ResultViewProps {
  result: VerificationResult;
  onReset: () => void;
  mediaThumbnail?: string;
  mediaType?: MediaType;
}

const ResultView: React.FC<ResultViewProps> = ({ result, onReset, mediaThumbnail, mediaType }) => {
  const isAuthentic = result.verdict === 'Authentic';
  const isSuspicious = result.verdict === 'Fake/Generated' || result.verdict === 'Suspicious';
  const isInconclusive = result.verdict === 'Inconclusive';

  const [expandedDetails, setExpandedDetails] = useState<Set<number>>(() => {
    // Automatically expand all details if the verdict is suspicious/fake to show explanations immediately
    if (isSuspicious) {
      return new Set(result.technicalDetails.map((_, idx) => idx));
    }
    return new Set();
  });
  
  const color = isAuthentic ? '#10b981' : isSuspicious ? '#ef4444' : '#f59e0b';
  const verdictColorClass = isAuthentic ? 'text-emerald-500' : isSuspicious ? 'text-red-500' : 'text-amber-500';
  const bgBadgeClass = isAuthentic ? 'bg-emerald-500/10 border-emerald-500/20' : isSuspicious ? 'bg-red-500/10 border-red-500/20' : 'bg-amber-500/10 border-amber-500/20';

  const data = [
    { name: 'Confidence', value: result.confidence },
    { name: 'Remaining', value: 100 - result.confidence },
  ];

  const getTypeIcon = () => {
    switch (mediaType) {
      case 'text': return <IconFileText className="w-5 h-5" />;
      case 'image': return <IconImage className="w-5 h-5" />;
      case 'audio': return <IconMic className="w-5 h-5" />;
      case 'video': return <IconVideo className="w-5 h-5" />;
      default: return null;
    }
  };

  const toggleDetail = (index: number) => {
    const newSet = new Set(expandedDetails);
    if (newSet.has(index)) {
      newSet.delete(index);
    } else {
      newSet.add(index);
    }
    setExpandedDetails(newSet);
  };

  return (
    <div className="w-full max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Evidence Preview Banner */}
      {mediaThumbnail && mediaType !== 'text' && (
        <div className="mb-8 rounded-2xl overflow-hidden border border-slate-700/50 bg-slate-800/50 shadow-2xl relative group">
          <div className="absolute top-4 left-4 z-10 bg-slate-900/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-slate-700 flex items-center gap-2 text-xs font-medium text-slate-300">
            {getTypeIcon()}
            <span className="uppercase">{mediaType} Evidence</span>
          </div>
          <div className="w-full h-48 md:h-64 bg-slate-900 flex items-center justify-center overflow-hidden">
             <img 
               src={mediaThumbnail} 
               alt="Evidence Preview" 
               className={`w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 ${mediaType === 'audio' ? 'opacity-80' : ''}`} 
             />
             {mediaType === 'audio' && (
               <div className="absolute inset-0 flex items-center justify-center">
                 <div className="w-16 h-16 rounded-full bg-veritas-500/20 flex items-center justify-center backdrop-blur-sm border border-veritas-500/50">
                   <IconMic className="w-8 h-8 text-veritas-400" />
                 </div>
               </div>
             )}
          </div>
        </div>
      )}

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

      {/* Inconclusive Disclaimer */}
      {isInconclusive && (
        <div className="mb-8 p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 flex items-start gap-4 animate-in fade-in slide-in-from-top-2">
          <IconAlertTriangle className="w-6 h-6 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-amber-400 font-semibold mb-1">Manual Review Recommended</h4>
            <p className="text-slate-300 text-sm leading-relaxed">
              The system could not definitively verify the authenticity of this media. Factors such as low resolution, significant compression artifacts, lack of context, or ambiguous features prevented a clear verdict. We strongly recommend further manual review by a human expert.
            </p>
          </div>
        </div>
      )}

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
            <div className="space-y-2">
              {result.technicalDetails.map((item, idx) => {
                const isExpanded = expandedDetails.has(idx);
                return (
                  <div 
                    key={idx} 
                    className={`rounded-lg transition-colors border ${isExpanded ? 'bg-slate-800 border-slate-600' : 'bg-transparent border-transparent hover:bg-slate-800/30 hover:border-slate-700/50'}`}
                  >
                    <div 
                      className="flex flex-col p-3 cursor-pointer select-none"
                      onClick={() => toggleDetail(idx)}
                    >
                      <div className="flex justify-between items-start gap-2">
                        <div className="flex-1">
                            <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold block">{item.label}</span>
                            <div className="text-sm text-slate-200 font-medium mt-0.5">{item.value}</div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wide uppercase shrink-0 ${
                            item.status === 'pass' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                            item.status === 'fail' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                            'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          }`}>
                            {item.status}
                          </span>
                          <IconChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} />
                        </div>
                      </div>
                    </div>
                    
                    {/* Expandable Section */}
                    {isExpanded && item.explanation && (
                      <div className="px-3 pb-3 animate-in fade-in slide-in-from-top-1 duration-200">
                        <div className={`text-xs p-3 rounded-md leading-relaxed flex gap-2 ${
                            item.status === 'pass' ? 'bg-slate-700/50 text-slate-300' :
                            item.status === 'fail' ? 'bg-red-500/10 text-red-200' :
                            'bg-amber-500/10 text-amber-200'
                        }`}>
                          <IconInfo className="w-4 h-4 shrink-0 mt-0.5 opacity-70" />
                          <div>
                            <span className="font-semibold block mb-1 opacity-90">Analysis Insight:</span>
                            {item.explanation}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
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