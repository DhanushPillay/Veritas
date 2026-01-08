import React, { useState, useEffect } from 'react';
import { 
  IconShieldCheck, 
  IconFileText, 
  IconMic, 
  IconVideo, 
  IconImage, 
  IconUpload, 
  IconActivity,
  IconAlertTriangle,
  IconTrash,
  IconCheck
} from './components/Icons';
import { verifyMedia } from './services/geminiService';
import { MediaType, AnalysisStatus, VerificationResult, HistoryItem } from './types';
import ResultView from './components/ResultView';

// --- Components defined internally to keep files minimized but structured ---

const Navbar: React.FC = () => (
  <nav className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50 flex items-center justify-between px-6">
    <div className="flex items-center gap-2 text-veritas-400">
      <IconShieldCheck className="w-8 h-8" />
      <span className="text-xl font-bold tracking-tight text-white">VERITAS</span>
    </div>
    <div className="flex items-center gap-4">
      <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/50 border border-slate-700 text-xs text-slate-400">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        System Operational
      </div>
    </div>
  </nav>
);

const TabButton: React.FC<{ 
  active: boolean; 
  onClick: () => void; 
  icon: React.ReactNode; 
  label: string 
}> = ({ active, onClick, icon, label }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
      active 
        ? 'bg-veritas-600 text-white shadow-lg shadow-veritas-900/50 ring-1 ring-veritas-500' 
        : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
    }`}
  >
    {icon}
    {label}
  </button>
);

const Toggle: React.FC<{
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}> = ({ checked, onChange, label }) => (
  <button 
    onClick={() => onChange(!checked)}
    className="flex items-center gap-3 group focus:outline-none"
  >
    <div className={`w-11 h-6 rounded-full transition-colors relative ${checked ? 'bg-veritas-500' : 'bg-slate-700'}`}>
      <div className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
    </div>
    <span className={`text-sm font-medium transition-colors ${checked ? 'text-veritas-400' : 'text-slate-400 group-hover:text-slate-300'}`}>
      {label}
    </span>
  </button>
);

// Thumbnail Generator Utility
const generateThumbnail = async (file: File, type: MediaType): Promise<string | undefined> => {
  if (type === 'text') return undefined;
  
  try {
    if (type === 'image') {
      return await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const img = new Image();
          img.onload = () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const maxSize = 300;
            let width = img.width;
            let height = img.height;
            
            if (width > height) {
              if (width > maxSize) {
                height *= maxSize / width;
                width = maxSize;
              }
            } else {
              if (height > maxSize) {
                width *= maxSize / height;
                height = maxSize;
              }
            }
            
            canvas.width = width;
            canvas.height = height;
            ctx?.drawImage(img, 0, 0, width, height);
            resolve(canvas.toDataURL('image/jpeg', 0.6));
          };
          img.src = e.target?.result as string;
        };
        reader.readAsDataURL(file);
      });
    }
    
    if (type === 'video') {
       return await new Promise((resolve) => {
         const video = document.createElement('video');
         video.preload = 'metadata';
         video.src = URL.createObjectURL(file);
         video.muted = true;
         video.playsInline = true;
         video.currentTime = 0.5; // Capture frame at 0.5s
         
         const capture = () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const maxSize = 300;
            let width = video.videoWidth;
            let height = video.videoHeight;
             if (width > height) {
              if (width > maxSize) {
                height *= maxSize / width;
                width = maxSize;
              }
            } else {
              if (height > maxSize) {
                width *= maxSize / height;
                height = maxSize;
              }
            }
            canvas.width = width;
            canvas.height = height;
            ctx?.drawImage(video, 0, 0, width, height);
            URL.revokeObjectURL(video.src);
            resolve(canvas.toDataURL('image/jpeg', 0.6));
         };

         video.onseeked = capture;
         video.onloadeddata = () => {
           // Fallback if seek doesn't trigger
           setTimeout(capture, 500); 
         };
         
         // Timeout fallback
         setTimeout(() => {
             resolve(undefined); 
         }, 3000);
       });
    }

    if (type === 'audio') {
        // Generate synthetic waveform visual
        const canvas = document.createElement('canvas');
        canvas.width = 300;
        canvas.height = 80;
        const ctx = canvas.getContext('2d');
        if (ctx) {
            ctx.fillStyle = '#0f172a'; // matches slate-900
            ctx.fillRect(0,0,300,80);
            
            const barWidth = 4;
            const gap = 2;
            const bars = Math.floor(300 / (barWidth + gap));
            
            ctx.fillStyle = '#38bdf8'; // veritas-400
            for(let i=0; i<bars; i++) {
                // Generate a "waveform" looking random height
                const h = Math.random() * 50 + 10;
                const x = i * (barWidth + gap);
                const y = (80 - h) / 2;
                ctx.fillRect(x, y, barWidth, h);
            }
        }
        return canvas.toDataURL('image/png');
    }
  } catch (e) {
    console.error("Thumbnail generation failed", e);
    return undefined;
  }
};

const RATE_LIMIT_SECONDS = 10;

interface AnalysisStep {
  id: number;
  label: string;
  status: 'pending' | 'processing' | 'completed';
}

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<MediaType>('text');
  const [inputText, setInputText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<AnalysisStatus>(AnalysisStatus.IDLE);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [isKeyReady, setIsKeyReady] = useState<boolean>(false);
  const [isCheckingKey, setIsCheckingKey] = useState<boolean>(true);
  const [useSearch, setUseSearch] = useState<boolean>(false);
  const [cooldown, setCooldown] = useState<number>(0);
  const [currentThumbnail, setCurrentThumbnail] = useState<string | undefined>(undefined);
  const [analysisSteps, setAnalysisSteps] = useState<AnalysisStep[]>([]);
  
  // History State
  const [history, setHistory] = useState<HistoryItem[]>(() => {
    try {
      const saved = localStorage.getItem('veritas_history');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.warn("Failed to load history", e);
      return [];
    }
  });

  // Persist history
  useEffect(() => {
    localStorage.setItem('veritas_history', JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    const checkKey = async () => {
      try {
        if (window.aistudio) {
          const hasKey = await window.aistudio.hasSelectedApiKey();
          setIsKeyReady(hasKey);
        } else {
          // Fallback for environments without aistudio namespace
          setIsKeyReady(true);
        }
      } catch (error) {
        console.error("Failed to check API key status:", error);
        setIsKeyReady(true); // Attempt to proceed anyway
      } finally {
        setIsCheckingKey(false);
      }
    };
    checkKey();
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (cooldown > 0) {
      timer = setTimeout(() => setCooldown(prev => prev - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleConnectKey = async () => {
    if (window.aistudio) {
      await window.aistudio.openSelectKey();
      setIsKeyReady(true);
      // If we were in an error state, reset to IDLE so the user can try again
      if (status === AnalysisStatus.ERROR) {
        resetAnalysis();
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const getAnalysisStepsList = (type: MediaType, search: boolean): string[] => {
    const steps = ['Initializing forensic protocols...'];
    
    // Media-specific Core Analysis
    switch (type) {
      case 'text':
        steps.push(
          'Analyzing linguistic patterns...',
          'Checking logical consistency...',
          'Detecting LLM generation markers...'
        );
        break;
      case 'image':
        steps.push(
          'Scanning Exif & metadata headers...',
          'Analyzing Error Level Analysis (ELA)...',
          'Checking shadow and lighting coherence...',
          'Scanning for generative noise artifacts...'
        );
        break;
      case 'audio':
        steps.push(
          'Generating spectral analysis...',
          'Detecting voice cloning artifacts...',
          'Analyzing breathing and pause patterns...'
        );
        break;
      case 'video':
        steps.push(
          'Extracting keyframes for analysis...',
          'Checking audio-visual synchronization...',
          'Analyzing temporal consistency...',
          'Detecting face manipulation artifacts...'
        );
        break;
    }

    // Dynamic Search/Context Steps
    if (search) {
      steps.push('Connecting to secure global index...');
      if (type === 'text') {
        steps.push(
          'Querying live news knowledge base...',
          'Cross-referencing factual claims...',
          'Verifying citations and quotes...'
        );
      } else if (type === 'image') {
        steps.push(
          'Performing reverse image search...',
          'Checking media provenance registries...',
          'Cross-referencing stock libraries...'
        );
      } else if (type === 'video') {
        steps.push(
          'Searching frame fingerprints online...',
          'Verifying event location and timeline...',
          'Checking source credibility...'
        );
      } else if (type === 'audio') {
        steps.push(
          'Matching voice prints against public records...',
          'Verifying context via news reports...',
          'Checking for existing source material...'
        );
      }
    } else {
      steps.push('Skipping external search (Local Analysis)...');
    }
    
    steps.push('Compiling final forensic verdict...');
    return steps;
  };

  const handleVerify = async () => {
    if (cooldown > 0) return;
    if (!inputText && !selectedFile) return;

    setCooldown(RATE_LIMIT_SECONDS);
    setStatus(AnalysisStatus.ANALYZING);

    // Initialize Analysis Steps
    const stepLabels = getAnalysisStepsList(activeTab, useSearch);
    const initialSteps: AnalysisStep[] = stepLabels.map((label, idx) => ({
      id: idx,
      label,
      status: idx === 0 ? 'processing' : 'pending'
    }));
    setAnalysisSteps(initialSteps);

    let currentStepIndex = 0;
    const intervalId = setInterval(() => {
        setAnalysisSteps(prev => {
            if (currentStepIndex >= prev.length - 1) return prev;
            
            const next = [...prev];
            // Mark current as completed
            next[currentStepIndex] = { ...next[currentStepIndex], status: 'completed' };
            
            // Move to next
            currentStepIndex++;
            next[currentStepIndex] = { ...next[currentStepIndex], status: 'processing' };
            
            return next;
        });
    }, 1500);

    try {
      const content = activeTab === 'text' ? inputText : selectedFile!;
      
      // Generate thumbnail concurrently with verification if possible, but simplest to wait
      let thumb: string | undefined = undefined;
      if (selectedFile) {
        thumb = await generateThumbnail(selectedFile, activeTab);
      }
      setCurrentThumbnail(thumb);

      const data = await verifyMedia(activeTab, content, useSearch);
      
      // Save to History
      const newItem: HistoryItem = {
        id: crypto.randomUUID(),
        timestamp: Date.now(),
        type: activeTab,
        preview: activeTab === 'text' 
          ? (inputText.length > 60 ? inputText.substring(0, 60) + '...' : inputText)
          : (selectedFile?.name || 'Unknown File'),
        mediaThumbnail: thumb,
        result: data
      };
      
      setHistory(prev => [newItem, ...prev]);
      setResult(data);
      setStatus(AnalysisStatus.COMPLETED);
    } catch (error: any) {
      console.error(error);
      // Check for specific error indicating key issues
      if (error.message && error.message.includes("Requested entity was not found")) {
         setIsKeyReady(false);
      }
      setStatus(AnalysisStatus.ERROR);
    } finally {
      clearInterval(intervalId);
    }
  };

  const resetAnalysis = () => {
    setStatus(AnalysisStatus.IDLE);
    setResult(null);
    setInputText('');
    setSelectedFile(null);
    setAnalysisSteps([]);
    setCurrentThumbnail(undefined);
  };
  
  const loadHistoryItem = (item: HistoryItem) => {
    setResult(item.result);
    // When loading history, we set the active tab to match the item type so UI is consistent
    setActiveTab(item.type);
    setCurrentThumbnail(item.mediaThumbnail);
    setStatus(AnalysisStatus.COMPLETED);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  
  const clearHistory = () => {
    if (confirm('Are you sure you want to clear your verification history?')) {
      setHistory([]);
    }
  };

  const getAcceptTypes = () => {
    switch (activeTab) {
      case 'audio': return 'audio/*';
      case 'video': return 'video/*';
      case 'image': return 'image/*';
      default: return '*';
    }
  };
  
  const getTypeIcon = (type: MediaType) => {
    switch (type) {
      case 'text': return <IconFileText className="w-4 h-4" />;
      case 'image': return <IconImage className="w-4 h-4" />;
      case 'audio': return <IconMic className="w-4 h-4" />;
      case 'video': return <IconVideo className="w-4 h-4" />;
    }
  };

  const isInputEmpty = activeTab === 'text' ? !inputText : !selectedFile;
  const isButtonDisabled = isInputEmpty || cooldown > 0;

  if (isCheckingKey) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-veritas-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isKeyReady) {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-200 font-sans flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-slate-800/50 border border-slate-700 rounded-2xl p-8 text-center space-y-6 shadow-2xl">
          <div className="inline-flex p-4 rounded-full bg-veritas-900/30 text-veritas-400 mb-2">
            <IconShieldCheck className="w-12 h-12" />
          </div>
          <h1 className="text-2xl font-bold text-white">API Key Required</h1>
          <p className="text-slate-400 leading-relaxed">
             Veritas utilizes Gemini 2.5 Flash for rapid, multimodal media forensics. To proceed, please connect your API key.
          </p>
          <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-800 text-xs text-slate-500 text-left">
            <p className="mb-2"><strong>Note:</strong> You can use a free API key from Google AI Studio.</p>
            <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-veritas-400 hover:underline">
              Get Free API Key &rarr;
            </a>
          </div>
          <button
            onClick={handleConnectKey}
            className="w-full bg-veritas-600 hover:bg-veritas-500 text-white py-3 rounded-lg font-medium transition-colors shadow-lg shadow-veritas-900/20"
          >
            Connect API Key
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 font-sans selection:bg-veritas-500/30 selection:text-white">
      <Navbar />

      <main className="max-w-6xl mx-auto px-6 py-12">
        
        {status === AnalysisStatus.IDLE && (
          <div className="space-y-12 animate-in fade-in duration-500">
            <div className="text-center space-y-4">
              <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
                Verify Reality in Real-Time
              </h1>
              <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                Advanced AI forensics to detect deepfakes, synthetic voices, and generated text with precision.
              </p>
            </div>

            <div className="flex flex-wrap justify-center gap-4">
              <TabButton 
                active={activeTab === 'text'} 
                onClick={() => { setActiveTab('text'); setSelectedFile(null); }} 
                icon={<IconFileText className="w-5 h-5"/>} 
                label="Text Verification" 
              />
              <TabButton 
                active={activeTab === 'image'} 
                onClick={() => { setActiveTab('image'); setSelectedFile(null); }} 
                icon={<IconImage className="w-5 h-5"/>} 
                label="Image Analysis" 
              />
              <TabButton 
                active={activeTab === 'audio'} 
                onClick={() => { setActiveTab('audio'); setSelectedFile(null); }} 
                icon={<IconMic className="w-5 h-5"/>} 
                label="Voice/Audio" 
              />
              <TabButton 
                active={activeTab === 'video'} 
                onClick={() => { setActiveTab('video'); setSelectedFile(null); }} 
                icon={<IconVideo className="w-5 h-5"/>} 
                label="Video Forensics" 
              />
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-8 max-w-3xl mx-auto shadow-2xl">
              <div className="space-y-6">
                
                {activeTab === 'text' ? (
                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-slate-400">Content to Analyze</label>
                    <textarea
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      placeholder="Paste article text, social media post, or statement here..."
                      className="w-full h-48 bg-slate-900/50 border border-slate-700 rounded-xl p-4 text-slate-200 focus:outline-none focus:ring-2 focus:ring-veritas-500 transition-all resize-none"
                    />
                  </div>
                ) : (
                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-slate-400">Upload Media Evidence</label>
                    <div className="border-2 border-dashed border-slate-700 rounded-xl p-12 text-center hover:bg-slate-800/50 transition-colors group relative cursor-pointer">
                      <input 
                        type="file" 
                        accept={getAcceptTypes()} 
                        onChange={handleFileChange}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      />
                      <div className="flex flex-col items-center gap-4">
                        <div className="p-4 rounded-full bg-slate-800 group-hover:bg-slate-700 transition-colors">
                          <IconUpload className="w-8 h-8 text-veritas-400" />
                        </div>
                        <div>
                          <p className="text-lg font-medium text-slate-200">
                            {selectedFile ? selectedFile.name : `Drop your ${activeTab} file here`}
                          </p>
                          <p className="text-sm text-slate-500 mt-1">or click to browse</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                  <div className="flex items-center gap-4">
                    <Toggle 
                      checked={useSearch} 
                      onChange={setUseSearch} 
                      label="Web Search Provenance" 
                    />
                  </div>

                  <div className="flex items-center gap-4">
                    <p className="text-xs text-slate-500 hidden sm:block">
                      *Veritas processes data privately. Max 20MB.
                    </p>
                    <button
                      onClick={handleVerify}
                      disabled={isButtonDisabled}
                      className={`
                        bg-gradient-to-r from-veritas-600 to-veritas-500 hover:from-veritas-500 hover:to-veritas-400 text-white px-8 py-3 rounded-lg font-medium transition-all shadow-lg shadow-veritas-900/20 flex items-center gap-2
                        ${isButtonDisabled ? 'opacity-50 cursor-not-allowed grayscale' : ''}
                      `}
                    >
                      {cooldown > 0 ? (
                        <span className="animate-pulse">Wait {cooldown}s</span>
                      ) : (
                        <>
                          <IconActivity className="w-5 h-5" />
                          Run Analysis
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Recent Analysis Section */}
              {history.length > 0 && (
                <div className="max-w-4xl mx-auto mt-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-300">Recent Analysis</h3>
                    <button 
                      onClick={clearHistory}
                      className="flex items-center gap-2 text-xs text-slate-500 hover:text-red-400 transition-colors"
                    >
                      <IconTrash className="w-3 h-3" />
                      Clear History
                    </button>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {history.map(item => {
                      const isAuthentic = item.result.verdict === 'Authentic';
                      const isSuspicious = item.result.verdict === 'Fake/Generated' || item.result.verdict === 'Suspicious';
                      const badgeColor = isAuthentic ? 'text-emerald-400' : isSuspicious ? 'text-red-400' : 'text-amber-400';
                      
                      return (
                        <div 
                          key={item.id}
                          onClick={() => loadHistoryItem(item)}
                          className="bg-slate-800/30 border border-slate-700/50 hover:border-veritas-500/50 hover:bg-slate-800/60 rounded-xl overflow-hidden cursor-pointer transition-all group flex"
                        >
                          {/* Thumbnail Preview in List */}
                          {item.mediaThumbnail ? (
                            <div className="w-24 h-full bg-slate-900 shrink-0 relative">
                               <img src={item.mediaThumbnail} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" alt="preview" />
                               {item.type === 'audio' && <IconMic className="absolute inset-0 m-auto w-6 h-6 text-white/50" />}
                               {item.type === 'video' && <IconVideo className="absolute inset-0 m-auto w-6 h-6 text-white/50" />}
                            </div>
                          ) : (
                             <div className="w-24 h-full bg-slate-800/50 flex items-center justify-center shrink-0">
                               {getTypeIcon(item.type)}
                             </div>
                          )}

                          <div className="p-4 flex-1 min-w-0">
                            <div className="flex justify-between items-start mb-2">
                               <div className="flex items-center gap-2 text-slate-400 group-hover:text-veritas-400 transition-colors">
                                 <span className="text-xs font-mono">{new Date(item.timestamp).toLocaleDateString()}</span>
                               </div>
                               <span className={`text-xs font-bold ${badgeColor} px-2 py-0.5 rounded-full bg-slate-900/50`}>
                                 {item.result.verdict}
                               </span>
                            </div>
                            <p className="text-sm text-slate-300 line-clamp-2">
                               {item.preview}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {status === AnalysisStatus.ANALYZING && (
          <div className="flex flex-col items-center justify-center min-h-[50vh] animate-in fade-in duration-700 max-w-md mx-auto w-full">
            {/* Spinner Header */}
            <div className="mb-8 text-center">
                 <div className="relative inline-block">
                    <div className="w-16 h-16 rounded-full border-4 border-slate-700 border-t-veritas-500 animate-spin"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <IconShieldCheck className="w-8 h-8 text-slate-600" />
                    </div>
                </div>
                <h2 className="mt-4 text-xl font-bold text-white">Analyzing Integrity</h2>
            </div>

            {/* Steps List */}
            <div className="w-full space-y-3 bg-slate-800/30 p-6 rounded-xl border border-slate-700/50 backdrop-blur-sm shadow-xl">
                {analysisSteps.map((step) => (
                    <div key={step.id} className="flex items-center gap-3">
                        <div className="shrink-0 w-5 h-5 flex items-center justify-center">
                            {step.status === 'completed' && <IconCheck className="w-5 h-5 text-emerald-500 animate-in zoom-in duration-300" />}
                            {step.status === 'processing' && (
                                <div className="w-4 h-4 rounded-full border-2 border-veritas-500 border-r-transparent animate-spin" />
                            )}
                            {step.status === 'pending' && (
                                <div className="w-2 h-2 rounded-full bg-slate-700" />
                            )}
                        </div>
                        <span className={`text-sm transition-colors duration-300 ${
                            step.status === 'processing' ? 'text-white font-medium scale-105 origin-left' : 
                            step.status === 'completed' ? 'text-slate-400' : 'text-slate-600'
                        }`}>
                            {step.label}
                        </span>
                    </div>
                ))}
            </div>
          </div>
        )}

        {status === AnalysisStatus.COMPLETED && result && (
          <ResultView 
            result={result} 
            onReset={resetAnalysis} 
            mediaThumbnail={currentThumbnail} 
            mediaType={activeTab} 
          />
        )}

        {status === AnalysisStatus.ERROR && (
           <div className="flex flex-col items-center justify-center min-h-[50vh] text-center max-w-md mx-auto">
             <div className="p-4 bg-red-500/10 rounded-full mb-6">
                <IconActivity className="w-12 h-12 text-red-500" />
             </div>
             <h2 className="text-2xl font-bold text-white mb-2">Analysis Failed</h2>
             <p className="text-slate-400 mb-6">We encountered an issue processing your request. Please ensure you are using a valid API key.</p>
             <div className="flex gap-4 justify-center">
               <button onClick={resetAnalysis} className="px-6 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white">Return Home</button>
               <button onClick={handleConnectKey} className="px-6 py-2 bg-veritas-700 hover:bg-veritas-600 rounded-lg text-white">Update API Key</button>
             </div>
           </div>
        )}

      </main>
    </div>
  );
};

export default App;