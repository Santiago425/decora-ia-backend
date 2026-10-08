import { AIProviderFactory } from './AIProviderFactory.js';
import { RoomAnalyzer } from '../products/RoomAnalyzer.js';
import { ImageGenerator } from '../products/ImageGenerator.js';

const SUGGESTIONS = {
  modern: ['Paredes en gris claro', 'Sofá de líneas rectas', 'Lámpara colgante negra'],
  nordic: ['Piso de madera clara', 'Textiles en lana blanca', 'Plantas pequeñas'],
  industrial: ['Pared de ladrillo visto', 'Estantería metálica', 'Bombillas vintage'],
  bohemian: ['Alfombra de colores', 'Cojines con textura', 'Muchas plantas colgantes'],
  minimalist: ['Quitar objetos sobre muebles', 'Paleta blanco y beige', 'Almacenamiento oculto'],
};

class MockRoomAnalyzer extends RoomAnalyzer {
  async analyze(request) {
    return {
      roomType: request.roomType,
      detectedObjects: ['bed', 'window', 'desk'],
      lighting: 'natural',
    };
  }
}

class MockImageGenerator extends ImageGenerator {
  async generate(request) {
    return {
      imageUrl: `https://placehold.co/1024x768?text=${encodeURIComponent(request.style)}`,
      suggestions: SUGGESTIONS[request.style] ?? SUGGESTIONS.modern,
    };
  }
}

export class MockAIFactory extends AIProviderFactory {
  get name() {
    return 'mock';
  }

  createRoomAnalyzer() {
    return new MockRoomAnalyzer();
  }

  createImageGenerator() {
    return new MockImageGenerator();
  }
}
