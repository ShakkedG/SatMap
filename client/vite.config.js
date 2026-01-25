import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  // חשוב: זה חייב להיות שם הריפו בדיוק (SatMap)
  base: "/SatMap/",
  plugins: [vue()],
});
