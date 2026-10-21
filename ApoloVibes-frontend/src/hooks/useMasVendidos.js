import { useEffect, useState } from 'react';
import { productoApi } from '../services/products.js';

/**
 * Carga el ranking de "más vendidos" para un periodo (`7d`, `30d` o `todo`).
 *
 * `activo` permite no pedirlo hasta que el usuario abre el filtro: el
 * ranking de la seccion de arriba y el de la grilla de categorias son el
 * mismo endpoint, pero el de la grilla solo se pide cuando se entra a el.
 *
 * El `periodo` va en las dependencias del efecto, asi que cambiar el
 * desplegable vuelve a consultar el backend con la ventana nueva.
 */
export function useMasVendidos(periodo, limite = 10, activo = true) {
  const [productos, setProductos] = useState([]);
  const [cargando, setCargando] = useState(activo);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!activo) {
      setProductos([]);
      setCargando(false);
      setError(null);
      return;
    }
    let vigente = true;
    setCargando(true);
    setError(null);
    productoApi
      .masVendidos(periodo, limite)
      .then((res) => {
        if (!vigente) return;
        setProductos(res.productos ?? []);
        setCargando(false);
      })
      .catch((err) => {
        if (!vigente) return;
        setError(err.message);
        setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, [periodo, limite, activo]);

  return { productos, cargando, error };
}
