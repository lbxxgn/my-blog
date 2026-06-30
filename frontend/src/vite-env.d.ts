/// <reference types="vite/client" />

declare module '*.css' {
  const content: string;
  export default content;
}

declare module '@blocknote/core/fonts/inter.css' {
  const content: string;
  export default content;
}

declare module '@blocknote/mantine/style.css' {
  const content: string;
  export default content;
}
