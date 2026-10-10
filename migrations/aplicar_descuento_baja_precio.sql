
UPDATE productos
SET precio_original = precio,
    precio = CEIL(precio * (100 - descuento) / 100)
WHERE descuento IS NOT NULL
  AND descuento > 0
  AND precio <> CEIL(precio_original * (100 - descuento) / 100);