"""Smart migration runner that tracks and only runs new migrations.

This script:
1. Checks which migrations have already been applied
2. Runs only the new migrations
3. Records each migration in the tracking table
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import psycopg2
from dotenv import load_dotenv

# Fix Windows console encoding for Unicode support
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback: disable Unicode symbols (Python < 3.7)
        pass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()


def get_db_connection():
    """Get database connection directly using psycopg2 (no SQLAlchemy)."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://finagent:finagent_secret@localhost:5432/finagent"
    )
    # Convert SQLAlchemy URL format to psycopg2 format if needed
    if database_url.startswith("postgresql://"):
        return psycopg2.connect(database_url)
    else:
        # Parse components
        return psycopg2.connect(database_url)


def get_applied_migrations(conn, cursor):
    """Get list of migrations that have already been applied."""
    try:
        cursor.execute("""
            SELECT migration_name
            FROM schema_migrations
            WHERE success = TRUE
            ORDER BY applied_at
        """)
        return {row[0] for row in cursor.fetchall()}
    except Exception:
        # Table doesn't exist yet - rollback the failed transaction
        conn.rollback()
        return set()


def apply_migration(cursor, migration_file, migration_name):
    """Apply a single migration and record it."""
    print(f"\n{'='*70}")
    print(f"📄 Applying: {migration_name}")
    print(f"{'='*70}")

    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    try:
        # Execute migration
        cursor.execute(sql)

        # Record success (if migrations table exists)
        try:
            cursor.execute("""
                INSERT INTO schema_migrations (migration_name, notes)
                VALUES (%s, %s)
                ON CONFLICT (migration_name) DO UPDATE
                SET applied_at = CURRENT_TIMESTAMP,
                    success = TRUE
            """, (migration_name, f"Applied from {migration_file.name}"))
        except Exception:
            # Migrations table doesn't exist yet (will be created by 000_create_migrations_table.sql)
            pass

        print(f"✅ SUCCESS: {migration_name}")
        return True

    except Exception as e:
        print(f"❌ FAILED: {migration_name}")
        print(f"Error: {e}")

        # Record failure (if migrations table exists)
        try:
            cursor.execute("""
                INSERT INTO schema_migrations (migration_name, success, notes)
                VALUES (%s, FALSE, %s)
                ON CONFLICT (migration_name) DO UPDATE
                SET applied_at = CURRENT_TIMESTAMP,
                    success = FALSE,
                    notes = %s
            """, (migration_name, str(e), str(e)))
        except Exception:
            pass

        return False


def run_all_migrations(auto_confirm=False):
    """Run all pending migrations in order.

    Args:
        auto_confirm: If True, skip confirmation prompt and apply migrations automatically
    """
    migrations_dir = Path(__file__).parent.parent / "database" / "migrations"

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return False

    # Get all SQL files
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("📭 No migration files found")
        return True

    print(f"\n{'='*70}")
    print(f"***  FINAGENT DATABASE MIGRATION RUNNER")
    print(f"{'='*70}")
    print(f"Migrations directory: {migrations_dir}")
    print(f"Total migration files: {len(migration_files)}")
    print(f"{'='*70}\n")

    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get already applied migrations
        applied = get_applied_migrations(conn, cursor)
        print(f"✓ Already applied: {len(applied)} migrations")

        if applied:
            print("\nPreviously applied migrations:")
            for name in sorted(applied):
                print(f"  ✓ {name}")

        # Find pending migrations
        pending = []
        for file in migration_files:
            name = file.stem  # filename without extension
            if name not in applied:
                pending.append((name, file))

        if not pending:
            print(f"\n🎉 All migrations are up to date! Nothing to apply.")
            return True

        print(f"\n📋 Pending migrations: {len(pending)}")
        for name, _ in pending:
            print(f"  ⏳ {name}")

        # Ask for confirmation (unless auto_confirm is True)
        print(f"\n{'='*70}")
        if not auto_confirm:
            response = input(f"Apply {len(pending)} pending migration(s)? [y/N]: ").strip().lower()

            if response != 'y':
                print("❌ Migration cancelled by user")
                return False
        else:
            print(f"Auto-confirming: Applying {len(pending)} pending migration(s)...")

        # Apply each pending migration
        success_count = 0
        fail_count = 0

        for name, file in pending:
            if apply_migration(cursor, file, name):
                conn.commit()
                success_count += 1
            else:
                conn.rollback()
                fail_count += 1
                print(f"\n⚠️  Migration failed. Stopping here to avoid cascading issues.")
                break

        # Summary
        print(f"\n{'='*70}")
        print(f"📊 MIGRATION SUMMARY")
        print(f"{'='*70}")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {fail_count}")
        print(f"⏭️  Skipped: {len(applied)}")
        print(f"{'='*70}\n")

        if fail_count == 0:
            print("🎉 All migrations applied successfully!")
            return True
        else:
            print("⚠️  Some migrations failed. Please fix errors and re-run.")
            return False

    except Exception as e:
        print(f"\n❌ Migration runner error: {e}")
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Parse command line arguments
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    success = run_all_migrations(auto_confirm=auto_confirm)
    sys.exit(0 if success else 1)
