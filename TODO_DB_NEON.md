# TODO: Switch project DB from MySQL (local) to Neon Postgres

- [x] Update `app/database.py` to remove MySQL-only driver assumptions (use generic SQLAlchemy engine).
- [x] Update `alembic/env.py` to set Alembic `sqlalchemy.url` from `settings.DATABASE_URL` (Neon Postgres).
- [x] Remove `pymysql` from `requirements.txt`.
- [ ] Add a Postgres driver dependency (`psycopg[binary]` or `psycopg2-binary`) to `requirements.txt`.
- [ ] Install Python dependencies (`pip install -r requirements.txt`).
- [ ] Run Alembic migrations against Neon Postgres (e.g. `alembic upgrade head`).
- [ ] Ensure `.env` contains `DATABASE_URL` set to the Neon URL.
- [ ] Start the server and verify `/health` and a DB-backed endpoint.

