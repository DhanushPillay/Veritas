export type MediaType = 'text' | 'audio' | 'video' | 'image';

export enum AnalysisStatus {
  IDLE = 'IDLE',
  ANALYZING = 'ANALYZING',
  COMPLETED = 'COMPLETED',
  ERROR = 'ERROR',
}

export interface VerificationResult {
  verdict: 'Authentic' | 'Fake/Generated' | 'Inconclusive' | 'Suspicious';
  confidence: number; // 0 to 100
  summary: string;
  reasoning: string[];
  technicalDetails: {
    label: string;
    value: string;
    status: 'pass' | 'fail' | 'warn';
  }[];
  sources?: {
    title: string;
    uri: string;
  }[];
}

export interface HistoryItem {
  id: string;
  timestamp: number;
  type: MediaType;
  preview: string;
  result: VerificationResult;
}
