/// <reference types="react" />

// Type declarations for the cubing <twisty-player> web component
// Augments React's IntrinsicElements so JSX accepts <twisty-player> without errors.
declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "twisty-player": React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          puzzle?: string;
          alg?: string;
          "experimental-setup-alg"?: string;
          visualization?: string;
          "camera-latitude"?: string | number;
          "camera-longitude"?: string | number;
          "back-view"?: string;
          "control-panel"?: string;
          "tempo-scale"?: string | number;
        },
        HTMLElement
      >;
    }
  }
}

export {};
