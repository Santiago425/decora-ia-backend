import { ImageGenerator } from '../products/ImageGenerator.js';

// Decorator: agrega comportamiento a cualquier ImageGenerator sin modificarlo.
export class ImageGeneratorDecorator extends ImageGenerator {
  constructor(inner) {
    super();
    this.inner = inner;
  }

  generate(request, analysis) {
    return this.inner.generate(request, analysis);
  }
}

export class LoggingDecorator extends ImageGeneratorDecorator {
  constructor(inner, logger = console) {
    super(inner);
    this.logger = logger;
  }

  async generate(request, analysis) {
    const start = Date.now();
    const result = await super.generate(request, analysis);
    this.logger.info(`[ai] style=${request.style} took ${Date.now() - start}ms`);
    return result;
  }
}

export class RetryDecorator extends ImageGeneratorDecorator {
  constructor(inner, attempts = 3) {
    super(inner);
    this.attempts = attempts;
  }

  async generate(request, analysis) {
    let lastError;
    for (let i = 0; i < this.attempts; i++) {
      try {
        return await super.generate(request, analysis);
      } catch (err) {
        lastError = err;
      }
    }
    throw lastError;
  }
}
