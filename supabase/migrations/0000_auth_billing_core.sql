create table if not exists users (
    id bigserial primary key,
    email text not null unique,
    hashed_password text not null,
    role text not null default 'user',
    subscription_status text not null default 'inactive',
    stripe_customer_id text,
    stripe_subscription_id text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists invoices (
    id bigserial primary key,
    total double precision not null,
    created_at timestamptz not null default now()
);

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

create index if not exists ix_users_email on users(email);
create index if not exists ix_users_stripe_customer_id on users(stripe_customer_id);
create index if not exists ix_users_stripe_subscription_id on users(stripe_subscription_id);
create index if not exists ix_subscriptions_user_id on subscriptions(user_id);
create index if not exists ix_subscriptions_status on subscriptions(status);
