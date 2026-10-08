// Abstract Factory: cada proveedor de IA crea su propia familia de productos
// (analizador del cuarto + generador de imagen) que funcionan juntos.
export class AIProviderFactory {
  get name() {
    throw new Error('name not implemented');
  }

  createRoomAnalyzer() {
    throw new Error('createRoomAnalyzer() not implemented');
  }

  createImageGenerator() {
    throw new Error('createImageGenerator() not implemented');
  }
}
