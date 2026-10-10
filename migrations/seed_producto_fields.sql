

-- Bulbasaur (impresora resina)
UPDATE productos SET
  specs = '["Material: Resina UV", "Tamaño: 8cm", "Peso: 45g", "Color: Verde"]',
  rating = 5,
  badge = 'Popular'
WHERE id = 'e75e213f-ff0b-4d55-9f2b-a2803f57ea12';

-- Charmander (impresora resina)
UPDATE productos SET
  specs = '["Material: Resina UV", "Tamaño: 8cm", "Peso: 42g", "Color: Naranja"]',
  rating = 5,
  badge = 'Popular'
WHERE id = '0ba6a9e4-8f52-42f7-ba52-d36ce3663dbc';

-- Colgante minimalista achatado (llaveros)
UPDATE productos SET
  descripcion = 'Llavero colgante de diseño minimalista, forma achatada ideal para personalizar.',
  specs = '["Material: PLA+", "Tamaño: 4cm", "Peso: 12g", "Color: Blanco"]',
  rating = 4,
  precio_original = 7990,
  descuento = 25
WHERE id = 'a22e4a80-5b69-40ef-80c7-bf7aa0fbfd35';

-- Llavero flor geometrica (llaveros)
UPDATE productos SET
  descripcion = 'Llavero con diseño de flor geometrica, impreso en 3D con acabado mate.',
  specs = '["Material: PLA+", "Tamaño: 3.5cm", "Peso: 10g", "Color: Rosa"]',
  rating = 4,
  badge = 'Nuevo'
WHERE id = 'da16fb25-e3c7-4324-8ba7-dab72491e1c2';

-- Squirtle (impresora resina)
UPDATE productos SET
  specs = '["Material: Resina UV", "Tamaño: 8cm", "Peso: 40g", "Color: Azul"]',
  rating = 5
WHERE id = '699fd29e-64ad-41e7-9a06-c046d15bebad';
