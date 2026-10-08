import { RoomAnalyzer } from '../products/RoomAnalyzer.js';
import { ImageGenerator } from '../products/ImageGenerator.js';

// Adapter: traduce la API HTTP del servicio de IA externo (snake_case, su propio
// formato de respuesta) a las interfaces RoomAnalyzer e ImageGenerator del backend.
export class AIServiceClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async post(path, body) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`AI service responded ${res.status}`);
    return res.json();
  }
}

export class AIServiceAnalyzerAdapter extends RoomAnalyzer {
  constructor(client) {
    super();
    this.client = client;
  }

  async analyze(request) {
    const data = await this.client.post('/analyze', {
      image_url: request.photoUrl,
      room_type: request.roomType,
    });
    return {
      roomType: data.room_type,
      detectedObjects: data.objects ?? [],
      lighting: data.lighting ?? 'unknown',
    };
  }
}

export class AIServiceGeneratorAdapter extends ImageGenerator {
  constructor(client) {
    super();
    this.client = client;
  }

  async generate(request, analysis) {
    const data = await this.client.post('/remodel', {
      image_url: request.photoUrl,
      style: request.style,
      budget: request.budget,
      colors: request.colors,
      keep_furniture: request.keepFurniture,
      detected_objects: analysis?.detectedObjects ?? [],
    });
    return {
      imageUrl: data.output_image_url,
      suggestions: data.tips ?? [],
    };
  }
}
