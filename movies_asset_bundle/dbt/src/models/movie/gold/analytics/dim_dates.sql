{{ config(
    materialized='table'
) }}

with date_spine as (
    {{
        dbt_utils.date_spine(
            datepart="day",
            start_date="cast('2026-01-01' as date)",
            end_date="cast('2030-12-31' as date)"
        )
    }}
),

final as (
    select
        date_day as date,

        cast(to_char(date_day, 'yyyyMMdd') as integer) as date_key,

        extract(year from date_day) as year,
        extract(month from date_day) as month,
        extract(day from date_day) as day,

        to_char(date_day, 'MMM') as month_name,
        to_char(date_day, 'EEE') as day_name,

        extract(dow from date_day) as day_of_week,
        extract(week from date_day) as week_of_year,

        case when extract(dow from date_day) in (1, 7) then true else false end as is_weekend,

        to_date(date_trunc('month', date_day)) as month_start,
        last_day(date_day) as month_end

    from date_spine
)

select * from final
