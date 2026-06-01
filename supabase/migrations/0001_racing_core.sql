create table if not exists race_meetings (
    id bigserial primary key,
    provider text not null,
    external_id text not null,
    meeting_date date not null,
    track_name text not null,
    country text,
    state text,
    track_condition text,
    weather text,
    data_quality_status text not null default 'sufficient',
    missing_data_fields jsonb not null default '[]'::jsonb,
    raw_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_race_meetings_provider_external unique (provider, external_id)
);

create table if not exists races (
    id bigserial primary key,
    meeting_id bigint not null references race_meetings(id) on delete cascade,
    provider text not null,
    external_id text not null,
    race_number integer,
    name text not null,
    start_time timestamptz not null,
    distance_meters integer,
    race_class text,
    status text not null default 'scheduled',
    track_condition text,
    data_quality_status text not null default 'sufficient',
    missing_data_fields jsonb not null default '[]'::jsonb,
    raw_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_races_provider_external unique (provider, external_id)
);

create table if not exists jockeys (
    id bigserial primary key,
    provider text not null,
    external_id text not null,
    name text not null,
    raw_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_jockeys_provider_external unique (provider, external_id)
);

create table if not exists trainers (
    id bigserial primary key,
    provider text not null,
    external_id text not null,
    name text not null,
    raw_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_trainers_provider_external unique (provider, external_id)
);

create table if not exists runners (
    id bigserial primary key,
    race_id bigint not null references races(id) on delete cascade,
    provider text not null,
    external_id text not null,
    horse_name text not null,
    barrier integer,
    weight_kg numeric(5, 2),
    jockey_id bigint references jockeys(id),
    trainer_id bigint references trainers(id),
    past_form jsonb not null default '[]'::jsonb,
    scratched boolean not null default false,
    data_quality_status text not null default 'sufficient',
    missing_data_fields jsonb not null default '[]'::jsonb,
    raw_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_runners_race_provider_external unique (race_id, provider, external_id)
);

create table if not exists odds_snapshots (
    id bigserial primary key,
    race_id bigint not null references races(id) on delete cascade,
    runner_id bigint not null references runners(id) on delete cascade,
    provider text not null,
    bookmaker text not null,
    market_type text not null default 'win',
    odds_decimal numeric(8, 3) not null,
    fetched_at timestamptz not null default now(),
    market_movement jsonb not null default '{}'::jsonb,
    raw_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists results (
    id bigserial primary key,
    race_id bigint not null references races(id) on delete cascade,
    runner_id bigint not null references runners(id) on delete cascade,
    provider text not null,
    position integer,
    margin numeric(8, 3),
    starting_price numeric(8, 3),
    result_status text not null default 'pending',
    raw_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_results_race_runner unique (race_id, runner_id)
);

create table if not exists model_ratings (
    id bigserial primary key,
    race_id bigint not null references races(id) on delete cascade,
    runner_id bigint not null references runners(id) on delete cascade,
    calculation_version text not null default 'v1',
    win_probability double precision,
    fair_odds numeric(8, 3),
    bookmaker_odds numeric(8, 3),
    expected_value double precision,
    confidence_score double precision,
    confidence_label text not null default 'insufficient data',
    rating_score double precision,
    data_quality_status text not null default 'sufficient',
    missing_data_fields jsonb not null default '[]'::jsonb,
    calculation_inputs jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_model_ratings_version unique (race_id, runner_id, calculation_version)
);

create table if not exists api_sync_runs (
    id bigserial primary key,
    provider text not null,
    sync_type text not null,
    status text not null default 'running',
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    records_processed integer not null default 0,
    missing_data_fields jsonb not null default '[]'::jsonb,
    error_message text,
    metadata_json jsonb not null default '{}'::jsonb
);

create index if not exists ix_race_meetings_date_track on race_meetings(meeting_date, track_name);
create index if not exists ix_races_meeting_start on races(meeting_id, start_time);
create index if not exists ix_runners_race_horse on runners(race_id, horse_name);
create index if not exists ix_odds_snapshots_runner_fetched on odds_snapshots(runner_id, fetched_at);
create index if not exists ix_odds_snapshots_race_bookmaker on odds_snapshots(race_id, bookmaker);
create index if not exists ix_model_ratings_expected_value on model_ratings(expected_value);
create index if not exists ix_api_sync_runs_provider_type_started on api_sync_runs(provider, sync_type, started_at);
