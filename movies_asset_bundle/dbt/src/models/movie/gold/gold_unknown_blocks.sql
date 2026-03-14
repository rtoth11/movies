{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append'
) }}

with source as (
    select
        md5(concat_ws('||', movie_tmdb_id, index_in_script)) as id,
        index_in_script,
        content,
        movie_tmdb_id,
        current_timestamp() as inserted_at
    from {{ ref('silver_script_blocks') }}
    where type = 'unknown'
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
  on source.id = t.id
where t.id is null
{% endif %}
