
-- Use JSON encoder
local json = require('dkjson')

-- Change SRID if desired
local srid = 3857

local tables = {}

tables.place_point = osm2pgsql.define_node_table('place_point', {
    { column = 'osm_type',     type = 'text', not_null = true },
    { column = 'tags',     type = 'jsonb' },
    { column = 'geom',     type = 'point' , projection = srid},
}, { schema = 'osm' })

tables.place_line = osm2pgsql.define_way_table('place_line', {
    { column = 'osm_type',     type = 'text', not_null = true },
    { column = 'tags',     type = 'jsonb' },
    { column = 'geom',     type = 'linestring', projection = srid },
}, { schema = 'osm' })


tables.place_polygon = osm2pgsql.define_way_table('place_polygon', {
    { column = 'osm_type',     type = 'text' , not_null = true},
    { column = 'tags',     type = 'jsonb' },
    { column = 'geom',     type = 'multipolygon', projection = srid },
}, { schema = 'osm' })



function clean_tags(tags)
    tags.odbl = nil
    tags.created_by = nil
    tags.source = nil
    tags['source:ref'] = nil

    return next(tags) == nil
end


function place_process_node(object)
    -- We are only interested in place details
    if not object.tags.place then
        return
    end

    clean_tags(object.tags)

    -- Using grab_tag() removes from remaining key/value saved to Pg
    local osm_type = object:grab_tag('place')

    tables.place_point:add_row({
        tags = json.encode(object.tags),
        osm_type = osm_type,
        geom = { create = 'point' }
    })

end

-- Change function name here
function place_process_way(object)
    -- We are only interested in highways
    if not object.tags.place then
        return
    end

    clean_tags(object.tags)

    local osm_type = object:grab_tag('place')


    if object.is_closed then
        tables.place_polygon:add_row({
            tags = json.encode(object.tags),
            osm_type = osm_type,
            geom = { create = 'area' }
        })
    else
        tables.place_line:add_row({
            tags = json.encode(object.tags),
            osm_type = osm_type,
            geom = { create = 'line' }
        })
    end
    
end


-- deep_copy based on copy2: https://gist.github.com/tylerneylon/81333721109155b2d244
function deep_copy(obj)
    if type(obj) ~= 'table' then return obj end
    local res = setmetatable({}, getmetatable(obj))
    for k, v in pairs(obj) do res[deep_copy(k)] = deep_copy(v) end
    return res
end


if osm2pgsql.process_node == nil then
    -- Change function name here
    osm2pgsql.process_node = place_process_node
else
    local nested = osm2pgsql.process_node
    osm2pgsql.process_node = function(object)
        local object_copy = deep_copy(object)
        nested(object)
        -- Change function name here
        place_process_node(object_copy)
    end
end



if osm2pgsql.process_way == nil then
    -- Change function name here
    osm2pgsql.process_way = place_process_way
else
    local nested = osm2pgsql.process_way
    osm2pgsql.process_way = function(object)
        local object_copy = deep_copy(object)
        nested(object)
        -- Change function name here
        place_process_way(object_copy)
    end
end