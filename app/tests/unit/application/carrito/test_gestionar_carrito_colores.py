from app.application.carrito.gestionar_carrito import GestionarCarrito
from app.domain.entities.carrito import Carrito


class _RepoFake:
    """Carrito en memoria con la misma semantica que el repo de BD.

    `obtener` devuelve lo guardado (o None si el usuario aun no tiene carrito),
    asi que las operaciones sucesivas ven el mismo carrito y no uno nuevo.
    """

    def __init__(self) -> None:
        self.por_usuario: dict[str, Carrito] = {}
        self.veces_guardado = 0

    def obtener(self, usuario_id: str) -> Carrito | None:
        return self.por_usuario.get(usuario_id)

    def guardar(self, carrito: Carrito) -> Carrito:
        self.veces_guardado += 1
        self.por_usuario[carrito.usuario_id] = carrito
        return carrito

    def eliminar(self, usuario_id: str) -> None:
        self.por_usuario.pop(usuario_id, None)


def _servicio() -> tuple[GestionarCarrito, _RepoFake]:
    repositorio = _RepoFake()
    return GestionarCarrito(repositorio), repositorio


def _agregar(servicio: GestionarCarrito, usuario, producto_id, cantidad=1, color=None):
    return servicio.agregar_item(usuario, producto_id, cantidad, color)


def test_agregar_sin_color_deja_el_color_en_none():
    servicio, _ = _servicio()
    usuario = "usuario-1"

    carrito = _agregar(servicio, usuario, "prod-1", 2)

    assert len(carrito.items) == 1
    assert carrito.items[0].color is None
    assert carrito.items[0].cantidad == 2


def test_mismo_producto_y_mismo_color_suma_cantidad_en_una_linea():
    servicio, _ = _servicio()
    usuario = "usuario-1"

    _agregar(servicio, usuario, "prod-1", 1, "Blanco")
    carrito = _agregar(servicio, usuario, "prod-1", 2, "Blanco")

    assert len(carrito.items) == 1
    assert carrito.items[0].cantidad == 3
    assert carrito.items[0].color == "Blanco"


def test_mismo_producto_en_distinto_color_genera_lineas_separadas():
    servicio, _ = _servicio()
    usuario = "usuario-1"

    _agregar(servicio, usuario, "prod-1", 1, "Blanco")
    carrito = _agregar(servicio, usuario, "prod-1", 1, "Negro")

    # Se imprime distinto, asi que no puede fusionarse en una sola linea.
    assert len(carrito.items) == 2
    assert sorted(i.color for i in carrito.items) == ["Blanco", "Negro"]
    assert all(i.cantidad == 1 for i in carrito.items)
    assert len({i.id for i in carrito.items}) == 2


def test_color_se_normaliza_a_none_cuando_viene_vacio():
    servicio, _ = _servicio()
    usuario = "usuario-1"

    _agregar(servicio, usuario, "prod-1", 1, "Blanco")
    carrito = _agregar(servicio, usuario, "prod-1", 1, "   ")

    # Sin color es la misma linea que la que no tiene color, no una nueva.
    assert len(carrito.items) == 2
    assert carrito.items[1].color is None


def test_color_se_normaliza_con_strip_antes_de_agrupar():
    servicio, _ = _servicio()
    usuario = "usuario-1"

    _agregar(servicio, usuario, "prod-1", 1, "Blanco")
    carrito = _agregar(servicio, usuario, "prod-1", 1, "  Blanco  ")

    assert len(carrito.items) == 1
    assert carrito.items[0].cantidad == 2
    assert carrito.items[0].color == "Blanco"


def test_actualizar_cantidad_solo_toca_la_linea_del_item():
    servicio, _ = _servicio()
    usuario = "usuario-1"

    _agregar(servicio, usuario, "prod-1", 1, "Blanco")
    carrito = _agregar(servicio, usuario, "prod-1", 1, "Negro")
    blanco = next(i for i in carrito.items if i.color == "Blanco")

    carrito = servicio.actualizar_cantidad(usuario, blanco.id, 5)

    por_color = {i.color: i.cantidad for i in carrito.items}
    assert por_color == {"Blanco": 5, "Negro": 1}


def test_eliminar_una_linea_no_arrastra_la_del_otro_color():
    servicio, _ = _servicio()
    usuario = "usuario-1"

    _agregar(servicio, usuario, "prod-1", 1, "Blanco")
    carrito = _agregar(servicio, usuario, "prod-1", 1, "Negro")
    blanco = next(i for i in carrito.items if i.color == "Blanco")

    carrito = servicio.eliminar_item(usuario, blanco.id)

    assert len(carrito.items) == 1
    assert carrito.items[0].color == "Negro"


def test_carrito_se_persiste_tras_agregar():
    servicio, repositorio = _servicio()

    _agregar(servicio, "usuario-1", "prod-1", 1, "Blanco")

    # Alta del carrito vacio + el guardado del item con color.
    assert repositorio.veces_guardado == 2
    guardado = repositorio.por_usuario["usuario-1"]
    assert isinstance(guardado, Carrito)
    assert guardado.items[0].color == "Blanco"


def test_cantidad_invalida_se_rechaza_tambien_con_color():
    servicio, _ = _servicio()

    try:
        _agregar(servicio, "usuario-1", "prod-1", 0, "Blanco")
    except ValueError as exc:
        assert "cantidad" in str(exc).lower()
    else:
        raise AssertionError("debio rechazar cantidad 0")
