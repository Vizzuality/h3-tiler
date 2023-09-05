import {Deck} from '@deck.gl/core';
import {H3HexagonLayer, TileLayer} from '@deck.gl/geo-layers';
import {GeoJsonLayer} from "@deck.gl/layers";
import chroma from 'chroma-js';
import {H3Tileset2D} from "./h3-tile-layer";


const COUNTRIES =
    'https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_scale_rank.geojson'; //eslint-disable-line

const INITIAL_VIEW_STATE = {
    latitude: 51.47,
    longitude: 0.45,
    zoom: 3,
    bearing: 0,
    pitch: 0
};

const colorScale = chroma.scale("OrRd").domain([0, 135]);

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
            TilesetClass: H3Tileset2D,
            id: 'tile-layer',
            // data: 'http://127.0.0.1:8000/tile/{z}/{x}/{y}',
            data: 'http://127.0.0.1:8000/h3index/{h3index}',
            minZoom: 2,
            maxZoom: 6,
            tileSize: 512,
            maxRequests: 10,  // max simultaneous requests. 0 means unlimited
            renderSubLayers: props => {
                const {bbox: {west, south, east, north}} = props.tile;
                const h3Indexes = props.data; // List of H3 indexes for the tile
                return new H3HexagonLayer({
                    id: `h3-layer`,
                    data: h3Indexes,
                    highPrecision: 'auto',
                    pickable: true,
                    wireframe: false,
                    filled: true,
                    extruded: false,
                    stroked: false,
                    getHexagon: d => d.h3index,
                    getFillColor: d => colorScale(d.value).rgb(),
                    getLineColor: [0, 0, 255, 255],
                    lineWidthUnits: 'pixels',
                    lineWidth: 1,
                });
            }
        }),
    ],
    // getTooltip: ({ object }) => object && `h3index: ${object.h3index}, value: ${object.value}`
});
