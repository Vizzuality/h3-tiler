// FIXME: this is only a placeholder for the actual implementation of H3TileSet :_)

import {_Tileset2D as Tileset2D} from '@deck.gl/geo-layers';
class QuadkeyTileset2D extends Tileset2D {
  getTileIndices(opts) {
    // Quadkeys and OSM tiles share the layout, leverage existing algorithm
    // Data format: [{quadkey: '0120'}, {quadkey: '0121'}, {quadkey: '0120'},...]
    return super.getTileIndices(opts).map(tileToQuadkey);
  }

  getTileId({quadkey}) {
    return quadkey;
  }

  getTileZoom({quadkey}) {
    return quadkey.length;
  }

  getParentIndex({quadkey}) {
    const quadkey = quadkey.slice(0, -1);
    return {quadkey};
  }
}

const quadkeyTileLayer = new TileLayer({
  TilesetClass: QuadkeyTileset2D,
  data: 'quadkey/{quadkey}.json',
  ...
});
