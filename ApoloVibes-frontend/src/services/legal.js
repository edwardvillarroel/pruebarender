export const VERSION_LEGAL = '2026-10-04'

export function fechaLegalLarga(iso = VERSION_LEGAL){
    const [a, m, d] = iso.split('-').map(Number)
    return new Date(a, m - 1, d).toLocaleDateString('es-CL', { 
        day: 'numeric', month: 'long', year: 'numeric'
    })
}