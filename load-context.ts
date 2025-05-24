import type { Context } from "hono";
import type { AppLoadContext } from "react-router";
import type { PlatformProxy } from "wrangler";

type Cloudflare = Omit<PlatformProxy<Env, IncomingRequestCfProperties>, "dispose" | "caches"> & {
  caches: PlatformProxy<Env, IncomingRequestCfProperties>["caches"] | CacheStorage;
};

export interface HonoEnv {
  Variables: Record<string, unknown>;
  Bindings: Env;
}

declare module "react-router" {
  interface AppLoadContext {
    cloudflare: Cloudflare;
    hono?: {
      context: Context<HonoEnv>;
    };
  }
}

type GetLoadContext = (args: {
  request: Request;
  context: {
    cloudflare: Cloudflare;
    hono?: { context: Context<HonoEnv> };
  };
}) => AppLoadContext;

export const getLoadContext: GetLoadContext = ({ context }) => {
  return context;
};
