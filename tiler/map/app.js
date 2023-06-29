import {Deck} from '@deck.gl/core';
import {H3HexagonLayer, TileLayer} from '@deck.gl/geo-layers';
import {GeoJsonLayer} from "@deck.gl/layers";


// source: Natural Earth http://www.naturalearthdata.com/ via geojson.xyz
const COUNTRIES =
    'https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_scale_rank.geojson'; //eslint-disable-line
const AIR_PORTS =
    'https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_10m_airports.geojson';

const INITIAL_VIEW_STATE = {
    latitude: 51.47,
    longitude: 0.45,
    zoom: 4,
    bearing: 0,
    pitch: 0
};

new Deck({
    initialViewState: INITIAL_VIEW_STATE,
    controller: true,
    layers: [
        new GeoJsonLayer({
            id: 'base-map',
            data: COUNTRIES,
            // Styles
            stroked: true,
            filled: true,
            lineWidthMinPixels: 2,
            opacity: 0.4,
            getLineColor: [60, 60, 60],
            getFillColor: [200, 200, 200]
        }),
        new TileLayer({
            id: 'tile-layer',
            data: 'http://127.0.0.1:8000/{z}/{x}/{y}',
            minZoom: 2,
            maxZoom: 6,
            tileSize: 512,
            renderSubLayers: props => {
                const {bbox: {west, south, east, north}} = props.tile;
                const h3Indexes = props.data; // List of H3 indexes for the tile
                return new H3HexagonLayer({
                    id: `h3-layer`,
                    data: h3Indexes,
                    highPrecision: true,
                    pickable: true,
                    wireframe: false,
                    filled: true,
                    extruded: false,
                    stroked: false,
                    getHexagon: d => d.h3index,
                    getFillColor: d => [100, 0, (1 - d.value)  * 255, 255],
                    getLineColor: [0, 0, 255, 255],
                    lineWidthUnits: 'pixels',
                    lineWidth: 1,
                });
            }
        }),
    ],
    getTooltip: ({object}) => object && `x: ${object.tile.x}, y: ${object.tile.y}, z: ${object.tile.z}, value: ${object.value}`
});