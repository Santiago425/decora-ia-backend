import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Database } from '../src/db/Database.js';
import { RemodelRequestBuilder } from '../src/ai/builders/RemodelRequestBuilder.js';
import { RetryDecorator } from '../src/ai/decorators/ImageGeneratorDecorators.js';
import { ImageGenerator } from '../src/ai/products/ImageGenerator.js';
import { createAIFactory } from '../src/ai/RemodelService.js';

test('Singleton: Database always returns the same instance', () => {
  assert.equal(Database.getInstance(), Database.getInstance());
  assert.throws(() => new Database());
});

test('Builder: validates the style', () => {
  assert.throws(() => new RemodelRequestBuilder().withPhoto('https://example.com/room.jpg').withStyle('gothic').build());
  const req = new RemodelRequestBuilder().withPhoto('https://example.com/room.jpg').withBudget('500').build();
  assert.equal(req.budget, 500);
  assert.ok(Object.isFrozen(req));
});

test('Abstract Factory: mock factory creates a matching family', () => {
  const factory = createAIFactory('mock');
  assert.ok(factory.createImageGenerator() instanceof ImageGenerator);
  assert.equal(typeof factory.createRoomAnalyzer().analyze, 'function');
});

test('Decorator: RetryDecorator retries until success', async () => {
  let calls = 0;
  const flaky = new (class extends ImageGenerator {
    async generate() {
      calls++;
      if (calls < 3) throw new Error('fail');
      return { imageUrl: 'ok' };
    }
  })();
  const result = await new RetryDecorator(flaky, 3).generate({});
  assert.equal(result.imageUrl, 'ok');
  assert.equal(calls, 3);
});

test('Builder: rejects unsafe photo URLs and invalid colors', () => {
  assert.throws(() => new RemodelRequestBuilder().withPhoto('javascript:alert(1)').build());
  assert.throws(() => new RemodelRequestBuilder().withPhoto('file:///etc/passwd').build());
  assert.throws(() => new RemodelRequestBuilder().withPhoto('https://a.com/x.jpg').withColors(['red']).build());
  assert.throws(() => new RemodelRequestBuilder().withPhoto('https://a.com/x.jpg').forRoom('garage').build());
});
