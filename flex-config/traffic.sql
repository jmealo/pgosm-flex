COMMENT ON TABLE osm.traffic_point IS 'Generated by osm2pgsql Flex output using pgosm/flex-config/traffic.lua';


ALTER TABLE osm.traffic_point
    ADD CONSTRAINT pk_osm_traffic_point_node_id
    PRIMARY KEY (node_id)
;


CREATE INDEX ix_osm_traffic_point_type ON osm.traffic_point (osm_type);