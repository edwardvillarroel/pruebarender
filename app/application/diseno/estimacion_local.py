def estimacion_local(alto, ancho, largo, cantidad, material_usuario):
    try:
        volumen = float(alto) * float(ancho) * float(largo) * 0.30
    except Exception:
        volumen = 10.0
    gramos = max(5.0, volumen * 1.24)
    precio_unitario = round(2500 + gramos * 120)
    precio_total = precio_unitario * int(cantidad or 1)
    tiempo = round(max(0.5, gramos / 15), 1)
    return {
        "precio_estimado_ia": precio_total,
        "precio_unitario_ia": precio_unitario,
        "gramos_estimados_ia": round(gramos, 1),
        "tiempo_estimado_horas_ia": tiempo,
        "material_sugerido_ia": material_usuario or "PLA+",
        "complejidad_ia": "Media",
        "confianza_material_ia": 0.5,
        "confianza_complejidad_ia": 0.5,
        "ia_origen": "cotizador-fallback-local-429",
    }
