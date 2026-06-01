alter table if exists race_meetings add column if not exists data_source text not null default 'official_api';
alter table if exists races add column if not exists data_source text not null default 'official_api';
alter table if exists jockeys add column if not exists data_source text not null default 'official_api';
alter table if exists trainers add column if not exists data_source text not null default 'official_api';
alter table if exists runners add column if not exists data_source text not null default 'official_api';
alter table if exists odds_snapshots add column if not exists data_source text not null default 'official_api';
alter table if exists results add column if not exists data_source text not null default 'official_api';
alter table if exists api_sync_runs add column if not exists data_source text not null default 'official_api';
alter table if exists model_ratings add column if not exists suggested_staking_unit double precision;

create index if not exists ix_race_meetings_data_source on race_meetings(data_source);
create index if not exists races_data_source_idx on races(data_source);
create index if not exists odds_snapshots_data_source_idx on odds_snapshots(data_source);
create index if not exists api_sync_runs_data_source_idx on api_sync_runs(data_source);
