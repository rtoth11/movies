with source as (
    select
        md5(concat_ws('||', s.movie_tmdb_id, s.index_in_script)) as id,
        s.index_in_script,
        length(s.dialogue) as dialogue_length,
        case
            when length(s.suffix) = 0 then false
            else true
        end as has_suffix,
        case
            when length(s.parentheticals) = 0 then false
            else true
        end as has_parentheticals,
        s.movie_tmdb_id,
        md5(concat_ws('||', s.character, c.actor_tmdb_id, s.movie_tmdb_id)) as character_id,
        c.actor_tmdb_id
    from {{ ref('silver_script_blocks') }} s
    inner join {{ ref('silver_character_actor_map') }} c
        on s.movie_tmdb_id = c.movie_tmdb_id
        and s.character = c.character_name
    where s.type = 'dialogue'
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
  on source.id = t.id
where t.id is null
{% endif %}
