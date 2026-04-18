with source as (
    select distinct session_id
    from {{ ref('silver_searches') }}
)

select distinct source.session_id
from source

{% if is_incremental() %}
left join {{ this }} t
  on source.session_id = t.session_id
where t.session_id is null
{% endif %}
