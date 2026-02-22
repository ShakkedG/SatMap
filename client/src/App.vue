<template>
  <div class="wrap">
    <iframe class="frame" :src="legacyUrl" title="SatMap"></iframe>
  </div>
</template>

<script setup>
const base = import.meta.env.BASE_URL || "/";
const legacyUrl = (base.endsWith("/") ? base : base + "/") + "legacy.html";
</script>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
}
.wrap {
  height: 100vh;
  width: 100%;
}
.frame {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}
</style>
