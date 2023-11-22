/* eslint-disable react/prop-types */
import React from "react";
import { createRoot } from "react-dom/client";
import { H3Map } from "@/components/Map";
import { CardDemo } from "@/components/Card";
export default function App({}) {
  return (
    <div>
      <CardDemo className="absolute top-5 right-5 z-10"></CardDemo>
      <H3Map></H3Map>
    </div>
  );
}

export function renderToDOM(container) {
  createRoot(container).render(<App />);
}
