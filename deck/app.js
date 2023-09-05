import {Deck} from '@deck.gl/core';
import {GeoJsonLayer} from "@deck.gl/layers";
import chroma from 'chroma-js';
import {DebugH3TileLayer, H3TileLayer} from "./h3-tile-layer";


const COUNTRIES =
    'https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_scale_rank.geojson'; //eslint-disable-line

const INITIAL_VIEW_STATE = {
    latitude: 51.47,
    longitude: 0.45,
    zoom: 3,
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
        H3TileLayer,
        // DebugH3TileLayer
    ],
    // getTooltip: ({ object }) => object && `h3index: ${object.h3index}, value: ${object.value}`
});
