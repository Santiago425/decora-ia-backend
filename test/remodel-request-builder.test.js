import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  RemodelRequestBuilder,
  STYLES,
  ROOM_TYPES,
} from '../src/ai/builders/RemodelRequestBuilder.js';

const PHOTO = 'https://example.com/cuarto.jpg';
const valid = () => new RemodelRequestBuilder().withPhoto(PHOTO);

describe('RemodelRequestBuilder: construcción', () => {
  test('usa valores por defecto cuando solo se da la foto', () => {
    const request = valid().build();
    assert.equal(request.photoUrl, PHOTO);
    assert.equal(request.roomType, 'bedroom');
    assert.equal(request.style, 'modern');
    assert.equal(request.budget, null);
    assert.deepEqual([...request.colors], []);
    assert.equal(request.keepFurniture, false);
  });

  test('permite encadenar todos los pasos', () => {
    const request = new RemodelRequestBuilder()
      .withPhoto(PHOTO)
      .forRoom('kitchen')
      .withStyle('nordic')
      .withBudget(500)
      .withColors(['#a1b2c3', '#FFFFFF'])
      .keepingFurniture()
      .build();
    assert.equal(request.roomType, 'kitchen');
    assert.equal(request.style, 'nordic');
    assert.equal(request.budget, 500);
    assert.deepEqual([...request.colors], ['#a1b2c3', '#FFFFFF']);
    assert.equal(request.keepFurniture, true);
  });

  test('cada paso devuelve el mismo builder', () => {
    const builder = new RemodelRequestBuilder();
    assert.equal(builder.withPhoto(PHOTO), builder);
    assert.equal(builder.forRoom('office'), builder);
    assert.equal(builder.withStyle('modern'), builder);
    assert.equal(builder.withBudget(10), builder);
    assert.equal(builder.withColors([]), builder);
    assert.equal(builder.keepingFurniture(false), builder);
  });

  test('recorta los espacios de la URL', () => {
    const request = new RemodelRequestBuilder().withPhoto('  ' + PHOTO + '  ').build();
    assert.equal(request.photoUrl, PHOTO);
  });

  test('acepta todos los estilos y tipos de espacio válidos', () => {
    for (const style of STYLES) {
      assert.doesNotThrow(() => valid().withStyle(style).build());
    }
    for (const room of ROOM_TYPES) {
      assert.doesNotThrow(() => valid().forRoom(room).build());
    }
  });
});

describe('RemodelRequestBuilder: foto', () => {
  test('exige photoUrl', () => {
    assert.throws(() => new RemodelRequestBuilder().build(), /photoUrl is required/);
  });

  test('rechaza esquemas peligrosos o no http(s)', () => {
    for (const url of ['javascript:alert(1)', 'file:///etc/passwd', 'ftp://example.com/a.jpg']) {
      assert.throws(
        () => new RemodelRequestBuilder().withPhoto(url).build(),
        /valid http\(s\) URL/,
        url,
      );
    }
  });

  test('rechaza texto que no es una URL', () => {
    assert.throws(() => new RemodelRequestBuilder().withPhoto('no es url').build(), /valid http\(s\) URL/);
  });

  test('rechaza URLs de más de 2048 caracteres', () => {
    const longUrl = 'https://example.com/' + 'a'.repeat(2048);
    assert.throws(() => new RemodelRequestBuilder().withPhoto(longUrl).build(), /valid http\(s\) URL/);
  });

  test('acepta http y https', () => {
    assert.doesNotThrow(() => new RemodelRequestBuilder().withPhoto('http://example.com/a.jpg').build());
    assert.doesNotThrow(() => new RemodelRequestBuilder().withPhoto('https://example.com/a.jpg').build());
  });
});

describe('RemodelRequestBuilder: estilo y tipo de espacio', () => {
  test('rechaza un estilo desconocido', () => {
    assert.throws(() => valid().withStyle('barroco').build(), /style must be one of/);
  });

  test('rechaza un tipo de espacio desconocido', () => {
    assert.throws(() => valid().forRoom('garage').build(), /roomType must be one of/);
  });
});

describe('RemodelRequestBuilder: presupuesto', () => {
  test('acepta 0, el máximo y textos numéricos', () => {
    assert.equal(valid().withBudget(0).build().budget, 0);
    assert.equal(valid().withBudget(1_000_000).build().budget, 1_000_000);
    assert.equal(valid().withBudget('500').build().budget, 500);
  });

  test('null, undefined y cadena vacía significan sin presupuesto', () => {
    assert.equal(valid().withBudget(null).build().budget, null);
    assert.equal(valid().withBudget(undefined).build().budget, null);
    assert.equal(valid().withBudget('').build().budget, null);
  });

  test('rechaza negativos, pasarse del máximo y valores no numéricos', () => {
    for (const bad of [-1, 1_000_001, 'abc', Infinity]) {
      assert.throws(() => valid().withBudget(bad).build(), /budget must be a number/, String(bad));
    }
  });
});

describe('RemodelRequestBuilder: colores', () => {
  test('acepta hasta 5 colores hexadecimales, en mayúscula o minúscula', () => {
    const colors = ['#000000', '#ffffff', '#A1B2C3', '#a1b2c3', '#123abc'];
    assert.equal(valid().withColors(colors).build().colors.length, 5);
  });

  test('rechaza más de 5 colores', () => {
    const colors = Array(6).fill('#000000');
    assert.throws(() => valid().withColors(colors).build(), /colors must be up to 5/);
  });

  test('rechaza formatos de color inválidos', () => {
    for (const bad of ['#fff', 'red', '#12345g', 'a1b2c3', '#a1b2c3ff']) {
      assert.throws(() => valid().withColors([bad]).build(), /colors must be up to 5/, bad);
    }
  });

  test('rechaza colores que no son una lista', () => {
    assert.throws(() => valid().withColors('#000000').build(), /colors must be up to 5/);
  });
});

describe('RemodelRequestBuilder: inmutabilidad', () => {
  test('la solicitud construida no se puede modificar', () => {
    const request = valid().withColors(['#000000']).build();
    assert.throws(() => { request.style = 'nordic'; }, TypeError);
    assert.throws(() => { request.colors.push('#ffffff'); }, TypeError);
  });

  test('cambiar el arreglo original no afecta la solicitud', () => {
    const colors = ['#000000'];
    const request = valid().withColors(colors).build();
    colors.push('#ffffff');
    assert.deepEqual([...request.colors], ['#000000']);
  });
});
