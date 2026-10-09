import { env } from '../config/env.js';
import { MockAIFactory } from './factories/MockAIFactory.js';
import { ExternalAIFactory } from './factories/ExternalAIFactory.js';
import { LoggingDecorator, RetryDecorator } from './decorators/ImageGeneratorDecorators.js';

export function createAIFactory(provider = env.aiProvider) {
  switch (provider) {
    case 'external':
      return new ExternalAIFactory(env.aiServiceUrl, env.aiTimeoutMs);
    case 'mock':
    default:
      return new MockAIFactory();
  }
}

export class RemodelService {
  constructor(factory = createAIFactory()) {
    this.provider = factory.name;
    this.analyzer = factory.createRoomAnalyzer();
    this.generator = new LoggingDecorator(new RetryDecorator(factory.createImageGenerator()));
  }

  async remodel(request) {
    const analysis = await this.analyzer.analyze(request);
    const result = await this.generator.generate(request, analysis);
    return { provider: this.provider, analysis, ...result };
  }
}
