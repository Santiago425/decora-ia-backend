import { Router } from 'express';
import { RemodelRequestBuilder, ROOM_TYPES, STYLES } from '../ai/builders/RemodelRequestBuilder.js';
import { RemodelService } from '../ai/RemodelService.js';

export const remodelRouter = Router();
const service = new RemodelService();

remodelRouter.get('/styles', (_req, res) => {
  res.json(STYLES);
});

remodelRouter.get('/room-types', (_req, res) => {
  res.json(ROOM_TYPES);
});

remodelRouter.post('/remodels/preview', async (req, res, next) => {
  let request;
  try {
    const { photoUrl, roomType, style, budget, colors, keepFurniture } = req.body ?? {};
    request = new RemodelRequestBuilder()
      .withPhoto(photoUrl)
      .forRoom(roomType ?? 'bedroom')
      .withStyle(style ?? 'modern')
      .withBudget(budget)
      .withColors(colors)
      .keepingFurniture(keepFurniture)
      .build();
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }
  try {
    res.json(await service.remodel(request));
  } catch (err) {
    next(err);
  }
});
