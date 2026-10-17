<script setup lang="ts">
/** 全站退出/失效监听；认证结果保持原有行为，仅管理拼豆本地数据。 */
import { watch } from "vue";
import { ElMessage } from "element-plus";
import { useAuthStore } from "@/stores/auth";
import { cancelBeadDialogs } from "./dialogs.ts";
import { transitionOwner, beadStorageNotice } from "./session.ts";
const auth = useAuthStore();
watch(beadStorageNotice, (notice) => {
  if (notice) {
    ElMessage.warning(notice);
    beadStorageNotice.value = "";
  }
});
watch(
  () => auth.user?.id,
  (id) => {
    cancelBeadDialogs();
    transitionOwner(id == null ? "guest" : `user:${id}`);
  },
  { immediate: true, flush: "sync" },
);
</script>
<template><!-- 独立持久化监听，无界面。 --></template>
