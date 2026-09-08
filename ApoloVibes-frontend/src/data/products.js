import { mediaPath } from '../utils/media.js'

export const categorias = [
  { id: 'figuras', nombre: 'Figuras de Colección', cantidad: 32 },
  { id: 'impresoras-resina', nombre: 'Impresoras de resina', cantidad: 14 },
  { id: 'llaveros', nombre: 'Llaveros', cantidad: 180 },
  { id: 'animales', nombre: 'Animales', cantidad: 120 },
  { id: 'anime', nombre: 'Figuras de Anime', cantidad: 210 },
  { id: 'diseno', nombre: 'Diseños a medida', cantidad: null },
]

export const productos = [
  {
    id: 'p1',
    nombre: 'Charmander',
    categoria: 'figuras',
    precio: 30000,
    badge: 'NUEVO',
    imagen: mediaPath('charmander.jpg'),
    descripcion: 'Figura de colección Charmander, pintada a mano con acabado en resina de alta definición. Ideal para exhibir o regalar.',
    specs: ['Material: resina', 'Altura: 12cm', 'Pintado a mano'],
  },
  { id: 'p2', nombre: 'PETG translúcido 1.75mm · 1kg', categoria: 'llaveros', precio: 12665, precioOriginal: 14900, descuento: '15', imagen: mediaPath('charmander.jpg') },
  { id: 'p3', nombre: 'Resina de alta precisión 0.5L', categoria: 'animales', precio: 22500, sinStock: true, imagen: mediaPath('charmander.jpg') },
  { id: 'p4', nombre: 'Kit boquillas endurecidas 0.4mm', categoria: 'anime', precio: 9200, imagen: mediaPath('charmander.jpg') },
]
