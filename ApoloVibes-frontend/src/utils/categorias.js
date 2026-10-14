export function slugDeCategoria(nombre) {
    const n = (nombre || '').toLowerCase()
    if (n.includes('videojuegos') || n.includes('cine')) return 'videojuegos-cine'
    if (n.includes('articulados')) return 'articulados'
    if (n.includes('llavero')) return 'llaveros'
    if (n.includes('animales')) return 'animales'
    if (n.includes('accesorios')) return 'accesorios'
    if (n.includes('diseno') || n.includes('diseño') || n.includes('medida')) return 'disenos-a-medida'

    return n.normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

export function rutaDeCategoria(cat) {
    return `/categorias?cat=${slugDeCategoria(cat.nombre)}`
}