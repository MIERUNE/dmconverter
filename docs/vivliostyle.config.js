// @ts-check

import { VFM } from "@vivliostyle/vfm";
import rehypeMermaid from "rehype-mermaid";

/** @type {import('@vivliostyle/cli').VivliostyleConfigSchema} */
export default {
  title: "xxxxシステム開発業務 基本設計書",
  author: "MIERUNE Inc.",
  size: "A4",
  language: "ja",
  theme: ["@vivliostyle/theme-academic", "styles/body.css"],
  image: "ghcr.io/vivliostyle/cli:10.3.1",
  entry: [
    {
      path: "contents/cover.html",
      title: "表紙",
      theme: ["@vivliostyle/theme-base", "styles/cover.css"],
    },
    {
      rel: "contents",
      theme: ["@vivliostyle/theme-academic", "styles/toc.css"],
    },
    {
      path: "contents/chap1.md",
      theme: ["@vivliostyle/theme-academic", "styles/body.css"],
    },
    {
      path: "contents/chap2.md",
      theme: ["@vivliostyle/theme-academic", "styles/body.css"],
    },
    {
      path: "contents/chap3.md",
      theme: ["@vivliostyle/theme-academic", "styles/body.css"],
    },
    {
      path: "contents/backcover.html",
      title: "裏表紙",
      theme: ["@vivliostyle/theme-base", "styles/backcover.css"],
    },
  ],
  output: ["document.pdf"],
  workspaceDir: ".vivliostyle", // directory which is saved intermediate files.
  toc: {
    title: "目次",
    sectionDepth: 3,
  },
  vfm: {
    math: true,
  },
  documentProcessor: (config, metadata) =>
    // 参考: https://zenn.dev/mura_mi/articles/4f08cc99f19887
    // @ts-ignore
    VFM(config, metadata).use(rehypeMermaid, { strategy: "img-svg" }),
};
