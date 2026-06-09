from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

from parallax.core.database import Base
from parallax.core.models.observation import Observation, ExperimentObservationLink


def test_observation_table_name():
    assert Observation.__tablename__ == "observations"


def test_observation_required_fields():
    cols = Observation.__table__.columns
    
    assert cols["source"].nullable is False
    assert cols["event_type"].nullable is False
    assert cols["captured_at_ms"].nullable is False
    assert cols["submission_id"].nullable is False


def test_observation_optional_fields():
    cols = Observation.__table__.columns
    
    assert cols["thread_id"].nullable is True
    assert cols["thread_name"].nullable is True
    assert cols["caller_package"].nullable is True
    assert cols["args"].nullable is True
    assert cols["return_value"].nullable is True
    assert cols["exception"].nullable is True
    assert cols["session_id"].nullable is True


def test_experiment_observation_link_hypothesis_id_is_string():
    col = ExperimentObservationLink.__table__.columns["hypothesis_id"]
    # Verify it is a String and its length is 128
    assert col.type.python_type == str
    assert col.type.length == 128


def test_experiment_observation_link_observation_id_is_uuid():
    col = ExperimentObservationLink.__table__.columns["observation_id"]
    # Check if type is UUID. python_type on UUID can be uuid.UUID
    import uuid
    assert col.type.python_type == uuid.UUID


def test_experiment_observation_link_composite_pk():
    pk = ExperimentObservationLink.__table__.primary_key
    assert len(pk.columns) == 2
    assert "hypothesis_id" in pk.columns
    assert "observation_id" in pk.columns


def test_experiment_observation_link_fk_to_hypotheses_hypothesis_id():
    col = ExperimentObservationLink.__table__.columns["hypothesis_id"]
    assert len(col.foreign_keys) == 1
    fk = list(col.foreign_keys)[0]
    assert fk.target_fullname == "hypotheses.hypothesis_id"


def test_experiment_observation_link_cascade_delete():
    # Check ondelete CASCADE for both FKs
    col_hyp = ExperimentObservationLink.__table__.columns["hypothesis_id"]
    fk_hyp = list(col_hyp.foreign_keys)[0]
    assert fk_hyp.ondelete == "CASCADE"
    
    col_obs = ExperimentObservationLink.__table__.columns["observation_id"]
    fk_obs = list(col_obs.foreign_keys)[0]
    assert fk_obs.ondelete == "CASCADE"

# You can optionally print schema compilation like user suggested
if __name__ == "__main__":
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    print(CreateTable(ExperimentObservationLink.__table__).compile(dialect=postgresql.dialect()))
