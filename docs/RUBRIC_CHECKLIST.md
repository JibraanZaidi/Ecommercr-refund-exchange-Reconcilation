# Rubric compliance checklist

Mapped to the eight categories supplied in the project brief. This is evidence mapping, not a guarantee of an instructor's score.

| Category | Marks | Concrete evidence |
|---|---:|---|
| Setup & structure | 10 | `wsgi.py`, `requirements.txt`, `app/__init__.py` factory, templates/static/services/tests/docs separation |
| Routing & views | 15 | `app/views.py` Blueprint; dynamic integer detail routes; GET reads and POST changes; custom 400/403/404/413/500 pages |
| Jinja2 | 15 | All pages extend `base.html`; `macros.html` reusable form/filter/pagination macros; conditions, loops, filters |
| Database & CRUD | 20 | `models.py` 48 real models/tables, foreign keys/indexes/uniqueness/check constraints; master CRUD; draft return CRUD; non-destructive posted transitions |
| Forms, validation, cookies & sessions | 15 | CSRFProtect, server parsing/domain validation, flash messages, session auth, password hashes, page-size cookie, PRG |
| Code quality | 10 | Separated services/imports/views; documented domain methods, explicit model names and operational boundaries |
| Functionality & testing | 10 | `tests/test_acceptance.py`, `tests/test_workflows.py`; refund/installment/duplicate/import/reversal/permissions/CRUD/filter/route/state tests |
| Documentation | 5 | README, architecture/viva, data dictionary, ERD, mapping guide, demo walkthrough, actual verification report |

The authoritative table count is printed by `flask --app wsgi verify-schema`, not inferred from model names. See `VERIFICATION.md` for actual results.
