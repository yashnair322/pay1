import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv

load_dotenv()

class DatabasePool:
    _pool = None

    @classmethod
    def initialize(cls):
        if not cls._pool:
            cls._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=os.getenv("DATABASE_URL")
            )
        return cls._pool

    @classmethod
    def get_connection(cls):
        if not cls._pool:
            cls.initialize()
        return cls._pool.getconn()

    @classmethod
    def return_connection(cls, conn):
        if cls._pool:
            cls._pool.putconn(conn)

    @classmethod
    def close_all(cls):
        if cls._pool:
            cls._pool.closeall()

# Initialize the connection pool
DatabasePool.initialize()


# Function to create users table if it doesn't exist
def create_users_table():
    try:
        conn = DatabasePool.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(200) NOT NULL,
            is_verified BOOLEAN DEFAULT FALSE,
            subscription_status BOOLEAN DEFAULT FALSE,
            subscription_plan VARCHAR(20) DEFAULT 'free'
        );
        """)
        conn.commit()
        print("✅ Users table is ready!")
        DatabasePool.return_connection(conn)
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        if conn:
            conn.rollback()
            DatabasePool.return_connection(conn)


# Function to create subscriptions table if it doesn't exist
def create_subscriptions_table():
    try:
        conn = DatabasePool.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(100) NOT NULL,
            plan_id VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP,
            payment_id VARCHAR(100),
            amount DECIMAL(10,2),
            FOREIGN KEY (user_email) REFERENCES users(email)
        );
        """)
        conn.commit()
        print("✅ Subscriptions table is ready!")
        DatabasePool.return_connection(conn)
    except Exception as e:
        print(f"❌ Error creating subscriptions table: {e}")
        if conn:
            conn.rollback()
            DatabasePool.return_connection(conn)

# Call the functions to ensure tables exist
create_users_table()
create_subscriptions_table()

# Close all connections
DatabasePool.close_all()