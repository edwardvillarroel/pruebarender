import { useEffect, useState } from 'react';
import { productoApi } from '../services/products.js';

const cache = new Map();

export function useMasVendidos(periodo, limite = 10, activo = true) {
  const key = `${periodo}|${limite}`;
  const cached = cache.get(key);

  const [productos, setProductos] = useState(cached?.productos ?? []);
  const [semana, setSemana] = useState(cached?.semana ?? null);
  const [cargando, setCargando] = useState(activo && !cached);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!activo) {
      setProductos([]);
      setSemana(null);
      setCargando(false);
      setError(null);
      return;
    }
    if (cache.has(key)) {
      const c = cache.get(key);
      setProductos(c.productos);
      setSemana(c.semana ?? null);
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
        const prods = res.productos ?? [];
        // `semana` solo viene con `periodo=semana`: dice si el backend mostro
        // la semana actual o la anterior (regla de los 4 productos distintos).
        const meta = res.semana ?? null;
        cache.set(key, { productos: prods, semana: meta });
        setProductos(prods);
        setSemana(meta);
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
  }, [periodo, limite, activo, key]);

  return { productos, cargando: activo ? cargando : false, error, semana };
}
