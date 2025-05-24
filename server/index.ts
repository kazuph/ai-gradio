import { Hono } from "hono";
import { basicAuth } from "hono/basic-auth";
import type { HonoEnv } from "../load-context";

const app = new Hono<HonoEnv>();

// Basic認証ミドルウェアをアプリケーション全体に追加
app.use(
  "*", // すべてのパスに適用
  basicAuth({
    verifyUser: (username, password, c) => {
      const validUsername = c.env.AUTH_USERNAME;
      const validPassword = c.env.AUTH_PASSWORD;
      return username === validUsername && password === validPassword;
    },
    realm: "Protected Area",
  })
);

export default app; 