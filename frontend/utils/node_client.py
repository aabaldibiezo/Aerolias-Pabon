# =============================================
# AEROLÍNEAS RAFAEL PABON
# utils/node_client.py — Cliente HTTP hacia el nodo FastAPI
# =============================================

import httpx


class NodeClient:
    """Cliente síncrono para la API REST de un nodo."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout  = timeout

    def _get(self, path: str, params: dict = None) -> dict:
        resp = httpx.get(f"{self.base_url}{path}", params=params or {}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict = None) -> dict:
        resp = httpx.post(f"{self.base_url}{path}", json=body or {}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ── Health ──────────────────────────────────────────────────────────
    def health(self) -> dict:
        return self._get("/")

    def sync_status(self) -> dict:
        return self._get("/sync/status")

    # ── Aeropuertos / Rutas ─────────────────────────────────────────────
    def get_airports(self) -> list[dict]:
        return self._get("/routes/airports")["aeropuertos"]

    def get_reachable(self, origen: str) -> list[dict]:
        return self._get("/routes/reachable", {"origen": origen})["destinos"]

    def get_shortest_route(self, origen: str, destino: str) -> dict | None:
        try:
            return self._get("/routes/shortest", {"origen": origen, "destino": destino})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    # ── Vuelos ──────────────────────────────────────────────────────────
    def search_flights(
        self,
        origen:  str | None = None,
        destino: str | None = None,
        fecha:   str | None = None,
    ) -> list[dict]:
        params = {}
        if origen:  params["origen"]  = origen
        if destino: params["destino"] = destino
        if fecha:   params["fecha"]   = fecha
        return self._get("/flights", params)["vuelos"]

    def get_flight(self, vuelo_id: str) -> dict | None:
        try:
            return self._get(f"/flights/{vuelo_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    # ── Asientos ────────────────────────────────────────────────────────
    def get_seats(self, vuelo_id: str) -> list[dict]:
        return self._get(f"/flights/{vuelo_id}/seats")["asientos"]

    def get_seat(self, vuelo_id: str, numero: str) -> dict | None:
        try:
            return self._get(f"/flights/{vuelo_id}/seats/{numero}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def reservar(self, vuelo_id: str, numero: str, pasaporte: str, nombre: str, email: str = None) -> dict:
        return self._post(f"/flights/{vuelo_id}/seats/{numero}/reservar",
                          {"pasaporte": pasaporte, "nombre": nombre, "email": email})

    def vender(self, vuelo_id: str, numero: str, pasaporte: str, nombre: str, email: str = None) -> dict:
        return self._post(f"/flights/{vuelo_id}/seats/{numero}/vender",
                          {"pasaporte": pasaporte, "nombre": nombre, "email": email})

    def devolver(self, vuelo_id: str, numero: str, motivo: str = None) -> dict:
        body = {}
        if motivo:
            body["motivo"] = motivo
        return self._post(f"/flights/{vuelo_id}/seats/{numero}/devolver", body)

    # ── Pasajeros ────────────────────────────────────────────────────────
    def get_passenger(self, pasaporte: str) -> dict | None:
        try:
            return self._get(f"/passengers/{pasaporte}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
