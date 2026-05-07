# document-template

MIERUNEが作成するドキュメントのひな形です。顧客による書式指定がない場合に利用します。

- Markdownでドキュメントを書いて、各プロジェクトのGitHubリポジトリで管理できます。
- [Vivliostyle](https://vivliostyle.org/ja/) によって綺麗なPDFが出力されます。

既存の業務リポジトリの `/docs/` 以下にコピーするか、このリポジトリをテンプレートとしてcloneしてください。どちらが良いかはおまかせします。

## 使い方

### ① ドキュメントを書く

- `contents`以下に雛形があります。表紙・裏表紙のみ、デザインの都合上HTMLで記述しています。そのほかはMarkdownで記述することができます。
- プレビューを見ながら編集できます。

```sh
pnpm install --frozen-lockfile
pnpm run preview # ブラウザでプレビュー
```

### ② 設定ファイルを修正する

- Markdownファイルを増やした場合など、`vivliostyle.config.js`の修正が必要となることがあります。

```js
const vivliostyleConfig = {
    title: ' ', // PDFの左上に表示されるタイトル
    author: 'MIERUNE Inc.',
    // size: 'A4',
    theme: '@vivliostyle/theme-academic',
    image: 'ghcr.io/vivliostyle/cli:8.12.1',
    entry: [
        {
            path: 'contents/cover.html',
            title: '表紙',
        },
        { rel: 'contents' },
        // ページを増やしたり、ファイル名を変更した場合は、以下を修正する。
        {
            path: 'contents/chap1.md',
        },
        {
            path: 'contents/chap2.md',
        },
        {
            path: 'contents/99_BACKCOVER.html',
            title: '裏表紙',
        },
    ],
    output: ['document.pdf'], // 出力ファイル名
    workspaceDir: '.vivliostyle',
    toc: {
        title: '目次',
        htmlPath: 'index.html',
        sectionDepth: 3,
    },
};
```

### ③ ドキュメントをビルドする

Markdownで書いたドキュメントは以下のようにしてPDFにビルドできます。

```sh
pnpm install --frozen-lockfile
pnpm run build # PDFファイルが出力される
```

GitHub Actions のワークフロー `.github/workflows/build-{name}-doc.yaml` も用意されており、GitHubで Release を作ると、ドキュメントが自動でビルドされて Release にアタッチされるようになっています。適宜調整してご活用ください。

## Markdownの記法

### VFM (Vivliostyle Flavored Markdown)

Vivliostyleでは、[Vivliostyle Flavored Markdown](https://vivliostyle.github.io/vfm/#/ja/vfm) (VFM) が使えます。

使える機能: 脚注、画像キャプション、ルビ、コードブロック、数式、など。

### ページ区切り

Markdown中に以下のHTMLを挿入すると、その箇所でページ区切りされます。

```html
<div class="page-break"></div>
```

### Mermaid記法

Mermaid記法による図表にも対応しています。

    ```mermaid
    graph LR

    a --> b
    ```
