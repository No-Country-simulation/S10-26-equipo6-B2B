"""Paridad entre la migracion SQL inicial y el modelo ORM (issue #38).

La migracion ``backend/migrations/0001_init.sql`` es la fuente del esquema en
PostgreSQL (Docker local y nube). Estas pruebas garantizan que cubra todas las
tablas, columnas, claves primarias, foraneas y de unicidad declaradas en
``app.models.entities``, la misma especificacion de ``docs/systemDesign.md``
(seccion 3.3).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from sqlalchemy import UniqueConstraint

from app.models import Base

RUTA_MIGRACION = Path(__file__).resolve().parents[2] / "migrations" / "0001_init.sql"


def _sql() -> str:
    return RUTA_MIGRACION.read_text(encoding="utf-8")


def _bloque(sql: str, tabla: str) -> str:
    """Devuelve el cuerpo entre ``CREATE TABLE <tabla>`` y su cierre."""
    inicio = re.search(
        rf"CREATE TABLE\s+{re.escape(tabla)}\s*\(", sql, re.IGNORECASE
    )
    assert inicio is not None, f"no se encontro CREATE TABLE para '{tabla}'"
    cierre = sql.find(");", inicio.end())
    assert cierre != -1, f"CREATE TABLE de '{tabla}' sin cierre"
    return sql[inicio.start() : cierre + 2]


def test_la_migracion_existe() -> None:
    assert RUTA_MIGRACION.is_file(), (
        f"falta la migracion en {RUTA_MIGRACION} (issue #38)"
    )
    assert _sql().strip(), "la migracion esta vacia"


def test_cubre_las_nueve_tablas() -> None:
    sql = _sql()
    assert len(Base.metadata.tables) == 9, "el modelo debe tener 9 tablas"
    for tabla in Base.metadata.tables:
        assert re.search(
            rf"CREATE TABLE\s+{re.escape(tabla)}\b", sql, re.IGNORECASE
        ), f"falta CREATE TABLE {tabla}"


def test_cubre_las_columnas() -> None:
    sql = _sql()
    for nombre_tabla, tabla in Base.metadata.tables.items():
        bloque = _bloque(sql, nombre_tabla)
        for columna in tabla.columns:
            assert re.search(
                rf"\b{re.escape(columna.name)}\b", bloque, re.IGNORECASE
            ), f"falta la columna {columna.name} en {nombre_tabla}"


def test_claves_primarias() -> None:
    sql = _sql()
    for nombre_tabla, tabla in Base.metadata.tables.items():
        bloque = _bloque(sql, nombre_tabla)
        columnas_pk = [columna.name for columna in tabla.primary_key.columns]
        if len(columnas_pk) > 1:
            patron = (
                r"PRIMARY KEY\s*\(\s*"
                + r"\s*,\s*".join(re.escape(c) for c in columnas_pk)
                + r"\s*\)"
            )
            assert re.search(patron, bloque, re.IGNORECASE), (
                f"PK compuesta {columnas_pk} ausente en {nombre_tabla}"
            )
        else:
            assert re.search(r"\bPRIMARY KEY\b", bloque, re.IGNORECASE), (
                f"PK de {nombre_tabla} ausente"
            )


def test_unicidad_declarada() -> None:
    sql = _sql()
    for nombre_tabla, tabla in Base.metadata.tables.items():
        bloque = _bloque(sql, nombre_tabla)
        for columna in tabla.columns:
            if columna.unique:
                assert re.search(
                    rf"\b{re.escape(columna.name)}\b[^,\n]*\bUNIQUE\b",
                    bloque,
                    re.IGNORECASE,
                ), (
                    f"unicidad de {nombre_tabla}.{columna.name} ausente"
                )
        for restriccion in tabla.constraints:
            if isinstance(restriccion, UniqueConstraint) and restriccion.name:
                assert restriccion.name in bloque, (
                    f"constraint {restriccion.name} ausente en {nombre_tabla}"
                )


def test_llaves_foraneas_y_on_delete() -> None:
    sql = _sql()
    for nombre_tabla, tabla in Base.metadata.tables.items():
        bloque = _bloque(sql, nombre_tabla)
        for fk in tabla.foreign_keys:
            tabla_padre = fk.target_fullname.split(".")[0]
            referencia = re.search(
                rf"REFERENCES\s+{re.escape(tabla_padre)}\s*\(", bloque, re.IGNORECASE
            )
            assert referencia is not None, (
                f"{nombre_tabla} no declara REFERENCES {tabla_padre}"
            )
            resto = bloque[referencia.end() :]
            if fk.ondelete:
                esperado = rf"\s*\w+\s*\)\s*ON DELETE\s+{fk.ondelete}\b"
                assert re.match(esperado, resto, re.IGNORECASE), (
                    f"{nombre_tabla}.{fk.column_name} debe tener "
                    f"ON DELETE {fk.ondelete}"
                )
            else:
                assert not re.match(
                    r"\s*\w+\s*\)\s*ON DELETE\b", resto, re.IGNORECASE
                ), (
                    f"{nombre_tabla}.{fk.column_name} no deberia declarar "
                    "ON DELETE (entities.py no lo hace)"
                )


def test_el_ddl_se_ejecuta_de_punta_a_punta() -> None:
    """El SQL plano corre completo en un motor relacional limpio."""
    conexion = sqlite3.connect(":memory:")
    try:
        conexion.executescript(_sql())
        filas = conexion.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    finally:
        conexion.close()
    obtenidas = {fila[0] for fila in filas}
    esperadas = set(Base.metadata.tables)
    assert obtenidas == esperadas, (
        f"solo {sorted(obtenidas)}; se esperaba {sorted(esperadas)}"
    )
