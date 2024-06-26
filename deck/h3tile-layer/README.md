# H3TileLayer

A deck.gl custom layer for rendering h3 tiles.

## Usage

Make a layer like this:

```js
import { H3TileLayer } from "@h3deck/layers";
import { H3HexagonLayer } from "@deck.gl/geo-layers";

layer = new H3TileLayer({
  data: "http://localhost:8000/tiler/{h3index}",
  renderSubLayers: (props) => {
    return new H3HexagonLayer({
      getHexagon: (d) => Object.keys(d)[0],
    });
  },
});
```

Note that the data url is a template string that will be replaced with the h3 index of the tile. Therefore, there must
exist a server that can handle the request and return the data for the tile.

Check the demo in `demo/` for a fully working example.
