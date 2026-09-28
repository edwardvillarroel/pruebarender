-- Modelo "oferta real": el descuento BAJA lo que paga el cliente.
--
-- Antes:  precio = base con IVA, precio_original = base inflada (precio/(1-d)).
-- Ahora:  precio = base * (1 - d/100) (lo que paga), precio_original = base.
--
-- Idempotente: guarda en el WHERE que la fila siga en formato viejo (comparando
-- que `precio` todavia no sea el rebajado a partir de `precio_original`).
UPDATE PRODUCTOS
SET PRECIO_ORIGINAL = PRECIO,
    PRECIO = CEIL(PRECIO * (100 - DESCUENTO) / 100)
WHERE DESCUENTO IS NOT NULL
  AND DESCUENTO > 0
  AND PRECIO <> CEIL(PRECIO_ORIGINAL * (100 - DESCUENTO) / 100);