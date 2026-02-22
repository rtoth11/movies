# This can be created by opening the scripts page of a genre (i.e: https://www.scriptslug.com/scripts/genre/adventure),
# using the "Copy as cURL (bash)" button on the appropriate gql request in the console, inserting it into
# https://curlconverter.com/ , then adding the content here.

json_data = {
    'operationName': 'GetScripts',
    'variables': {
        'relationId': 10540,
        'offset': 0,
        'limit': 1501,
        'orderBy': 'year DESC, postDate DESC',
    },
    'query': 'query GetScripts($relationId: [QueryArgument] = null, $offset: Int, $limit: Int, $type: [String], $orderBy: String) {\n  scriptsEntries(\n    comingSoon: false\n    relatedTo: $relationId\n    type: $type\n    offset: $offset\n    limit: $limit\n    orderBy: $orderBy\n  ) {\n    ... on filmScript_Entry {\n      uri\n      poster {\n        url\n        x: imagerTransform(transform: "posterMd") {\n          url\n          width\n          height\n          mimeType\n          __typename\n        }\n        __typename\n      }\n      scriptTitle\n      year\n      dateUpdated @formatDateTime(format: "YmdHis")\n      typeHandle\n      __typename\n    }\n    ... on seriesScript_Entry {\n      uri\n      poster {\n        url\n        x: imagerTransform(transform: "posterMd") {\n          url\n          width\n          height\n          mimeType\n          __typename\n        }\n        __typename\n      }\n      seriesTitle {\n        ... on series_Entry {\n          seriesTitle\n          __typename\n        }\n        __typename\n      }\n      year\n      episodeTitle\n      seasonNumber\n      episodeNumber\n      dateUpdated @formatDateTime(format: "YmdHis")\n      typeHandle\n      __typename\n    }\n    ... on podcastScript_Entry {\n      uri\n      poster {\n        url\n        x: imagerTransform(transform: "posterMd") {\n          url\n          width\n          height\n          mimeType\n          __typename\n        }\n        __typename\n      }\n      seriesTitle {\n        ... on series_Entry {\n          seriesTitle\n          __typename\n        }\n        __typename\n      }\n      year\n      episodeTitle\n      seasonNumber\n      episodeNumber\n      dateUpdated @formatDateTime(format: "YmdHis")\n      typeHandle\n      __typename\n    }\n    __typename\n  }\n}',
}
