import sqlite3
import json
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


class Database:
    def __init__(self, db_path: str = "database.sqlite3"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Check if accounts table exists and has correct structure
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
            table_exists = cursor.fetchone()

            if table_exists:
                # Check columns
                cursor.execute("PRAGMA table_info(accounts)")
                columns = [row[1] for row in cursor.fetchall()]

                # If private_key column doesn't exist, recreate table
                if 'private_key' not in columns:
                    print("⚠️  Detected old database structure. Migrating...")
                    cursor.execute("DROP TABLE IF EXISTS accounts")
                    table_exists = None
                # Check if token columns exist
                elif 'access_token' not in columns:
                    print("⚠️  Adding token columns to database...")
                    cursor.execute("ALTER TABLE accounts ADD COLUMN access_token TEXT")
                    cursor.execute("ALTER TABLE accounts ADD COLUMN token_expires_at TIMESTAMP")

            # Create accounts table
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS accounts (
                                                                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                   private_key TEXT UNIQUE NOT NULL,
                                                                   address TEXT NOT NULL,
                                                                   smart_account TEXT,
                                                                   username TEXT,
                                                                   fingerprint TEXT NOT NULL,
                                                                   proxy TEXT,
                                                                   access_token TEXT,
                                                                   token_expires_at TIMESTAMP,
                                                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           )
                           ''')

            # Statistics table
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS statistics (
                                                                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                     account_id INTEGER,
                                                                     action_type TEXT NOT NULL,
                                                                     status TEXT NOT NULL,
                                                                     details TEXT,
                                                                     tx_hash TEXT,
                                                                     timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                     FOREIGN KEY (account_id) REFERENCES accounts (id)
                               )
                           ''')

            # Faucet claims table
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS faucet_claims (
                                                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                        account_id INTEGER,
                                                                        amount REAL,
                                                                        next_claim_time INTEGER,
                                                                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                        FOREIGN KEY (account_id) REFERENCES accounts (id)
                               )
                           ''')

            # Create indexes for better performance
            cursor.execute('''
                           CREATE INDEX IF NOT EXISTS idx_accounts_private_key
                               ON accounts(private_key)
                           ''')

            cursor.execute('''
                           CREATE INDEX IF NOT EXISTS idx_statistics_account_id
                               ON statistics(account_id)
                           ''')

            conn.commit()

        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def generate_fingerprint(self) -> str:
        return secrets.token_hex(32)

    def add_account(self, private_key: str, address: str, proxy: Optional[str] = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT id, fingerprint FROM accounts WHERE private_key = ?', (private_key,))
            existing = cursor.fetchone()

            if existing:
                return existing['id']

            fingerprint = self.generate_fingerprint()

            cursor.execute('''
                           INSERT INTO accounts (private_key, address, fingerprint, proxy)
                           VALUES (?, ?, ?, ?)
                           ''', (private_key, address, fingerprint, proxy))

            account_id = cursor.lastrowid
            conn.commit()
            return account_id

        except sqlite3.IntegrityError as e:
            cursor.execute('SELECT id FROM accounts WHERE private_key = ?', (private_key,))
            return cursor.fetchone()['id']
        except Exception as e:
            print(f"❌ Error adding account: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_account(self, private_key: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                           SELECT id, private_key, address, smart_account, username, fingerprint, proxy,
                                  access_token, token_expires_at
                           FROM accounts WHERE private_key = ?
                           ''', (private_key,))

            row = cursor.fetchone()

            if row:
                return {
                    'id': row['id'],
                    'private_key': row['private_key'],
                    'address': row['address'],
                    'smart_account': row['smart_account'],
                    'username': row['username'],
                    'fingerprint': row['fingerprint'],
                    'proxy': row['proxy'],
                    'access_token': row['access_token'],
                    'token_expires_at': row['token_expires_at']
                }
            return None

        finally:
            conn.close()

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                           SELECT id, private_key, address, smart_account, username, fingerprint, proxy,
                                  access_token, token_expires_at
                           FROM accounts
                           ORDER BY created_at DESC
                           ''')

            accounts = []
            for row in cursor.fetchall():
                accounts.append({
                    'id': row['id'],
                    'private_key': row['private_key'],
                    'address': row['address'],
                    'smart_account': row['smart_account'],
                    'username': row['username'],
                    'fingerprint': row['fingerprint'],
                    'proxy': row['proxy'],
                    'access_token': row['access_token'],
                    'token_expires_at': row['token_expires_at']
                })

            return accounts

        finally:
            conn.close()

    def update_account(self, private_key: str, **kwargs):
        """Update account data"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Build update query
            fields = []
            values = []
            for key, value in kwargs.items():
                fields.append(f"{key} = ?")
                values.append(value)

            if not fields:
                return

            fields.append("updated_at = ?")
            values.append(datetime.now())
            values.append(private_key)

            query = f"UPDATE accounts SET {', '.join(fields)} WHERE private_key = ?"
            cursor.execute(query, values)

            conn.commit()

        except Exception as e:
            print(f"❌ Error updating account: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_token(self, private_key: str, access_token: str, expires_in_hours: int = 24):
        """Save access token with expiration time"""
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        self.update_account(
            private_key,
            access_token=access_token,
            token_expires_at=expires_at
        )

    def get_token(self, private_key: str) -> Optional[str]:
        """Get valid access token"""
        account = self.get_account(private_key)
        if not account or not account['access_token']:
            return None

        # Check if token is still valid
        if account['token_expires_at']:
            expires_at = datetime.fromisoformat(account['token_expires_at'])
            if datetime.now() >= expires_at:
                # Token expired
                return None

        return account['access_token']

    def is_token_valid(self, private_key: str) -> bool:
        """Check if token is still valid"""
        account = self.get_account(private_key)
        if not account or not account['access_token'] or not account['token_expires_at']:
            return False

        expires_at = datetime.fromisoformat(account['token_expires_at'])
        return datetime.now() < expires_at

    def clear_token(self, private_key: str):
        """Clear expired token"""
        self.update_account(
            private_key,
            access_token=None,
            token_expires_at=None
        )

    def set_proxy(self, private_key: str, proxy: str):
        """Set proxy for account"""
        self.update_account(private_key, proxy=proxy)

    def remove_all_proxies(self):
        """Remove all proxies from all accounts"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('UPDATE accounts SET proxy = NULL')
            affected = cursor.rowcount
            conn.commit()
            return affected

        finally:
            conn.close()

    def add_statistic(self, account_id: int, action_type: str, status: str,
                      details: Optional[str] = None, tx_hash: Optional[str] = None):
        """Add action statistic"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                           INSERT INTO statistics (account_id, action_type, status, details, tx_hash)
                           VALUES (?, ?, ?, ?, ?)
                           ''', (account_id, action_type, status, details, tx_hash))

            conn.commit()

        except Exception as e:
            print(f"❌ Error adding statistic: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_statistics(self, account_id: Optional[int] = None, limit: int = 100) -> List[tuple]:
        """Get statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if account_id:
                cursor.execute('''
                               SELECT action_type, status, details, tx_hash, timestamp
                               FROM statistics WHERE account_id = ?
                               ORDER BY timestamp DESC
                                   LIMIT ?
                               ''', (account_id, limit))
            else:
                cursor.execute('''
                               SELECT a.address, s.action_type, s.status, s.details, s.tx_hash, s.timestamp
                               FROM statistics s
                                        JOIN accounts a ON s.account_id = a.id
                               ORDER BY s.timestamp DESC
                                   LIMIT ?
                               ''', (limit,))

            return cursor.fetchall()

        finally:
            conn.close()

    def export_statistics(self, filename: str = "statistics_export.json") -> int:
        """Export statistics to JSON file"""
        stats = self.get_statistics(limit=10000)

        export_data = []
        for row in stats:
            export_data.append({
                'address': row[0],
                'action_type': row[1],
                'status': row[2],
                'details': row[3],
                'tx_hash': row[4],
                'timestamp': row[5]
            })

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=4)

        return len(export_data)

    def get_account_count(self) -> int:
        """Get total account count"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT COUNT(*) FROM accounts')
            count = cursor.fetchone()[0]
            return count

        finally:
            conn.close()

    def get_success_rate(self) -> Dict[str, Any]:
        """Get success rate statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                           SELECT
                               COUNT(*) as total,
                               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                               SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                           FROM statistics
                           ''')

            row = cursor.fetchone()

            total = row[0]
            success = row[1] or 0
            failed = row[2] or 0

            return {
                'total': total,
                'success': success,
                'failed': failed,
                'success_rate': (success / total * 100) if total > 0 else 0
            }

        finally:
            conn.close()

    def cleanup_old_stats(self, days: int = 30):
        """Remove statistics older than specified days"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                           DELETE FROM statistics
                           WHERE timestamp < datetime('now', '-' || ? || ' days')
                           ''', (days,))

            deleted = cursor.rowcount
            conn.commit()
            return deleted

        finally:
            conn.close()

    def vacuum_database(self):
        """Optimize database (vacuum)"""
        conn = self.get_connection()
        try:
            conn.execute('VACUUM')
            print("✓ Database optimized successfully")
        finally:
            conn.close()