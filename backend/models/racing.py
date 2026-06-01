from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from backend.core.database import Base


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Meeting(Base, TimestampMixin):
    __tablename__ = "race_meetings"
    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_race_meetings_provider_external"),
        Index("ix_race_meetings_date_track", "meeting_date", "track_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(80), nullable=False)
    external_id = Column(String(160), nullable=False)
    meeting_date = Column(Date, nullable=False, index=True)
    track_name = Column(String(255), nullable=False)
    country = Column(String(80))
    state = Column(String(80))
    track_condition = Column(String(120))
    weather = Column(String(120))
    data_quality_status = Column(String(40), default="sufficient", nullable=False)
    missing_data_fields = Column(JSON, default=list, nullable=False)
    raw_payload = Column(JSON, default=dict, nullable=False)

    races = relationship("Race", back_populates="meeting", cascade="all, delete-orphan")


class Race(Base, TimestampMixin):
    __tablename__ = "races"
    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_races_provider_external"),
        Index("ix_races_meeting_start", "meeting_id", "start_time"),
    )

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("race_meetings.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(80), nullable=False)
    external_id = Column(String(160), nullable=False)
    race_number = Column(Integer)
    name = Column(String(255), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    distance_meters = Column(Integer)
    race_class = Column(String(120))
    status = Column(String(80), default="scheduled", nullable=False)
    track_condition = Column(String(120))
    data_quality_status = Column(String(40), default="sufficient", nullable=False)
    missing_data_fields = Column(JSON, default=list, nullable=False)
    raw_payload = Column(JSON, default=dict, nullable=False)

    meeting = relationship("Meeting", back_populates="races")
    runners = relationship("Runner", back_populates="race", cascade="all, delete-orphan")
    odds_snapshots = relationship("OddsSnapshot", back_populates="race", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="race", cascade="all, delete-orphan")
    model_ratings = relationship("ModelRating", back_populates="race", cascade="all, delete-orphan")


class Jockey(Base, TimestampMixin):
    __tablename__ = "jockeys"
    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_jockeys_provider_external"),)

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(80), nullable=False)
    external_id = Column(String(160), nullable=False)
    name = Column(String(255), nullable=False)
    raw_payload = Column(JSON, default=dict, nullable=False)

    runners = relationship("Runner", back_populates="jockey")


class Trainer(Base, TimestampMixin):
    __tablename__ = "trainers"
    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_trainers_provider_external"),)

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(80), nullable=False)
    external_id = Column(String(160), nullable=False)
    name = Column(String(255), nullable=False)
    raw_payload = Column(JSON, default=dict, nullable=False)

    runners = relationship("Runner", back_populates="trainer")


class Runner(Base, TimestampMixin):
    __tablename__ = "runners"
    __table_args__ = (
        UniqueConstraint("race_id", "provider", "external_id", name="uq_runners_race_provider_external"),
        Index("ix_runners_race_horse", "race_id", "horse_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(80), nullable=False)
    external_id = Column(String(160), nullable=False)
    horse_name = Column(String(255), nullable=False)
    barrier = Column(Integer)
    weight_kg = Column(Numeric(5, 2))
    jockey_id = Column(Integer, ForeignKey("jockeys.id"))
    trainer_id = Column(Integer, ForeignKey("trainers.id"))
    past_form = Column(JSON, default=list, nullable=False)
    scratched = Column(Boolean, default=False, nullable=False)
    data_quality_status = Column(String(40), default="sufficient", nullable=False)
    missing_data_fields = Column(JSON, default=list, nullable=False)
    raw_payload = Column(JSON, default=dict, nullable=False)

    race = relationship("Race", back_populates="runners")
    jockey = relationship("Jockey", back_populates="runners")
    trainer = relationship("Trainer", back_populates="runners")
    odds_snapshots = relationship("OddsSnapshot", back_populates="runner", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="runner", cascade="all, delete-orphan")
    model_ratings = relationship("ModelRating", back_populates="runner", cascade="all, delete-orphan")


class OddsSnapshot(Base, TimestampMixin):
    __tablename__ = "odds_snapshots"
    __table_args__ = (
        Index("ix_odds_snapshots_runner_fetched", "runner_id", "fetched_at"),
        Index("ix_odds_snapshots_race_bookmaker", "race_id", "bookmaker"),
    )

    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id", ondelete="CASCADE"), nullable=False)
    runner_id = Column(Integer, ForeignKey("runners.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(80), nullable=False)
    bookmaker = Column(String(120), nullable=False)
    market_type = Column(String(80), default="win", nullable=False)
    odds_decimal = Column(Numeric(8, 3), nullable=False)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    market_movement = Column(JSON, default=dict, nullable=False)
    raw_payload = Column(JSON, default=dict, nullable=False)

    race = relationship("Race", back_populates="odds_snapshots")
    runner = relationship("Runner", back_populates="odds_snapshots")


class Result(Base, TimestampMixin):
    __tablename__ = "results"
    __table_args__ = (UniqueConstraint("race_id", "runner_id", name="uq_results_race_runner"),)

    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id", ondelete="CASCADE"), nullable=False)
    runner_id = Column(Integer, ForeignKey("runners.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(80), nullable=False)
    position = Column(Integer)
    margin = Column(Numeric(8, 3))
    starting_price = Column(Numeric(8, 3))
    result_status = Column(String(80), default="pending", nullable=False)
    raw_payload = Column(JSON, default=dict, nullable=False)

    race = relationship("Race", back_populates="results")
    runner = relationship("Runner", back_populates="results")


class ModelRating(Base, TimestampMixin):
    __tablename__ = "model_ratings"
    __table_args__ = (
        UniqueConstraint("race_id", "runner_id", "calculation_version", name="uq_model_ratings_version"),
        Index("ix_model_ratings_expected_value", "expected_value"),
    )

    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id", ondelete="CASCADE"), nullable=False)
    runner_id = Column(Integer, ForeignKey("runners.id", ondelete="CASCADE"), nullable=False)
    calculation_version = Column(String(40), default="v1", nullable=False)
    win_probability = Column(Float)
    fair_odds = Column(Numeric(8, 3))
    bookmaker_odds = Column(Numeric(8, 3))
    expected_value = Column(Float)
    confidence_score = Column(Float)
    confidence_label = Column(String(40), default="insufficient data", nullable=False)
    rating_score = Column(Float)
    data_quality_status = Column(String(40), default="sufficient", nullable=False)
    missing_data_fields = Column(JSON, default=list, nullable=False)
    calculation_inputs = Column(JSON, default=dict, nullable=False)

    race = relationship("Race", back_populates="model_ratings")
    runner = relationship("Runner", back_populates="model_ratings")


class SyncRun(Base):
    __tablename__ = "api_sync_runs"
    __table_args__ = (
        Index("ix_api_sync_runs_provider_type_started", "provider", "sync_type", "started_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(80), nullable=False)
    sync_type = Column(String(80), nullable=False)
    status = Column(String(40), default="running", nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    records_processed = Column(Integer, default=0, nullable=False)
    missing_data_fields = Column(JSON, default=list, nullable=False)
    error_message = Column(Text)
    metadata_json = Column(JSON, default=dict, nullable=False)
