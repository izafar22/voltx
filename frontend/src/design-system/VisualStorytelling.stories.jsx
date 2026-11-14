import React from "react";
import {
  StoryImage,
  storyAssets,
} from "../pages/public/storytelling/StoryImage";
import "../pages/public/PublicPage.css";
import "../pages/public/storytelling/StoryPages.css";
export default {
  title: "Patterns/Visual Storytelling",
  parameters: {
    docs: {
      description: {
        component:
          "Reviewed fictional AI-generated scenes, not actual RushX people, facilities or completed repairs. Local responsive WebP assets with intrinsic geometry. Exact source review and generation prompts are documented in VISUAL_STORYTELLING.md.",
      },
    },
  },
};
export const Scene = {
  args: {
    asset: "pcb",
    caption: "Fictional electronics rework concept, not a repair instruction.",
  },
  argTypes: { asset: { control: "select", options: Object.keys(storyAssets) } },
  render: (args) => (
    <div className="rx-public" style={{ maxWidth: 640, padding: 16 }}>
      <StoryImage {...args} />
    </div>
  ),
};
