import { GoogleGenAI, Type } from "@google/genai";
import { VerificationResult, MediaType } from "../types";

// Helper to convert blob to base64
export const fileToGenerativePart = async (file: File): Promise<{ inlineData: { data: string; mimeType: string } }> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64String = (reader.result as string).split(',')[1];
      resolve({
        inlineData: {
          data: base64String,
          mimeType: file.type,
        },
      });
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

const RESPONSE_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    verdict: {
      type: Type.STRING,
      enum: ['Authentic', 'Fake/Generated', 'Inconclusive', 'Suspicious'],
      description: "The final verdict on the media's authenticity.",
    },
    confidence: {
      type: Type.NUMBER,
      description: "Confidence score between 0 and 100.",
    },
    summary: {
      type: Type.STRING,
      description: "A short paragraph summarizing the findings.",
    },
    reasoning: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
      description: "List of key reasons for the verdict.",
    },
    technicalDetails: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          label: { type: Type.STRING },
          value: { type: Type.STRING },
          status: { type: Type.STRING, enum: ['pass', 'fail', 'warn'] },
          explanation: { type: Type.STRING, description: "A detailed explanation of what this metric analyzes and its specific implication for this media's authenticity." }
        },
        required: ['label', 'value', 'status', 'explanation']
      },
      description: "Technical analysis points (e.g., 'Lip Sync', 'Audio Spectrum', 'Metadata')."
    }
  },
  required: ['verdict', 'confidence', 'summary', 'reasoning', 'technicalDetails'],
};

export const verifyMedia = async (
  type: MediaType,
  content: string | File,
  useSearch: boolean = false
): Promise<VerificationResult> => {
  // Initialize AI client inside the function to use the most current API_KEY from environment
  const apiKey = process.env.API_KEY || '';
  const ai = new GoogleGenAI({ apiKey });

  // Use gemini-2.0-flash for reliable multimodal and tool use. 
  // 'gemini-2.5-flash-latest' was causing 404s as it is not a valid public model alias yet.
  const model = 'gemini-2.0-flash';
  
  let systemInstruction = `You are Veritas, a world-class media forensics and fact-checking AI. 
  Your job is to verify the authenticity of ${type} input. 
  Detect deepfakes, AI generation artifacts, misinformation, or inconsistencies. 
  Be rigorous. If audio/video, look for artifacts, sync issues, and spectral anomalies. 
  If text, check facts and logical consistency based on your internal knowledge base.
  
  For the technicalDetails section:
  - Generate specific technical checks relevant to the media type.
  - For the 'explanation' field: Provide a detailed insight. Explain what the metric checks (e.g., "Error Level Analysis detects compression inconsistencies") AND what the specific finding implies for this media (e.g., "Uniform compression suggests authenticity").`;

  if (useSearch) {
    systemInstruction += ` You have access to Google Search. 
    MANDATORY: Use search to find if this media (or similar content) exists on the internet.
    - Check if it is a known stock image/video.
    - Check if it is from a known real event (news sources).
    - Check if it is a known generated/fake image.
    - Try to identify the original creator (Human or AI).
    If the media is found on credible news sites, it increases the likelihood of being Authentic.
    If it is found on stock sites or known AI galleries, mark as Suspicious or Generated.`;
  }

  const parts: any[] = [];
  const tools: any[] = [];

  if (useSearch) {
    tools.push({ googleSearch: {} });
  }

  if (type === 'text') {
    parts.push({ text: content as string });
  } else if (type === 'audio') {
    if (content instanceof File) {
      const part = await fileToGenerativePart(content);
      parts.push(part);
      parts.push({ text: "Analyze this audio for AI generation markers, voice cloning artifacts, and natural breathing patterns." });
    }
  } else if (type === 'image') {
       if (content instanceof File) {
        const part = await fileToGenerativePart(content);
        parts.push(part);
        parts.push({ text: "Analyze this image. Describe it and search online to see if it appears on any websites, news platforms, or stock libraries." });
      }
  } else if (type === 'video') {
     if (content instanceof File) {
      const part = await fileToGenerativePart(content);
      parts.push(part);
      parts.push({ text: "Analyze this video frames. Search for key visual elements online to find if this video has been published by news agencies or creators." });
    }
  }

  // Setup configuration
  const config: any = {
    systemInstruction,
    tools: tools.length > 0 ? tools : undefined,
  };

  // IMPORTANT: When using tools (Google Search), enforcing `responseSchema` can cause API errors or malformed responses.
  // If search is enabled, we ask for JSON in the prompt and manually parse it.
  // If search is disabled, we use the API's native JSON enforcement.
  if (!useSearch) {
    config.responseMimeType = "application/json";
    config.responseSchema = RESPONSE_SCHEMA;
  } else {
    config.systemInstruction += `\n\nCRITICAL: You must return your response strictly as a valid JSON object matching this structure. Do not use markdown blocks.\n${JSON.stringify(RESPONSE_SCHEMA)}`;
  }

  try {
    const response = await ai.models.generateContent({
      model,
      contents: { parts },
      config,
    });

    let jsonText = response.text || "{}";
    
    // Sanitize output: Remove markdown code blocks if present (common when responseMimeType is not set)
    // Also find the JSON object boundaries to ignore preamble/postamble
    const firstBrace = jsonText.indexOf('{');
    const lastBrace = jsonText.lastIndexOf('}');
    
    if (firstBrace !== -1 && lastBrace !== -1) {
      jsonText = jsonText.substring(firstBrace, lastBrace + 1);
    }
    
    const result = JSON.parse(jsonText) as VerificationResult;

    // Extract search grounding if available and supported by the model response
    const groundingChunks = response.candidates?.[0]?.groundingMetadata?.groundingChunks;
    if (groundingChunks) {
      const sources: { title: string; uri: string }[] = [];
      groundingChunks.forEach((chunk: any) => {
        if (chunk.web) {
            sources.push({ title: chunk.web.title, uri: chunk.web.uri });
        }
      });
      // Deduplicate sources
      const uniqueSources = Array.from(new Map(sources.map(item => [item.uri, item])).values());
      if (uniqueSources.length > 0) {
        result.sources = uniqueSources;
      }
    }

    return result;

  } catch (error) {
    console.error("Gemini Verification Error:", error);
    throw error; // Re-throw to handle in App.tsx
  }
};