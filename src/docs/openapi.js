import { ROOM_TYPES, STYLES } from '../ai/builders/RemodelRequestBuilder.js';

const error = (description, message) => ({
  description,
  content: { 'application/json': { schema: { $ref: '#/components/schemas/Error' }, example: { error: message } } },
});

const ok = (description, schema, example) => ({
  description,
  content: { 'application/json': { schema, example } },
});

const sessionExample = {
  token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YjFlLi4uIn0.firma',
  user: {
    id: '7b1e4c2a-9f3d-4e8b-a6c1-2d5f8e9a0b13',
    fullName: 'Ana Pérez',
    email: 'ana@example.com',
    createdAt: '2026-10-09T15:30:00.000Z',
  },
};

export const openapi = {
  openapi: '3.0.3',
  info: {
    title: 'DecoraIA API',
    version: '0.1.0',
    description:
      'API REST de **DecoraIA**: el usuario sube una foto de su espacio, elige un estilo y la IA le propone cómo remodelarlo.\n\n' +
      'Para probar las rutas protegidas: crea una cuenta en `POST /auth/register` o entra en `POST /auth/login`, ' +
      'copia el `token` de la respuesta y pégalo en el botón **Authorize**.',
  },
  servers: [{ url: '/api/v1', description: 'Este servidor' }],
  tags: [
    { name: 'Estado', description: 'Comprobar que el servicio está vivo' },
    { name: 'Autenticación', description: 'Registro, inicio de sesión y datos de la sesión' },
    { name: 'Catálogo', description: 'Opciones disponibles para una remodelación' },
    { name: 'Remodelación', description: 'Propuestas generadas por la IA' },
  ],
  components: {
    securitySchemes: {
      bearerAuth: { type: 'http', scheme: 'bearer', bearerFormat: 'JWT' },
    },
    schemas: {
      Error: {
        type: 'object',
        properties: { error: { type: 'string' } },
        required: ['error'],
      },
      User: {
        type: 'object',
        properties: {
          id: { type: 'string', format: 'uuid' },
          fullName: { type: 'string' },
          email: { type: 'string', format: 'email' },
          createdAt: { type: 'string', format: 'date-time' },
        },
      },
      Session: {
        type: 'object',
        properties: {
          token: { type: 'string', description: 'JWT firmado con HS256, válido por 2 horas' },
          user: { $ref: '#/components/schemas/User' },
        },
      },
      RegisterInput: {
        type: 'object',
        required: ['fullName', 'email', 'password'],
        properties: {
          fullName: { type: 'string', minLength: 2, maxLength: 120 },
          email: { type: 'string', format: 'email', maxLength: 160 },
          password: {
            type: 'string',
            minLength: 8,
            maxLength: 128,
            description: 'Al menos una letra y un número',
          },
        },
      },
      LoginInput: {
        type: 'object',
        required: ['email', 'password'],
        properties: {
          email: { type: 'string', format: 'email' },
          password: { type: 'string', minLength: 8, maxLength: 128 },
        },
      },
      RemodelInput: {
        type: 'object',
        required: ['photoUrl'],
        properties: {
          photoUrl: { type: 'string', format: 'uri', maxLength: 2048, description: 'URL http(s) de la foto del espacio' },
          roomType: { type: 'string', enum: ROOM_TYPES, default: 'bedroom' },
          style: { type: 'string', enum: STYLES, default: 'modern' },
          budget: { type: 'number', minimum: 0, maximum: 1000000, nullable: true, description: 'Presupuesto en dólares' },
          colors: {
            type: 'array',
            maxItems: 5,
            items: { type: 'string', pattern: '^#[0-9a-fA-F]{6}$' },
            description: 'Paleta deseada en hexadecimal',
          },
          keepFurniture: { type: 'boolean', default: false, description: 'Conservar los muebles actuales' },
        },
      },
      RemodelResult: {
        type: 'object',
        properties: {
          provider: { type: 'string', description: 'Proveedor de IA que generó la propuesta (mock o external)' },
          analysis: {
            type: 'object',
            properties: {
              roomType: { type: 'string' },
              detectedObjects: { type: 'array', items: { type: 'string' } },
              lighting: { type: 'string' },
            },
          },
          imageUrl: { type: 'string', format: 'uri' },
          suggestions: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
  paths: {
    '/hello': {
      get: {
        tags: ['Estado'],
        summary: 'Hello World del backend',
        responses: {
          200: ok(
            'El backend responde',
            {
              type: 'object',
              properties: {
                message: { type: 'string' },
                service: { type: 'string' },
                timestamp: { type: 'string', format: 'date-time' },
              },
            },
            { message: 'Hello World desde DecoraIA', service: 'decora-ia-backend', timestamp: '2026-10-09T15:30:00.000Z' },
          ),
        },
      },
    },
    '/health': {
      get: {
        tags: ['Estado'],
        summary: 'Estado de la API y de la base de datos',
        responses: {
          200: ok(
            'API y base de datos funcionando',
            {
              type: 'object',
              properties: {
                api: { type: 'string' },
                database: { type: 'string' },
                server_time: { type: 'string', format: 'date-time' },
                styles: { type: 'integer', description: 'Estilos guardados en la tabla design_styles' },
              },
            },
            { api: 'up', database: 'up', server_time: '2026-10-09T15:30:00.000Z', styles: 5 },
          ),
          503: ok(
            'La base de datos no está configurada o no responde',
            { type: 'object', properties: { api: { type: 'string' }, database: { type: 'string' } } },
            { api: 'up', database: 'down' },
          ),
        },
      },
    },
    '/auth/register': {
      post: {
        tags: ['Autenticación'],
        summary: 'Crear una cuenta',
        description: 'Crea el usuario y devuelve directamente una sesión iniciada. Máximo 10 intentos fallidos cada 15 minutos por IP.',
        requestBody: {
          required: true,
          content: {
            'application/json': {
              schema: { $ref: '#/components/schemas/RegisterInput' },
              example: { fullName: 'Ana Pérez', email: 'ana@example.com', password: 'secreta123' },
            },
          },
        },
        responses: {
          201: ok('Cuenta creada', { $ref: '#/components/schemas/Session' }, sessionExample),
          400: error('Datos inválidos', 'La contraseña debe tener al menos una letra y un número'),
          409: error('El correo ya está registrado', 'Ya existe una cuenta con ese correo'),
          429: error('Demasiados intentos', 'Demasiados intentos, espera unos minutos e inténtalo de nuevo'),
        },
      },
    },
    '/auth/login': {
      post: {
        tags: ['Autenticación'],
        summary: 'Iniciar sesión',
        description: 'Devuelve un token JWT para usar en la cabecera `Authorization: Bearer <token>`.',
        requestBody: {
          required: true,
          content: {
            'application/json': {
              schema: { $ref: '#/components/schemas/LoginInput' },
              example: { email: 'ana@example.com', password: 'secreta123' },
            },
          },
        },
        responses: {
          200: ok('Sesión iniciada', { $ref: '#/components/schemas/Session' }, sessionExample),
          400: error('Datos inválidos', 'Ingresa un correo válido'),
          401: error('Credenciales incorrectas', 'Correo o contraseña incorrectos'),
          429: error('Demasiados intentos', 'Demasiados intentos, espera unos minutos e inténtalo de nuevo'),
        },
      },
    },
    '/auth/me': {
      get: {
        tags: ['Autenticación'],
        summary: 'Datos del usuario de la sesión',
        security: [{ bearerAuth: [] }],
        responses: {
          200: ok(
            'Usuario autenticado',
            { type: 'object', properties: { user: { $ref: '#/components/schemas/User' } } },
            { user: sessionExample.user },
          ),
          401: error('Sin sesión o token vencido', 'Inicia sesión para continuar'),
        },
      },
    },
    '/styles': {
      get: {
        tags: ['Catálogo'],
        summary: 'Estilos de diseño disponibles',
        responses: {
          200: ok('Lista de estilos', { type: 'array', items: { type: 'string', enum: STYLES } }, STYLES),
        },
      },
    },
    '/room-types': {
      get: {
        tags: ['Catálogo'],
        summary: 'Tipos de espacio disponibles',
        responses: {
          200: ok('Lista de tipos de espacio', { type: 'array', items: { type: 'string', enum: ROOM_TYPES } }, ROOM_TYPES),
        },
      },
    },
    '/remodels/preview': {
      post: {
        tags: ['Remodelación'],
        summary: 'Generar una propuesta de remodelación',
        description:
          'Analiza la foto del espacio y devuelve una imagen remodelada con el estilo elegido y una lista de sugerencias. ' +
          'El proveedor de IA es intercambiable (`AI_PROVIDER`).',
        security: [{ bearerAuth: [] }],
        requestBody: {
          required: true,
          content: {
            'application/json': {
              schema: { $ref: '#/components/schemas/RemodelInput' },
              example: {
                photoUrl: 'https://example.com/cuarto.jpg',
                roomType: 'bedroom',
                style: 'nordic',
                budget: 500,
                colors: ['#f5f0e6', '#7a8b6f'],
                keepFurniture: true,
              },
            },
          },
        },
        responses: {
          200: ok('Propuesta generada', { $ref: '#/components/schemas/RemodelResult' }, {
            provider: 'mock',
            analysis: { roomType: 'bedroom', detectedObjects: ['bed', 'window', 'desk'], lighting: 'natural' },
            imageUrl: 'https://placehold.co/1024x768?text=nordic',
            suggestions: ['Piso de madera clara', 'Textiles en lana blanca', 'Plantas pequeñas'],
          }),
          400: error('Datos inválidos', 'photoUrl must be a valid http(s) URL'),
          401: error('Sin sesión o token vencido', 'Inicia sesión para continuar'),
          429: error('Demasiadas solicitudes', 'Demasiadas solicitudes, intenta de nuevo en un minuto'),
        },
      },
    },
  },
};
