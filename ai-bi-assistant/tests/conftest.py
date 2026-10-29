import pytest
from app.database import initialize_database
from app.ingestion import ingest_csv

@pytest.fixture
def test_db(tmp_path):
    db = str(tmp_path / "test.db")
    initialize_database(db)
    return db

@pytest.fixture
def populated_db(test_db):
    from pathlib import Path
    csv_path = Path(__file__).resolve().parents[1] / "data" / "sales_data.csv"
    ingest_csv(csv_path, test_db)
    return test_db
