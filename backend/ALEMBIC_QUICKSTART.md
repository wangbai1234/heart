# Alembic Quick Start - Heart AI Companion

## ✅ Current Status

Alembic is **fully configured and tested** for the Heart project.

```
✓ Async SQLAlchemy 2.0 configured
✓ PostgreSQL 15 + pgvector ready
✓ Environment variables from .env
✓ Initial migration applied
✓ All tests passing (7/7)
✓ Ready for development
```

## 🚀 Quick Commands

### Check Migration Status

```bash
# See current migration
alembic current
# Output: e814230ade46 (head)

# See migration history
alembic history
# Output: <base> -> e814230ade46, Initial empty schema revision

# See pending migrations
alembic heads
```

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply next 2 migrations
alembic upgrade +2

# Downgrade one migration
alembic downgrade -1

# Downgrade all migrations
alembic downgrade base
```

### Create Migrations

**When you add SQLAlchemy models:**

```bash
# Enable autogenerate in migrations/env.py:
# from heart.infra.db import Base
# target_metadata = Base.metadata

# Then generate migration:
alembic revision --autogenerate -m "Add users table"

# Or manually (if autogenerate can't detect):
alembic revision -m "Add custom index"
```

### Test Migrations

```bash
# Run all migration tests
pytest tests/integration/test_migrations.py -v

# Quick status check
alembic current && echo "OK"
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `alembic.ini` | Main configuration |
| `migrations/env.py` | Async SQLAlchemy setup |
| `migrations/versions/` | Migration scripts |
| `migrations/README.md` | Full documentation |
| `migrations/SETUP_GUIDE.md` | Setup workflow |
| `migrations/MIGRATION_EXAMPLES.md` | Real-world examples |
| `.env` | Environment variables (root) |

## 🔑 Environment Variable

Set in root `.env` file:

```bash
DATABASE_URL=postgresql+asyncpg://heart:heartdev@localhost:5432/heart
```

## 📚 When You Need More Info

1. **How to add first table?**
   → Read `migrations/SETUP_GUIDE.md` § "When Adding Database Models"

2. **Want to see examples?**
   → Check `migrations/MIGRATION_EXAMPLES.md`

3. **Full documentation?**
   → See `migrations/README.md`

4. **Configuration details?**
   → Review `docs/archive/2026-05-16_alembic_config.md` (历史快照)

## ⚠️ Important Notes

### Autogenerate Requires Models

```python
# Only works after you add this to env.py:
from heart.infra.db import Base
target_metadata = Base.metadata
```

### Always Test Rollback

```bash
# After creating migration:
alembic upgrade head      # Apply
alembic downgrade -1      # Rollback
alembic upgrade head      # Re-apply
```

### Large Table Changes

Use `postgresql_concurrently=True` for indexes:

```python
op.create_index('idx_name', 'large_table', ['col'],
                postgresql_concurrently=True)
```

## 🆘 Troubleshooting

### CONNECTION REFUSED

```bash
# Check PostgreSQL is running
docker-compose ps

# Restart if needed
docker-compose restart postgres
```

### DATABASE_URL NOT SET

```bash
# Check .env exists in root
cat .env | grep DATABASE_URL

# Or set environment variable
export DATABASE_URL=postgresql+asyncpg://...
```

### MIGRATION WON'T GENERATE

```bash
# Make sure target_metadata is set in env.py
grep "target_metadata" migrations/env.py

# Check models are importable
python3 -c "from heart.infra.db import Base; print(Base.metadata.tables)"
```

## ✨ Next Steps

1. **Create database models** in `heart/infra/db.py`
2. **Enable autogenerate** in `migrations/env.py`
3. **Generate migrations** with `alembic revision --autogenerate`
4. **Apply migrations** with `alembic upgrade head`
5. **Write tests** for your models

## 📞 Full Documentation

- **Alembic Site**: https://alembic.sqlalchemy.org/
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **PostgreSQL Docs**: https://www.postgresql.org/docs/current/
- **Engineering Spec**: `/runtime_specs/08_engineering_architecture.md` §4-5

---

**Status**: ✅ Ready for development  
**Configuration**: Complete  
**Tests**: All passing (7/7)  
**Last Updated**: May 16, 2026
