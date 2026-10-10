
ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS entrega varchar(20) DEFAULT 'retiro';

ALTER TABLE detalle_pedidos
    ADD COLUMN IF NOT EXISTS nombre varchar(150);

UPDATE detalle_pedidos d
   SET nombre = p.nombre
  FROM productos p
 WHERE p.id = d.producto_id
   AND d.nombre IS NULL;