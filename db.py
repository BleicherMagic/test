# db.py
import os
import streamlit as st
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


@st.cache_resource
def init_connection_pool() -> SimpleConnectionPool:
    db_url = st.secrets.get("database_url") or os.getenv("DATABASE_URL",
                                                         "postgresql://postgres:postgres@localhost:5432/postgres")
    return SimpleConnectionPool(
        minconn=1, maxconn=6, dsn=db_url, sslmode="require",
        cursor_factory=RealDictCursor,
        keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5,
    )


_pool = init_connection_pool()


@contextmanager
def pooled_cursor(commit: bool = True):
    conn = _pool.getconn()
    try:
        with conn.cursor() as cur:
            yield cur
            if commit:
                conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
