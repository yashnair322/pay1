
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

# Establish database connection
try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("✅ Database connected successfully!")
except Exception as e:
    print(f"❌ Error connecting to the database: {e}")

# Create subscriptions table if it doesn't exist
def create_subscriptions_table():
    try:
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
    except Exception as e:
        print(f"❌ Error creating subscriptions table: {e}")
        conn.rollback()

# Function to create users table if it doesn't exist
def create_users_table():
    try:
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
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        conn.rollback()

def create_subscriptions_table():
    try:
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
    except Exception as e:
        print(f"❌ Error creating subscriptions table: {e}")
        conn.rollback()

# Call the functions to ensure tables exist
create_users_table()
create_subscriptions_table()
