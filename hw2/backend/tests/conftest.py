import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from waitlist.db import Base, SessionLocal, engine
from waitlist.main import app
from waitlist.models import Party

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    with SessionLocal() as session:
        session.execute(delete(Party))
        session.commit()
    yield
    with SessionLocal() as session:
        session.execute(delete(Party))
        session.commit()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session() -> Session:
    with SessionLocal() as session:
        yield session
