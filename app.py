import streamlit as st
import sqlite3, datetime, uuid, io, base64, random
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ─────────────────────────────────────────────────────────
#  CONFIGURACION
# ─────────────────────────────────────────────────────────
st.set_page_config(page_title="ServiScan", page_icon="📦", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Syne', sans-serif !important; }
.stApp { background: #0D1117; color: #E6EDF3; }
section[data-testid="stSidebar"] { background: #161B22; border-right: 1px solid #30363D; }
section[data-testid="stSidebar"] * { color: #E6EDF3 !important; }
[data-testid="metric-container"] { background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px !important; }
[data-testid="metric-container"] label { color: #7D8590 !important; font-size: .75rem !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #3FB950 !important; font-size: 1.8rem !important; font-family: 'Syne', sans-serif !important; }
.stButton > button { background: #21262D !important; color: #58A6FF !important; border: 1px solid #30363D !important; border-radius: 8px !important; font-family: 'DM Sans', sans-serif !important; }
.stButton > button:hover { border-color: #58A6FF !important; }
.stTextInput > div > div > input, .stTextArea textarea, .stSelectbox > div > div { background: #161B22 !important; border: 1px solid #30363D !important; color: #E6EDF3 !important; border-radius: 8px !important; }
.stDataFrame { border: 1px solid #30363D; border-radius: 8px; }
hr { border-color: #30363D; }
.card { background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px; margin: 8px 0; }
.bc-box { background: white; border-radius: 8px; padding: 16px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
#  BASE DE DATOS
# ─────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect("servicios.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS servicios (
            id          TEXT PRIMARY KEY,
            cliente     TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            categoria   TEXT DEFAULT 'General',
            estado      TEXT DEFAULT 'Pendiente',
            tecnico     TEXT DEFAULT '',
            creado_en   TEXT NOT NULL,
            actualizado TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id          TEXT PRIMARY KEY,
            servicio_id TEXT NOT NULL,
            accion      TEXT NOT NULL,
            detalle     TEXT DEFAULT '',
            fecha       TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def nuevo_id():
    fecha = datetime.datetime.now().strftime("%Y%m%d")
    codigo = str(uuid.uuid4().int)[:4]
    return f"SVC-{fecha}-{codigo}"

def agregar_historial(servicio_id, accion, detalle=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO historial(id,servicio_id,accion,detalle,fecha) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), servicio_id, accion, detalle,
         datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()

def crear_servicio(cliente, descripcion, categoria, estado, tecnico):
    conn = get_db()
    sid  = nuevo_id()
    now  = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    conn.execute(
        "INSERT INTO servicios(id,cliente,descripcion,categoria,estado,tecnico,creado_en,actualizado)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (sid, cliente, descripcion, categoria, estado, tecnico, now, now)
    )
    conn.commit()
    conn.close()
    agregar_historial(sid, "CREADO", f"Cliente: {cliente} | Estado: {estado}")
    return sid

def todos_los_servicios():
    conn = get_db()
    rows = conn.execute("SELECT * FROM servicios ORDER BY creado_en DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def buscar_por_id(sid):
    conn = get_db()
    r = conn.execute("SELECT * FROM servicios WHERE id=?", (sid,)).fetchone()
    conn.close()
    return dict(r) if r else None

def actualizar_estado(sid, nuevo_estado, tecnico):
    conn = get_db()
    now  = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    conn.execute(
        "UPDATE servicios SET estado=?, tecnico=?, actualizado=? WHERE id=?",
        (nuevo_estado, tecnico, now, sid)
    )
    conn.commit()
    conn.close()
    agregar_historial(sid, "ACTUALIZADO", f"Nuevo estado: {nuevo_estado}")

def historial_de(sid):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM historial WHERE servicio_id=? ORDER BY fecha ASC", (sid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─────────────────────────────────────────────────────────
#  GENERADOR DE CODIGO DE BARRA  (Code 128 / ISO-15420)
# ─────────────────────────────────────────────────────────
_CS = ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'
_PT = ["11011001100","11001101100","11001100110","10010011000","10010001100","10001001100","10011001000","10011000100","10001100100","11001001000","11001000100","11000100100","10110011100","10011011100","10011001110","10111001100","10011101100","10011100110","11001110010","11001011100","11001001110","11011100100","11001110100","11101101110","11101001100","11100101100","11100100110","11101100100","11100110100","11100110010","11011011000","11011000110","11000110110","10100011000","10001011000","10001000110","10110001000","10001101000","10001100010","11010001000","11000101000","11000100010","10110111000","10110001110","10001101110","10111011000","10111000110","10001110110","11101110110","11010001110","11000101110","11011101000","11011100010","11011101110","11101011000","11101000110","11100010110","11101101000","11101100010","11100011010","11101111010","11001000010","11110001010","10100110000","10100001100","10010110000","10010000110","10000101100","10000100110","10110010000","10110000100","10011010000","10011000010","10000110100","10000110010","11000010010","11001010000","11110111010","11000010100","10001111010","10100111100","10010111100","10010011110","10111100100","10011110100","10011110010","11110100100","11110010100","11110010010","11011011110","11011110110","11110110110","10101111000","10100011110","10001011110","10111101000","10111100010","11110101000","11110100010","10111011110","10111101110","11101011110","11110101110","11010000100","11010010000","11010011100","1100011101011"]

def hacer_barcode(texto):
    """Genera imagen PNG del codigo de barra (Code 128, ISO/IEC 15420)."""
    codigos = [104]; ck = 104
    for i, c in enumerate(texto):
        v = _CS.find(c)
        v = 0 if v < 0 else v
        codigos.append(v); ck += v * (i + 1)
    codigos.append(ck % 103); codigos.append(106)
    patron = "".join(_PT[c] for c in codigos if c < len(_PT))

    escala = 2
    zona   = 10 * escala
    ancho  = len(patron) * escala + 2 * zona
    alto   = 90
    img    = Image.new("RGB", (ancho, alto + 20), "white")
    draw   = ImageDraw.Draw(img)
    x = zona
    for bit in patron:
        if bit == "1":
            draw.rectangle([x, 4, x + escala - 1, alto], fill="black")
        x += escala
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except Exception:
        font = ImageFont.load_default()
    tw = draw.textlength(texto, font=font) if hasattr(draw,"textlength") else len(texto)*6
    draw.text(((ancho - tw)/2, alto + 4), texto, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()

def mostrar_barcode(texto, ancho=350):
    datos = hacer_barcode(texto)
    b64   = base64.b64encode(datos).decode()
    st.markdown(
        f'<div class="bc-box">'
        f'<img src="data:image/png;base64,{b64}" width="{ancho}"/>'
        f'<p style="font-family:monospace;font-size:.75rem;color:#555;margin-top:6px">'
        f'{texto} &nbsp;·&nbsp; Code 128 / ISO-15420</p></div>',
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────────────────
#  GRAFICAS
# ─────────────────────────────────────────────────────────
def grafica_estados(servicios):
    plt.rcParams.update({
        "figure.facecolor":"#161B22","axes.facecolor":"#0D1117",
        "axes.edgecolor":"#30363D","text.color":"#E6EDF3",
        "xtick.color":"#7D8590","ytick.color":"#7D8590",
    })
    conteo = {}
    for s in servicios:
        conteo[s["estado"]] = conteo.get(s["estado"], 0) + 1
    if not conteo:
        return None
    fig, ax = plt.subplots(figsize=(5, 3))
    colores = {"Pendiente":"#F78166","En Proceso":"#58A6FF","Completado":"#3FB950"}
    etiquetas = list(conteo.keys())
    valores   = list(conteo.values())
    clrs = [colores.get(e,"#7D8590") for e in etiquetas]
    bars = ax.bar(etiquetas, valores, color=clrs, width=0.5)
    ax.bar_label(bars, fmt="%d", color="#E6EDF3", padding=3)
    ax.set_title("Servicios por Estado", color="#58A6FF", fontsize=11)
    ax.set_ylabel("Cantidad", fontsize=9)
    ax.grid(True, alpha=0.15, axis="y")
    ax.spines[["top","right"]].set_visible(False)
    fig.tight_layout()
    return fig

def grafica_categorias(servicios):
    plt.rcParams.update({
        "figure.facecolor":"#161B22","axes.facecolor":"#0D1117",
        "axes.edgecolor":"#30363D","text.color":"#E6EDF3",
    })
    conteo = {}
    for s in servicios:
        conteo[s["categoria"]] = conteo.get(s["categoria"], 0) + 1
    if not conteo:
        return None
    fig, ax = plt.subplots(figsize=(4, 4))
    PAL = ["#58A6FF","#3FB950","#F78166","#E3B341","#BC8CFF"]
    ws, ts, ats = ax.pie(
        list(conteo.values()), labels=list(conteo.keys()),
        autopct="%1.0f%%", colors=PAL[:len(conteo)],
        wedgeprops={"linewidth":1,"edgecolor":"#0D1117"}
    )
    for t in ts+ats: t.set_color("#E6EDF3"); t.set_fontsize(9)
    ax.set_title("Por Categoría", color="#58A6FF", fontsize=11)
    fig.tight_layout()
    return fig

# ─────────────────────────────────────────────────────────
#  SIDEBAR  (menú de navegación)
# ─────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center;padding:10px 0 4px'>
          <div style='font-family:Syne,sans-serif;font-size:1.5rem;
                      font-weight:800;color:#3FB950'>📦 ServiScan</div>
          <div style='font-size:.72rem;color:#7D8590;margin-top:2px'>
            Gestión de Servicios con Código de Barra
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        pagina = st.radio("Ir a:", [
            "🏠  Inicio",
            "📝  Registrar Servicio",
            "📋  Inventario",
            "🔍  Buscar / Escanear",
            "📈  Estadísticas",
            "🔎  Trazabilidad",
            "📖  ¿Qué es un código de barra?",
        ], label_visibility="collapsed")
        st.divider()
        svcs = todos_los_servicios()
        total     = len(svcs)
        pendientes = sum(1 for s in svcs if s["estado"] == "Pendiente")
        st.markdown(
            f'<div style="font-size:.78rem;color:#7D8590;line-height:2">'
            f'Total: <b style="color:#E6EDF3">{total}</b><br/>'
            f'Pendientes: <b style="color:#F78166">{pendientes}</b>'
            f'</div>', unsafe_allow_html=True)
    return pagina

# ─────────────────────────────────────────────────────────
#  PAGINA: INICIO
# ─────────────────────────────────────────────────────────
def pg_inicio():
    st.markdown("# 📦 ServiScan")
    st.markdown("**Sistema de Gestión de Servicios con Código de Barra**")
    st.divider()
    svcs = todos_los_servicios()
    c1,c2,c3 = st.columns(3)
    c1.metric("Total de servicios",  len(svcs))
    c2.metric("Pendientes", sum(1 for s in svcs if s["estado"]=="Pendiente"))
    c3.metric("Completados",sum(1 for s in svcs if s["estado"]=="Completado"))
    st.divider()
    st.markdown("### ¿Qué puedes hacer aquí?")
    st.markdown("""
    - **📝 Registrar Servicio** — Crea un nuevo servicio. Se genera su código de barra automáticamente.
    - **📋 Inventario** — Ve la lista completa de todos los servicios.
    - **🔍 Buscar / Escanear** — Escribe el ID o usa la cámara para encontrar un servicio.
    - **📈 Estadísticas** — Gráficas con el resumen de los servicios.
    - **🔎 Trazabilidad** — Ve el historial completo de cualquier servicio (quién lo creó, cuándo cambió de estado).
    - **📖 ¿Qué es un código de barra?** — Explicación del tema para la clase.
    """)

# ─────────────────────────────────────────────────────────
#  PAGINA: REGISTRAR SERVICIO  (captura de datos)
# ─────────────────────────────────────────────────────────
def pg_registrar():
    st.markdown("# 📝 Registrar Nuevo Servicio")
    st.markdown("Llena el formulario y se generará el código de barra.")
    st.divider()
    with st.form("form_nuevo", clear_on_submit=True):
        a, b = st.columns(2)
        cliente     = a.text_input("Nombre del cliente *")
        categoria   = b.selectbox("Categoría",
                      ["General","Reparación","Mantenimiento","Instalación","Consulta"])
        descripcion = st.text_area("Descripción del servicio *",
                      placeholder="Ej: Reparación de laptop, pantalla no enciende")
        c, d = st.columns(2)
        estado  = c.selectbox("Estado inicial", ["Pendiente","En Proceso","Completado"])
        tecnico = d.text_input("Técnico asignado")
        enviado = st.form_submit_button("✅ Crear Servicio", use_container_width=True)

    if enviado:
        if not cliente.strip():
            st.error("El nombre del cliente es obligatorio.")
        elif not descripcion.strip():
            st.error("La descripción es obligatoria.")
        else:
            sid = crear_servicio(cliente, descripcion, categoria, estado, tecnico)
            st.success(f"✅ Servicio creado con ID: **{sid}**")
            st.markdown("### Código de Barra generado:")
            mostrar_barcode(sid)
            png = hacer_barcode(sid)
            st.download_button(
                "⬇ Descargar código como imagen",
                data=png,
                file_name=f"barcode_{sid}.png",
                mime="image/png"
            )
            st.info("💡 Descarga e imprime el código para poder escanearlo después.")

# ─────────────────────────────────────────────────────────
#  PAGINA: INVENTARIO
# ─────────────────────────────────────────────────────────
def pg_inventario():
    st.markdown("# 📋 Inventario de Servicios")
    st.divider()
    svcs = todos_los_servicios()
    if not svcs:
        st.info("Aún no hay servicios. Ve a **Registrar Servicio** para crear uno.")
        return

    # Filtros
    a, b = st.columns(2)
    filtro_estado = a.selectbox("Filtrar por estado",
                    ["Todos","Pendiente","En Proceso","Completado"])
    filtro_buscar = b.text_input("Buscar por nombre o ID")

    if filtro_estado != "Todos":
        svcs = [s for s in svcs if s["estado"] == filtro_estado]
    if filtro_buscar:
        q = filtro_buscar.lower()
        svcs = [s for s in svcs if q in s["cliente"].lower() or q in s["id"].lower()]

    st.caption(f"Mostrando {len(svcs)} servicios")

    filas = []
    for s in svcs:
        icono = "🔴" if s["estado"]=="Pendiente" else "🔵" if s["estado"]=="En Proceso" else "🟢"
        filas.append({
            "ID":          s["id"],
            "Cliente":     s["cliente"],
            "Descripción": s["descripcion"][:40] + "..." if len(s["descripcion"])>40 else s["descripcion"],
            "Categoría":   s["categoria"],
            "Estado":      f"{icono} {s['estado']}",
            "Técnico":     s["tecnico"] or "—",
            "Creado":      s["creado_en"],
        })
    st.dataframe(filas, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### ✏️ Actualizar estado de un servicio")
    svcs_todos = todos_los_servicios()
    opciones   = {s["id"] + " — " + s["cliente"]: s["id"] for s in svcs_todos}
    sel = st.selectbox("Seleccionar servicio", [""] + list(opciones.keys()))
    if sel:
        col1, col2, col3 = st.columns(3)
        nuevo_est = col1.selectbox("Nuevo estado",
                    ["Pendiente","En Proceso","Completado"])
        nuevo_tec = col2.text_input("Técnico")
        if col3.button("💾 Guardar cambio", use_container_width=True):
            actualizar_estado(opciones[sel], nuevo_est, nuevo_tec)
            st.success("✅ Estado actualizado")
            st.rerun()

# ─────────────────────────────────────────────────────────
#  PAGINA: BUSCAR / ESCANEAR
# ─────────────────────────────────────────────────────────
def _leer_barcode_de_imagen(img_pil):
    """Lee el codigo de barra de una imagen PIL usando pyzbar."""
    try:
        from pyzbar import pyzbar
        codigos = pyzbar.decode(img_pil.convert("RGB"))
        if codigos:
            return codigos[0].data.decode("utf-8")
    except Exception:
        pass
    return None

def _mostrar_servicio(svc):
    """Muestra la tarjeta de info de un servicio."""
    icono = "🔴" if svc["estado"]=="Pendiente" else "🔵" if svc["estado"]=="En Proceso" else "🟢"
    st.markdown(f"""
    <div class="card">
      <b style="color:#58A6FF;font-size:1rem">{svc['id']}</b><br/><br/>
      👤 Cliente: <b>{svc['cliente']}</b><br/>
      🔧 Servicio: <span style="color:#7D8590">{svc['descripcion']}</span><br/>
      📂 Categoría: <b>{svc['categoria']}</b><br/>
      {icono} Estado: <b>{svc['estado']}</b><br/>
      👷 Técnico: <b>{svc['tecnico'] or '—'}</b><br/>
      <span style="font-size:.78rem;color:#7D8590">
      Creado: {svc['creado_en']} · Actualizado: {svc['actualizado']}</span>
    </div>
    """, unsafe_allow_html=True)


def pg_buscar():
    st.markdown("# 🔍 Buscar Servicio")
    st.divider()

    # ── Opción 1: subir foto o usar cámara ────────────────────────
    st.markdown("### 📷 Opción 1 — Foto del código de barra")
    st.markdown(
        '<div class="card">'
        '<p style="font-size:.85rem;color:#7D8590">'
        'Sube una foto del código de barra impreso '
        '(desde tu teléfono, cámara o computadora). '
        'La app lo leerá automáticamente.</p>'
        '</div>', unsafe_allow_html=True)

    archivo = st.file_uploader(
        "📂 Seleccionar imagen del código de barra",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed"
    )

    if archivo is not None:
        img_pil = Image.open(archivo)
        col_img, col_res = st.columns([1, 1])
        with col_img:
            st.image(img_pil, caption="Imagen cargada", use_container_width=True)
        with col_res:
            with st.spinner("Leyendo código..."):
                codigo_leido = _leer_barcode_de_imagen(img_pil)
            if codigo_leido:
                st.success(f"✅ Código leído:\n**{codigo_leido}**")
                svc = buscar_por_id(codigo_leido.strip())
                if svc:
                    _mostrar_servicio(svc)
                else:
                    st.warning("Código leído, pero no existe ese servicio en la base de datos.")
            else:
                st.error(
                    "No se pudo leer el código.\n\n"
                    "**Consejos:** buena luz, código enfocado, "
                    "fondo blanco.\n\nO escribe el ID abajo."
                )

    st.divider()
    st.markdown("### ✍️ Opción 2 — Escribir el ID del servicio")
    col1, col2 = st.columns([3, 1])
    sid_manual = col1.text_input("ID del servicio", placeholder="Ej: SVC-20250321-0001")
    if col2.button("🔍 Buscar", use_container_width=True) and sid_manual:
        svc = buscar_por_id(sid_manual.strip())
        if not svc:
            st.error(f"No se encontró ningún servicio con ID: **{sid_manual}**")
        else:
            st.success("✅ Servicio encontrado")
            _mostrar_servicio(svc)
            mostrar_barcode(svc["id"], ancho=300)

    st.divider()
    st.markdown("### 📋 Opción 3 — Elegir de la lista")
    svcs = todos_los_servicios()
    if svcs:
        opciones = {f"{s['id']} — {s['cliente']}": s["id"] for s in svcs}
        sel = st.selectbox("Seleccionar servicio", [""] + list(opciones.keys()))
        if sel:
            svc = buscar_por_id(opciones[sel])
            if svc:
                _mostrar_servicio(svc)
                mostrar_barcode(svc["id"], ancho=300)
                st.download_button(
                    "⬇ Descargar código de barra",
                    hacer_barcode(svc["id"]),
                    f"barcode_{svc['id']}.png",
                    "image/png"
                )
    elif not svcs:
        st.info("Aún no hay servicios. Crea uno primero.")

# ─────────────────────────────────────────────────────────
#  PAGINA: ESTADISTICAS
# ─────────────────────────────────────────────────────────
def pg_estadisticas():
    st.markdown("# 📈 Estadísticas")
    st.divider()
    svcs = todos_los_servicios()
    if not svcs:
        st.info("Crea servicios para ver estadísticas.")
        return

    total      = len(svcs)
    pendientes = sum(1 for s in svcs if s["estado"] == "Pendiente")
    en_proceso = sum(1 for s in svcs if s["estado"] == "En Proceso")
    completados= sum(1 for s in svcs if s["estado"] == "Completado")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total",      total)
    c2.metric("Pendientes", pendientes)
    c3.metric("En Proceso", en_proceso)
    c4.metric("Completados",completados)

    st.divider()
    g1, g2 = st.columns(2)
    with g1:
        fig = grafica_estados(svcs)
        if fig:
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
    with g2:
        fig2 = grafica_categorias(svcs)
        if fig2:
            st.pyplot(fig2, use_container_width=True)
            plt.close(fig2)

    if total > 0:
        pct_completados = round(completados / total * 100)
        st.divider()
        st.markdown(f"**Tasa de completados:** {pct_completados}% de los servicios han sido completados.")
        if pendientes > 0:
            st.warning(f"⚠ Hay **{pendientes}** servicio(s) pendiente(s).")

# ─────────────────────────────────────────────────────────
#  PAGINA: TRAZABILIDAD
# ─────────────────────────────────────────────────────────
def pg_trazabilidad():
    st.markdown("# 🔎 Trazabilidad")
    st.markdown("La trazabilidad muestra **todo lo que le ha pasado a un servicio** desde que fue creado.")
    st.divider()
    svcs = todos_los_servicios()
    if not svcs:
        st.info("Crea servicios primero.")
        return
    opciones = {f"{s['id']} — {s['cliente']}": s["id"] for s in svcs}
    sel = st.selectbox("Seleccionar servicio", [""] + list(opciones.keys()))
    if not sel:
        return
    sid = opciones[sel]
    svc = buscar_por_id(sid)
    if not svc:
        return

    st.markdown(f"""
    <div class="card">
      <b style="color:#58A6FF">{svc['id']}</b><br/>
      Cliente: <b>{svc['cliente']}</b> &nbsp;·&nbsp; Estado actual: <b>{svc['estado']}</b>
    </div>
    """, unsafe_allow_html=True)

    eventos = historial_de(sid)
    if not eventos:
        st.info("Este servicio no tiene historial aún.")
        return

    st.markdown(f"**{len(eventos)} evento(s) registrados:**")
    for i, ev in enumerate(eventos):
        icono = "🟢" if ev["accion"] == "CREADO" else "🔵"
        st.markdown(
            f'<div style="border-left:3px solid #30363D;padding:8px 12px;'
            f'margin:4px 0;background:#161B22;border-radius:0 8px 8px 0">'
            f'{icono} <b>[{i+1}] {ev["accion"]}</b> &nbsp;'
            f'<span style="color:#7D8590;font-size:.8rem">{ev["fecha"]}</span><br/>'
            f'<span style="font-size:.85rem;color:#E6EDF3">{ev["detalle"]}</span>'
            f'</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
#  PAGINA: EXPLICACION DEL CODIGO DE BARRA
# ─────────────────────────────────────────────────────────
def pg_explicacion():
    st.markdown("# 📖 ¿Qué es un Código de Barra?")
    st.divider()

    st.markdown("""
    ### Definición simple
    Un **código de barra** es una forma de guardar información (como un número o un ID)
    usando rayas negras y blancas de diferentes grosores.
    Cuando una cámara o lector lo escanea, convierte esas rayas de vuelta al texto original.
    """)

    st.markdown("**Ejemplo — este es el código del servicio `SVC-20250321-0001`:**")
    mostrar_barcode("SVC-20250321-0001")

    st.divider()
    st.markdown("### ¿Cómo funciona?")
    st.markdown("""
    Cada letra o número se convierte en un patrón de barras.
    Por ejemplo, la letra **A** se convierte en el patrón `10100011000`.
    Un `1` significa barra negra, un `0` significa espacio blanco.

    Al final de todas las barras se incluye un número de verificación
    (llamado **checksum**) para detectar errores de lectura.
    """)

    st.divider()
    st.markdown("### Norma utilizada: **ISO/IEC 15420 — Code 128**")
    st.markdown("""
    Esta aplicación usa el estándar **Code 128**, definido en la norma **ISO/IEC 15420**.

    | Característica | Detalle |
    |---|---|
    | Nombre oficial | Code 128 / GS1-128 |
    | Norma | ISO/IEC 15420 |
    | Tipo | Código de barras lineal (1D) |
    | Caracteres soportados | Letras, números y símbolos (ASCII completo) |
    | Zona silenciosa | Mínimo 10 módulos en cada lado (requerido por la norma) |
    | Verificación | Checksum módulo 103 |
    | Usos comunes | Logística, almacenes, supermercados, hospitales |
    """)

    st.divider()
    st.markdown("### Principios del código de barra")
    st.markdown("""
    1. **Módulo** — La unidad mínima de ancho de una barra.
    2. **Zona silenciosa** — Espacio en blanco antes y después de las barras, para que el lector sepa dónde empieza y dónde termina.
    3. **Patrón de inicio** — Indica que el código comienza.
    4. **Datos** — El contenido codificado (el ID del servicio).
    5. **Checksum** — Número calculado para verificar que la lectura fue correcta.
    6. **Patrón de parada** — Indica que el código terminó.
    """)

    st.divider()
    st.markdown("### ¿Qué es la Trazabilidad?")
    st.markdown("""
    La **trazabilidad** es la capacidad de seguir el recorrido completo de algo.
    En esta aplicación, cada vez que un servicio se crea o cambia de estado,
    se guarda un registro con la fecha y el detalle del cambio.

    Esto permite saber:
    - **Cuándo** fue creado el servicio
    - **Quién** lo atendió
    - **Cómo** cambió su estado con el tiempo

    La norma que regula esto en logística es la **ISO/IEC 15459**.
    """)

# ─────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────
def main():
    init_db()
    pagina = sidebar()
    if   pagina.startswith("🏠"):  pg_inicio()
    elif pagina.startswith("📝"):  pg_registrar()
    elif pagina.startswith("📋"):  pg_inventario()
    elif pagina.startswith("🔍"):  pg_buscar()
    elif pagina.startswith("📈"):  pg_estadisticas()
    elif pagina.startswith("🔎"):  pg_trazabilidad()
    elif pagina.startswith("📖"):  pg_explicacion()

if __name__ == "__main__":
    main()
