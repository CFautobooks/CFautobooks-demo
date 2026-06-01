alter table if exists users add column if not exists role text not null default 'user';
alter table if exists users add column if not exists subscription_status text not null default 'inactive';
alter table if exists users add column if not exists stripe_customer_id text;
alter table if exists users add column if not exists stripe_subscription_id text;
alter table if exists users add column if not exists created_at timestamptz not null default now();
alter table if exists users add column if not exists updated_at timestamptz not null default now();

create table if not exists subscriptions (
    id bigserial primary key,
    user_id bigint not null references users(id) on delete cascade,
    stripe_customer_id text,
    stripe_subscription_id text,
    status text not null default 'inactive',
    price_id text,
    current_period_end timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_subscriptions_stripe_subscription_id unique (stripe_subscription_id)
);

create index if not exists ix_users_stripe_customer_id on users(stripe_customer_id);
create index if not exists ix_users_stripe_subscription_id on users(stripe_subscription_id);
create index if not exists ix_subscriptions_user_id on subscriptions(user_id);
create index if not exists ix_subscriptions_status on subscriptions(status);
