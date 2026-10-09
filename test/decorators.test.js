import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { ImageGenerator } from '../src/ai/products/ImageGenerator.js';
import {
  ImageGeneratorDecorator,
  LoggingDecorator,
  RetryDecorator,
} from '../src/ai/decorators/ImageGeneratorDecorators.js';

const RESULT = { imageUrl: 'https://example.com/out.jpg', suggestions: ['lámpara'] };
const REQUEST = { style: 'nordic' };
const ANALYSIS = { light: 'low' };

// Generador falso: falla las primeras `failures` veces y luego devuelve RESULT.
function fakeGenerator({ failures = 0 } = {}) {
  const calls = [];
  const generator = new ImageGenerator();
  generator.generate = async (request, analysis) => {
    calls.push({ request, analysis });
    if (calls.length <= failures) throw new Error(`fallo ${calls.length}`);
    return RESULT;
  };
  generator.calls = calls;
  return generator;
}

// Logger falso: guarda los mensajes en lugar de imprimirlos.
function fakeLogger() {
  const messages = [];
  return { messages, info: (message) => messages.push(message) };
}

describe('ImageGeneratorDecorator (base)', () => {
  test('es un ImageGenerator', () => {
    const decorator = new ImageGeneratorDecorator(fakeGenerator());
    assert.ok(decorator instanceof ImageGenerator);
  });

  test('delega en el generador interno sin alterar argumentos ni resultado', async () => {
    const inner = fakeGenerator();
    const result = await new ImageGeneratorDecorator(inner).generate(REQUEST, ANALYSIS);
    assert.equal(result, RESULT);
    assert.equal(inner.calls.length, 1);
    assert.equal(inner.calls[0].request, REQUEST);
    assert.equal(inner.calls[0].analysis, ANALYSIS);
  });
});

describe('RetryDecorator', () => {
  test('no reintenta si funciona a la primera', async () => {
    const inner = fakeGenerator();
    const result = await new RetryDecorator(inner, 3).generate(REQUEST, ANALYSIS);
    assert.equal(result, RESULT);
    assert.equal(inner.calls.length, 1);
  });

  test('reintenta hasta tener éxito', async () => {
    const inner = fakeGenerator({ failures: 2 });
    const result = await new RetryDecorator(inner, 3).generate(REQUEST, ANALYSIS);
    assert.equal(result, RESULT);
    assert.equal(inner.calls.length, 3);
  });

  test('se rinde al agotar los intentos y lanza el último error', async () => {
    const inner = fakeGenerator({ failures: 10 });
    await assert.rejects(() => new RetryDecorator(inner, 3).generate(REQUEST, ANALYSIS), /fallo 3/);
    assert.equal(inner.calls.length, 3);
  });

  test('usa 3 intentos por defecto', async () => {
    const inner = fakeGenerator({ failures: 10 });
    await assert.rejects(() => new RetryDecorator(inner).generate(REQUEST, ANALYSIS));
    assert.equal(inner.calls.length, 3);
  });

  test('respeta un número de intentos personalizado', async () => {
    const five = fakeGenerator({ failures: 10 });
    await assert.rejects(() => new RetryDecorator(five, 5).generate(REQUEST, ANALYSIS));
    assert.equal(five.calls.length, 5);

    const one = fakeGenerator({ failures: 10 });
    await assert.rejects(() => new RetryDecorator(one, 1).generate(REQUEST, ANALYSIS));
    assert.equal(one.calls.length, 1);
  });

  test('envía los mismos request y analysis en cada reintento', async () => {
    const inner = fakeGenerator({ failures: 1 });
    await new RetryDecorator(inner, 3).generate(REQUEST, ANALYSIS);
    assert.equal(inner.calls[1].request, REQUEST);
    assert.equal(inner.calls[1].analysis, ANALYSIS);
  });
});

describe('LoggingDecorator', () => {
  test('registra el estilo y el tiempo con logger.info', async () => {
    const logger = fakeLogger();
    await new LoggingDecorator(fakeGenerator(), logger).generate(REQUEST, ANALYSIS);
    assert.equal(logger.messages.length, 1);
    assert.match(logger.messages[0], /^\[ai\] style=nordic took \d+ms$/);
  });

  test('devuelve el resultado sin alterarlo', async () => {
    const result = await new LoggingDecorator(fakeGenerator(), fakeLogger()).generate(REQUEST, ANALYSIS);
    assert.equal(result, RESULT);
  });

  test('no registra nada y propaga el error si el generador falla', async () => {
    const logger = fakeLogger();
    const inner = fakeGenerator({ failures: 1 });
    await assert.rejects(() => new LoggingDecorator(inner, logger).generate(REQUEST, ANALYSIS), /fallo 1/);
    assert.equal(logger.messages.length, 0);
  });

  test('usa console como logger por defecto', () => {
    assert.equal(new LoggingDecorator(fakeGenerator()).logger, console);
  });
});

describe('Decoradores apilados', () => {
  test('Logging(Retry(generador)) reintenta y registra una sola vez', async () => {
    const logger = fakeLogger();
    const inner = fakeGenerator({ failures: 2 });
    const stacked = new LoggingDecorator(new RetryDecorator(inner, 3), logger);

    const result = await stacked.generate(REQUEST, ANALYSIS);

    assert.equal(result, RESULT);
    assert.equal(inner.calls.length, 3);
    assert.equal(logger.messages.length, 1);
  });
});
