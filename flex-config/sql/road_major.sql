COMMENT ON TABLE osm.road_major IS 'OpenStreetMap roads - Major only. Classification handled by helpers.major_road(). Generated by osm2pgsql Flex output using pgosm-flex/flex-config/road_major.lua';
COMMENT ON COLUMN osm.road_major.osm_type IS 'Value from "highway" key from OpenStreetMap data.  e.g. motorway, residential, etc.';
COMMENT ON COLUMN osm.road_major.maxspeed IS 'Maximum posted speed limit in kilometers per hour (km/hr).  Units not enforced by OpenStreetMap.  Please fix values in MPH in OpenStreetMap.org to either the value in km/hr OR with the suffix "mph" so it can be properly converted.  See https://wiki.openstreetmap.org/wiki/Key:maxspeed';


COMMENT ON COLUMN osm.road_major.osm_id IS 'OpenStreetMap ID. Unique along with geometry type.';

COMMENT ON COLUMN osm.road_major.layer IS 'Vertical ordering layer (Z) to handle crossing/overlapping features. "All ways without an explicit value are assumed to have layer 0." - per Wiki - https://wiki.openstreetmap.org/wiki/Key:layer';
COMMENT ON COLUMN osm.road_major.bridge IS 'If empty, assume not a bridge.  If not empty, check value for details.';
COMMENT ON COLUMN osm.road_major.tunnel IS 'If empty, assume not a tunnel.  If not empty, check value for details.';
COMMENT ON COLUMN osm.road_major.name IS 'Best name option determined by helpers.get_name(). Keys with priority are: name, short_name, alt_name and loc_name.  See pgosm-flex/flex-config/helpers.lua for full logic of selection.';
COMMENT ON COLUMN osm.road_major.geom IS 'Geometry loaded by osm2pgsql.';

COMMENT ON COLUMN osm.road_major.ref IS 'Reference number or code. Best ref option determined by helpers.get_ref(). https://wiki.openstreetmap.org/wiki/Key:ref';


ALTER TABLE osm.road_major
	ADD CONSTRAINT pk_osm_road_major_osm_id
    PRIMARY KEY (osm_id)
;



------------------------------------------------

CREATE TEMP TABLE road_major_in_relations AS
SELECT p_no_rel.osm_id
    FROM osm.road_major p_no_rel
    WHERE osm_id > 0
        AND EXISTS (SELECT * 
            FROM (SELECT i.osm_id AS relation_id, 
                        jsonb_array_elements_text(i.member_ids)::BIGINT AS member_id
                    FROM osm.road_major i
                    WHERE i.osm_id < 0
                    ) rel
            WHERE rel.member_id = p_no_rel.osm_id
            ) 
;


DELETE
    FROM osm.road_major p
    WHERE EXISTS (
        SELECT osm_id
            FROM road_major_in_relations pir
            WHERE p.osm_id = pir.osm_id
    )
;

