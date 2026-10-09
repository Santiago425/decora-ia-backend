export const STYLES = ['modern', 'nordic', 'industrial', 'bohemian', 'minimalist'];
export const ROOM_TYPES = ['bedroom', 'living_room', 'kitchen', 'bathroom', 'dining_room', 'office'];

const MAX_URL_LENGTH = 2048;
const MAX_BUDGET = 1_000_000;
const MAX_COLORS = 5;
const HEX_COLOR = /^#[0-9a-f]{6}$/i;

function isHttpUrl(value) {
  if (typeof value !== 'string' || value.length > MAX_URL_LENGTH) return false;
  try {
    const { protocol } = new URL(value);
    return protocol === 'https:' || protocol === 'http:';
  } catch {
    return false;
  }
}

class RemodelRequest {
  constructor({ photoUrl, roomType, style, budget, colors, keepFurniture }) {
    this.photoUrl = photoUrl;
    this.roomType = roomType;
    this.style = style;
    this.budget = budget;
    this.colors = Object.freeze([...colors]);
    this.keepFurniture = keepFurniture;
    Object.freeze(this);
  }
}

// Builder: arma paso a paso una solicitud de remodelación con varios campos opcionales.
export class RemodelRequestBuilder {
  #data = { roomType: 'bedroom', style: 'modern', budget: null, colors: [], keepFurniture: false };

  withPhoto(url) {
    this.#data.photoUrl = typeof url === 'string' ? url.trim() : url;
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
    this.#data.budget = amount == null || amount === '' ? null : Number(amount);
    return this;
  }

  withColors(colors = []) {
    this.#data.colors = Array.isArray(colors) ? [...colors] : colors;
    return this;
  }

  keepingFurniture(keep = true) {
    this.#data.keepFurniture = Boolean(keep);
    return this;
  }

  build() {
    const { photoUrl, roomType, style, budget, colors } = this.#data;
    if (!photoUrl) throw new Error('photoUrl is required');
    if (!isHttpUrl(photoUrl)) throw new Error('photoUrl must be a valid http(s) URL');
    if (!ROOM_TYPES.includes(roomType)) throw new Error(`roomType must be one of: ${ROOM_TYPES.join(', ')}`);
    if (!STYLES.includes(style)) throw new Error(`style must be one of: ${STYLES.join(', ')}`);
    if (budget != null && (!Number.isFinite(budget) || budget < 0 || budget > MAX_BUDGET)) {
      throw new Error(`budget must be a number between 0 and ${MAX_BUDGET}`);
    }
    if (!Array.isArray(colors) || colors.length > MAX_COLORS || !colors.every((c) => HEX_COLOR.test(c))) {
      throw new Error(`colors must be up to ${MAX_COLORS} hex values like #a1b2c3`);
    }
    return new RemodelRequest(this.#data);
  }
}
