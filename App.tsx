import React, { useState, useEffect } from 'react';
import { 
  IconShieldCheck, 
  IconFileText, 
  IconMic, 
  IconVideo, 
  IconImage, 
  IconUpload, 
  IconActivity,
  IconAlertTriangle
} from './components/Icons';
import { verifyMedia } from './services/geminiService';
import { MediaType, AnalysisStatus, VerificationResult } from './types';
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

const RATE_LIMIT_SECONDS = 10;

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
  const [progressMessage, setProgressMessage] = useState<string>('');

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

  const handleVerify = async () => {
    if (cooldown > 0) return;
    if (!inputText && !selectedFile) return;

    setCooldown(RATE_LIMIT_SECONDS);
    setStatus(AnalysisStatus.ANALYZING);

    // Dynamic steps based on context
    const steps = ['Initializing forensic protocols...'];
    
    if (activeTab === 'text') {
      steps.push(
        'Analyzing linguistic patterns...',
        'Checking logical consistency...',
        'Detecting LLM generation markers...',
        'Verifying factual claims...'
      );
    } else if (activeTab === 'image') {
      steps.push(
        'Scanning Exif & metadata headers...',
        'Analyzing Error Level Analysis (ELA)...',
        'Checking shadow and lighting coherence...',
        'Scanning for generative noise artifacts...'
      );
    } else if (activeTab === 'audio') {
      steps.push(
        'Generating spectral analysis...',
        'Detecting voice cloning artifacts...',
        'Analyzing breathing and pause patterns...',
        'Checking background noise continuity...'
      );
    } else if (activeTab === 'video') {
      steps.push(
        'Extracting keyframes for analysis...',
        'Checking audio-visual synchronization...',
        'Analyzing temporal consistency...',
        'Detecting face manipulation artifacts...'
      );
    }

    if (useSearch) {
      steps.push(
        'Querying global news index...',
        'Cross-referencing trusted sources...',
        'Verifying media provenance...'
      );
    }
    
    steps.push('Compiling final verdict...');

    setProgressMessage(steps[0]);
    let stepIndex = 0;
    
    const intervalId = setInterval(() => {
      stepIndex++;
      if (stepIndex < steps.length) {
        setProgressMessage(steps[stepIndex]);
      }
    }, 2000); // Update message every 2s

    try {
      const content = activeTab === 'text' ? inputText : selectedFile!;
      const data = await verifyMedia(activeTab, content, useSearch);
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
    setProgressMessage('');
  };

  const getAcceptTypes = () => {
    switch (activeTab) {
      case 'audio': return 'audio/*';
      case 'video': return 'video/*';
      case 'image': return 'image/*';
      default: return '*';
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
            </div>
          </div>
        )}

        {status === AnalysisStatus.ANALYZING && (
          <div className="flex flex-col items-center justify-center min-h-[50vh] animate-in fade-in duration-700">
            <div className="relative">
              <div className="w-24 h-24 rounded-full border-t-4 border-b-4 border-veritas-500 animate-spin"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <IconShieldCheck className="w-10 h-10 text-veritas-500 opacity-50" />
              </div>
            </div>
            <h2 className="mt-8 text-2xl font-bold text-white">Analyzing Integrity</h2>
            <div className="mt-4 flex flex-col items-center gap-2">
              <p className="text-veritas-400 font-medium animate-pulse text-lg">{progressMessage}</p>
              <div className="flex gap-1 mt-1">
                <span className="w-2 h-2 rounded-full bg-veritas-600 animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-2 h-2 rounded-full bg-veritas-500 animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-2 h-2 rounded-full bg-veritas-400 animate-bounce"></span>
              </div>
            </div>
          </div>
        )}

        {status === AnalysisStatus.COMPLETED && result && (
          <ResultView result={result} onReset={resetAnalysis} />
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