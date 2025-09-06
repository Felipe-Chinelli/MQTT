from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL do banco de dados SQLite. Cria um arquivo 'sql_app.db' na raiz do projeto.
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

# Criar o engine para o SQLAlchemy
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} # Necessário para SQLite com FastAPI
)

# Base declarativa para nossos modelos de banco de dados
Base = declarative_base()

# Fábrica de sessões para interagir com o DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependência para obter a sessão do banco de dados (usada nos endpoints da API)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()