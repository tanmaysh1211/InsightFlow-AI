import re
from typing import Dict, List, Any, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from app.db.models import DatabaseConnection

class DatabaseExecutor:
    @staticmethod
    def get_connection_url(conn: DatabaseConnection) -> str:
        """Constructs the SQLAlchemy connection URL based on db_type."""
        db_type = conn.db_type.lower()
        if db_type == "sqlite":
            path = conn.file_path or "enterprise_demo.db"
            return f"sqlite:///{path}"
        elif db_type == "postgresql":
            pw = conn.get_password()
            return f"postgresql://{conn.username}:{pw}@{conn.host}:{conn.port}/{conn.database_name}"
        elif db_type == "mysql":
            pw = conn.get_password()
            # use pymysql driver
            return f"mysql+pymysql://{conn.username}:{pw}@{conn.host}:{conn.port}/{conn.database_name}"
        elif db_type == "sqlserver":
            pw = conn.get_password()
            # use pyodbc / pymssql (we can use pymssql for simpler installation)
            return f"mssql+pymssql://{conn.username}:{pw}@{conn.host}:{conn.port}/{conn.database_name}"
        else:
            raise ValueError(f"Unsupported database type: {conn.db_type}")

    @classmethod
    def get_engine(cls, conn: DatabaseConnection) -> Engine:
        """Creates and returns a SQLAlchemy Engine."""
        url = cls.get_connection_url(conn)
        # 10 second timeout for queries, prevent hanging connections
        if conn.db_type.lower() == "sqlite":
            return create_engine(url)
        else:
            return create_engine(url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)

    @classmethod
    def test_connection(cls, conn: DatabaseConnection) -> Tuple[bool, str]:
        """Tests whether a connection can be established."""
        try:
            engine = cls.get_engine(conn)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True, "Connection successful."
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    @classmethod
    def get_schema_info(cls, conn: DatabaseConnection) -> List[Dict[str, Any]]:
        """
        Inspects the database schema using SQLAlchemy inspector.
        Returns a list of tables with columns, types, primary keys, and foreign keys.
        """
        engine = cls.get_engine(conn)
        inspector = inspect(engine)
        
        schema_data = []
        try:
            table_names = inspector.get_table_names()
            for table_name in table_names:
                columns = []
                # Fetch columns
                for col in inspector.get_columns(table_name):
                    columns.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "default": str(col.get("default")) if col.get("default") is not None else None
                    })
                
                # Fetch primary keys
                pk_constraint = inspector.get_pk_constraint(table_name)
                pks = pk_constraint.get("constrained_columns", [])
                
                # Fetch foreign keys
                fks = []
                for fk in inspector.get_foreign_keys(table_name):
                    fks.append({
                        "constrained_columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"]
                    })
                
                schema_data.append({
                    "table_name": table_name,
                    "columns": columns,
                    "primary_keys": pks,
                    "foreign_keys": fks
                })
        except Exception as e:
            # Fallback for dynamic sqlite or single table systems
            print(f"Error inspecting schema: {e}")
        return schema_data

    @classmethod
    def execute_query(cls, conn: DatabaseConnection, sql_query: str, limit: int = 500) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], str]:
        """
        Safely executes a SQL query on the target connection.
        Enforces read-only verification, row limits, and returns:
          - rows: List of dictionaries (column -> value)
          - columns: List of dictionaries with column name and type info
          - error_message: Empty string if successful, else error details.
        """
        # Defensive check against destructive operations (in case Validator agent fails)
        sanitized = re.sub(r'\s+', ' ', sql_query).strip().upper()
        blocked_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "RENAME", "REPLACE", "CREATE", "GRANT", "REVOKE"]
        for keyword in blocked_keywords:
            # Use word boundaries to check if query contains any destructive operations
            if re.search(r'\b' + keyword + r'\b', sanitized):
                return [], [], f"Security Block: Direct SQL execution of '{keyword}' commands is not permitted."

        engine = cls.get_engine(conn)
        rows = []
        columns = []
        error_msg = ""
        
        try:
            with engine.connect() as connection:
                # Limit query if it's select to avoid memory issues (add limit if not present, or wrap it)
                # For sqlite/postgresql/mysql we can add a LIMIT clause or fetch only up to 'limit' rows
                result = connection.execute(text(sql_query))
                
                # Retrieve columns schema info
                if result.returns_rows:
                    col_names = list(result.keys())
                    for col_name in col_names:
                        columns.append({"name": col_name, "type": "Text"})  # standard fallback type
                    
                    # Fetch only up to limit rows
                    fetched_rows = result.fetchmany(limit)
                    for r in fetched_rows:
                        # Convert Row to dict, formatting datetime/date objects as strings for JSON compatibility
                        row_dict = {}
                        for i, val in enumerate(r):
                            c_name = col_names[i]
                            if hasattr(val, "isoformat"):
                                row_dict[c_name] = val.isoformat()
                            else:
                                row_dict[c_name] = val
                        rows.append(row_dict)
                else:
                    error_msg = "Query executed successfully but returned no rows (e.g. DDL/DML, which should be blocked)."
        except Exception as e:
            error_msg = str(e)
            
        return rows, columns, error_msg
