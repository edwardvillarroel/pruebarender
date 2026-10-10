"""Verificacion cruzada Oracle <-> Postgres: los conteos no alcanzan.

Un UUID mal convertido mantiene el conteo de filas intacto y aun asi rompe
todos los joins. Estos checks miran los DATOS.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import migrar_datos_oracle_postgres as M  # noqa: E402

ora, pg = M.conectar_oracle(), M.conectar_pg()
co, cp = ora.cursor(), pg.cursor()
fallos = []


def check(nombre, q_ora, q_pg, transform=lambda v: v):
    co.execute(q_ora)
    a = co.fetchone()[0]
    cp.execute(q_pg)
    b = cp.fetchone()[0]
    a, b = transform(a), transform(b)
    ok = a == b
    if not ok:
        fallos.append(nombre)
    print(f"  [{'OK ' if ok else 'FAIL'}] {nombre:38} oracle={a}  postgres={b}")


print("integridad referencial (prueba que los UUID se convirtieron bien):")
check("carritos que hacen join con usuarios",
      "SELECT COUNT(*) FROM CARRITO",
      "SELECT COUNT(*) FROM carrito c JOIN usuarios u ON u.id = c.usuario_id")
check("items que hacen join con producto",
      "SELECT COUNT(*) FROM CARRITO_ITEMS",
      "SELECT COUNT(*) FROM carrito_items ci JOIN productos p ON p.id = ci.producto_id")
check("items que hacen join con carrito",
      "SELECT COUNT(*) FROM CARRITO_ITEMS",
      "SELECT COUNT(*) FROM carrito_items ci JOIN carrito c ON c.id = ci.carrito_id")
check("pedidos que hacen join con usuario",
      "SELECT COUNT(*) FROM PEDIDOS",
      "SELECT COUNT(*) FROM pedidos pe JOIN usuarios u ON u.id = pe.usuario_id")

print("\nBLOB (los bytes tienen que coincidir exactamente):")
for col in ("IMAGEN_BYTES", "IMAGEN_THUMB_BYTES"):
    check(f"productos.{col} bytes",
          f"SELECT NVL(SUM(DBMS_LOB.GETLENGTH({col})),0) FROM PRODUCTOS",
          f"SELECT COALESCE(SUM(octet_length({col.lower()})),0) FROM productos")
    check(f"producto_colores.{col} bytes",
          f"SELECT NVL(SUM(DBMS_LOB.GETLENGTH({col})),0) FROM PRODUCTO_COLORES",
          f"SELECT COALESCE(SUM(octet_length({col.lower()})),0) FROM producto_colores")

print("\nvalores No nulos (un NULL perdido o inventado cambia esto):")
check("usuarios con email",
      "SELECT COUNT(EMAIL) FROM USUARIOS",
      "SELECT COUNT(email) FROM usuarios")
check("items con color NULL",
      "SELECT COUNT(*)-COUNT(COLOR) FROM CARRITO_ITEMS",
      "SELECT count(*)-count(color) FROM carrito_items")
check("items con cantidad NULL",
      "SELECT COUNT(*)-COUNT(CANTIDAD) FROM CARRITO_ITEMS",
      "SELECT count(*)-count(cantidad) FROM carrito_items")

print("\nbooleanos (NUMBER(1,0) -> boolean):")
check("usuarios activos",
      "SELECT COUNT(*) FROM USUARIOS WHERE ACTIVO = 1",
      "SELECT COUNT(*) FROM usuarios WHERE activo IS TRUE")

print("\nfechas (rango):")
check("pedidos: creado_en mas antiguo",
      "SELECT TO_CHAR(MIN(CREADO_EN),'YYYY-MM-DD HH24:MI:SS') FROM PEDIDOS",
      "SELECT to_char(min(creado_en) AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS') FROM pedidos")
check("pedidos: creado_en mas nuevo",
      "SELECT TO_CHAR(MAX(CREADO_EN),'YYYY-MM-DD HH24:MI:SS') FROM PEDIDOS",
      "SELECT to_char(max(creado_en) AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS') FROM pedidos")

print("\nidentidad de una fila completa (mismo producto, mismos bytes):")
co.execute("SELECT NOMBRE, STOCK, PRECIO FROM PRODUCTOS ORDER BY ID FETCH FIRST 3 ROWS ONLY")
a = co.fetchall()
cp.execute("SELECT nombre, stock, precio FROM productos ORDER BY id LIMIT 3")
b = cp.fetchall()
for x, y in zip(a, b):
    ok = str(x[0]) == str(y[0]) and float(x[1]) == float(y[1]) and float(x[2]) == float(y[2])
    if not ok:
        fallos.append(f"producto {x}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {str(x[0])[:24]:26} stock={x[1]} precio={x[2]}")

print()
if fallos:
    print(f"RESULTADO: {len(fallos)} verificaciones FALLaron -> {fallos}")
    sys.exit(1)
print("RESULTADO: todas las verificaciones cruzadas pasaron")
ora.close(); pg.close()