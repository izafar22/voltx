import assets from "./assets.json";
export { default as storyAssets } from "./assets.json";

export function StoryImage({ asset, priority = false, caption }) {
  const item = assets[asset];
  if (!item) return null;
  const largest = item.outputs[item.outputs.length - 1];
  return (
    <figure
      className="rx-story-image"
      style={{ "--story-ratio": `${item.width} / ${item.height}` }}
      data-story-asset={asset}
    >
      <img
        src={largest.src}
        srcSet={item.outputs.map((o) => `${o.src} ${o.width}w`).join(", ")}
        sizes="(max-width:760px) calc(100vw - 44px), (max-width:1000px) 45vw, 610px"
        width={item.width}
        height={item.height}
        alt={item.alt}
        loading={priority ? "eager" : "lazy"}
        fetchpriority={priority ? "high" : undefined}
        decoding="async"
      />
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}
