import {Deck} from '@deck.gl/core';
import {GeoJsonLayer} from "@deck.gl/layers";
import {DebugH3BBoxTileLayer, DebugH3TileLayer, H3TileLayer} from "./h3-tile-layer";


const COUNTRIES =
    'https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_scale_rank.geojson'; //eslint-disable-line

const INITIAL_VIEW_STATE = {
    latitude: 51.47,
    longitude: 0.45,
    zoom: 3,
    bearing: 0,
    pitch: 0
};


const deck = new Deck({
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
        DebugH3TileLayer,
        // DebugH3BBoxTileLayer
    ],
    getTooltip: ({ object }) => object && `${Object.keys(object)[0]}: ${(+Object.values(object)[0]).toFixed(2)}`
});
