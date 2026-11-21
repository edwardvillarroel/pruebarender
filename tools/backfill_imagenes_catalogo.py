import os, mimetypes, requests, psycopg2

DB = os.environ["DATABASE_URL"]
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
BUCKET = "catalogo"

conn = psycopg2.connect(DB)
cur = conn.cursor()
cur.execute("""
    select distinct on (p.id)
      p.id, pc.imagen_bytes, pc.imagen_content_type
    from productos p
    join producto_colores pc on pc.producto_id = p.id
    where p.activo = true
      and (p.imagen_url is null or p.imagen_url = '')
      and pc.imagen_bytes is not null
    order by p.id, pc.orden asc, pc.creado_en asc
""")
for pid, data, ctype in cur.fetchall():
    ext = mimetypes.guess_extension(ctype or "") or ".bin"
    path = f"productos/{pid}{ext}"
    up = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}",
        headers={
            "Authorization": f"Bearer {SERVICE_KEY}",
            "apikey": SERVICE_KEY,
            "Content-Type": ctype or "application/octet-stream",
            "x-upsert": "true",
        },
        data=bytes(data),
    )
    up.raise_for_status()
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
    cur.execute("update productos set imagen_url=%s where id=%s", (public_url, pid))
    conn.commit()
    print("ok", pid, public_url)
cur.close(); conn.close()