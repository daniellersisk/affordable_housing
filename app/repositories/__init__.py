# Package marker for repository modules.
# Repositories own all SQLAlchemy queries and direct database access.
# Service layers call repositories; route handlers never query the DB directly.
