-- Modelo "oferta real": el descuento BAJA lo que paga el cliente.
--
-- Antes:  precio = base con IVA, precio_original = base inflada (precio/(1-d)).
-- Ahora:  precio = base * (1 - d/100) (lo que paga), precio_original = base.
--
-- Idempotente: guarda en el WHERE que la fila siga en formato viejo (comparando
-- que `precio` todavia no sea el rebajado a partir de `precio_original`).
--
-- `precio`, `precio_original` y `descuento` son `numeric(10,2)` (vienen de
-- NUMBER(10,2) de Oracle), asi que la aritmetica ya es exacta y CEIL no
-- necesita cast. Solo hay que castear el resultado a numeric para no arrastrar
-- un tipo unexpected en la asignacion. Un `::integer` aqui seria un error:
-- truncaria los decimales de un precio.
UPDATE productos
SET precio_original = precio,
    precio = CEIL(precio * (100 - descuento) / 100)
WHERE descuento IS NOT NULL
  AND descuento > 0
  AND precio <> CEIL(precio_original * (100 - descuento) / 100);