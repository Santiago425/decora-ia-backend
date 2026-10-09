import { AIProviderFactory } from './AIProviderFactory.js';
import {
  AIServiceClient,
  AIServiceAnalyzerAdapter,
  AIServiceGeneratorAdapter,
} from '../adapters/AIServiceAdapter.js';

export class ExternalAIFactory extends AIProviderFactory {
  constructor(baseUrl, timeoutMs) {
    super();
    if (!baseUrl) throw new Error('AI_SERVICE_URL is required for the external provider');
    this.client = new AIServiceClient(baseUrl, timeoutMs);
  }

  get name() {
    return 'external';
  }

  createRoomAnalyzer() {
    return new AIServiceAnalyzerAdapter(this.client);
  }

  createImageGenerator() {
    return new AIServiceGeneratorAdapter(this.client);
  }
}
