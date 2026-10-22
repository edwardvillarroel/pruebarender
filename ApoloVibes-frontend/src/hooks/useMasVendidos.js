import { useEffect, useState } from 'react';
import { productoApi } from '../services/products.js';

const cache = new Map();

export function useMasVendidos(periodo, limite = 10, activo = true) {
  const key = `${periodo}|${limite}`;
  const cached = cache.get(key);

  const [productos, setProductos] = useState(cached?.productos ?? []);
  const [cargando, setCargando] = useState(activo && !cached);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!activo) {
      setProductos([]);
      setCargando(false);
      setError(null);
      return;
    }
    if (cache.has(key)) {
      const c = cache.get(key);
      setProductos(c.productos);
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
        cache.set(key, { productos: prods });
        setProductos(prods);
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

  return { productos, cargando: activo ? cargando : false, error };
}
