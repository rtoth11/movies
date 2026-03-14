{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append'
) }}

with source as (
    select
        tmdb_id,
        title,
        year,
        current_timestamp() as inserted_at
    from {{ source('bronze', 'bronze_json_movies') }}
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
  on source.tmdb_id = t.tmdb_id
where t.tmdb_id is null
{% endif %}
