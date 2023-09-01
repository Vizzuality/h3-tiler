// FIXME: this is only a placeholder for the actual implementation of H3TileSet :_)

import {_Tileset2D as Tileset2D, TileLayer} from '@deck.gl/geo-layers';
import {cellToParent, getResolution, polygonToCells} from "h3-js"

export class H3Tileset2D extends Tileset2D {
    getTileIndices(opts) {
        // get z level from viewport original implementation
        let z = Math.min(Math.max(Math.floor(opts.viewport.zoom) - 3, 0), 5);
        console.log(opts)
        console.log(z)
        // [minX, minY, maxX, maxY]
        const bounds = opts.viewport.getBounds();
        const polygon = [
            [bounds[0], bounds[1]],
            [bounds[0], bounds[3]],
            [bounds[2], bounds[3]],
            [bounds[2], bounds[1]],
        ]
        return polygonToCells(polygon, z, true).map(h3index => ({"h3index": h3index}));
    }

    getTileId({h3index}) {
        return h3index;
    }

    getTileZoom({h3index}) {
        return getResolution(h3index);
    }

    getParentIndex({h3index}) {
        const res = getResolution(h3index);
        return {"h3index": cellToParent(h3index, res - 1)};
    }
}
