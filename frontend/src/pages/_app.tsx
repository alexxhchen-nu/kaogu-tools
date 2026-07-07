import type { AppProps } from "next/app"
import Head from "next/head"

import "@/styles/globals.css"

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>考古工具箱 · 考古工作台</title>
        <meta
          name="description"
          content="面向考古资料检索、墓葬文本抽取、墓葬建模与空间分析的工具门户前端。"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <Component {...pageProps} />
    </>
  )
}
