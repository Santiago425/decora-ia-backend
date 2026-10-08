export const STYLES = ['modern', 'nordic', 'industrial', 'bohemian', 'minimalist'];

class RemodelRequest {
  constructor({ photoUrl, roomType, style, budget, colors, keepFurniture }) {
    this.photoUrl = photoUrl;
    this.roomType = roomType;
    this.style = style;
    this.budget = budget;
    this.colors = colors;
    this.keepFurniture = keepFurniture;
    Object.freeze(this);
  }
}

// Builder: arma paso a paso una solicitud de remodelación con varios campos opcionales.
export class RemodelRequestBuilder {
  #data = { roomType: 'bedroom', style: 'modern', budget: null, colors: [], keepFurniture: false };

  withPhoto(url) {
    this.#data.photoUrl = url;
    return this;
  }

  forRoom(roomType) {
    this.#data.roomType = roomType;
    return this;
  }

  withStyle(style) {
    this.#data.style = style;
    return this;
  }

  withBudget(amount) {
    this.#data.budget = amount == null ? null : Number(amount);
    return this;
  }

  withColors(colors = []) {
    this.#data.colors = [...colors];
    return this;
  }

  keepingFurniture(keep = true) {
    this.#data.keepFurniture = Boolean(keep);
    return this;
  }

  build() {
    const { photoUrl, style, budget } = this.#data;
    if (!photoUrl) throw new Error('photoUrl is required');
    if (!STYLES.includes(style)) throw new Error(`style must be one of: ${STYLES.join(', ')}`);
    if (budget != null && (Number.isNaN(budget) || budget < 0)) throw new Error('budget must be a positive number');
    return new RemodelRequest(this.#data);
  }
}
