<script setup lang="ts">
/** 图纸画布只做观察；指针拖动及双指缩放不会改写网格。 */
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import type { BeadColor, BeadPattern } from "./types.ts";
import { paintGrid } from "./export.ts";
const props = defineProps<{ pattern: BeadPattern; colors: BeadColor[] }>();
const viewport = ref<HTMLDivElement>(),
  canvas = ref<HTMLCanvasElement>(),
  codes = ref(false);
const scale = ref(1),
  x = ref(0),
  y = ref(0),
  hovered = ref("拖动平移 · 滚轮或双指缩放");
const transform = computed(
  () => `translate(${x.value}px, ${y.value}px) scale(${scale.value})`,
);
const points = new Map<number, { x: number; y: number }>();
let observer: ResizeObserver | null = null;
function fit() {
  const box = viewport.value;
  if (!box) return;
  scale.value = Math.min(
    (box.clientWidth - 32) / (props.pattern.width * 16),
    (box.clientHeight - 32) / (props.pattern.height * 16),
    2,
  );
  x.value = (box.clientWidth - props.pattern.width * 16 * scale.value) / 2;
  y.value = (box.clientHeight - props.pattern.height * 16 * scale.value) / 2;
}
function zoom(
  factor: number,
  atX = (viewport.value?.clientWidth ?? 0) / 2,
  atY = (viewport.value?.clientHeight ?? 0) / 2,
) {
  const next = Math.max(0.05, Math.min(8, scale.value * factor)),
    ratio = next / scale.value;
  x.value = atX - (atX - x.value) * ratio;
  y.value = atY - (atY - y.value) * ratio;
  scale.value = next;
}
function down(event: PointerEvent) {
  viewport.value?.setPointerCapture(event.pointerId);
  points.set(event.pointerId, { x: event.clientX, y: event.clientY });
}
function up(event: PointerEvent) {
  points.delete(event.pointerId);
}
function move(event: PointerEvent) {
  const previous = points.get(event.pointerId),
    rect = viewport.value!.getBoundingClientRect();
  if (previous) {
    if (points.size === 1) {
      x.value += event.clientX - previous.x;
      y.value += event.clientY - previous.y;
    } else {
      const other = [...points].find(([id]) => id !== event.pointerId)?.[1];
      if (other) {
        const oldDistance = Math.hypot(
            previous.x - other.x,
            previous.y - other.y,
          ),
          newDistance = Math.hypot(
            event.clientX - other.x,
            event.clientY - other.y,
          );
        if (oldDistance > 0)
          zoom(
            newDistance / oldDistance,
            (previous.x + other.x) / 2 - rect.left,
            (previous.y + other.y) / 2 - rect.top,
          );
        x.value += (event.clientX - previous.x) / 2;
        y.value += (event.clientY - previous.y) / 2;
      }
    }
    points.set(event.pointerId, { x: event.clientX, y: event.clientY });
  }
  const cx = Math.floor(
      (event.clientX - rect.left - x.value) / scale.value / 16,
    ),
    cy = Math.floor((event.clientY - rect.top - y.value) / scale.value / 16);
  if (
    cx >= 0 &&
    cy >= 0 &&
    cx < props.pattern.width &&
    cy < props.pattern.height
  ) {
    const color =
      props.colors[props.pattern.cells[cy * props.pattern.width + cx]!];
    hovered.value = `第 ${cy + 1} 行 · 第 ${cx + 1} 列 · ${color ? color.code + " " + color.hex : "空白，无需放豆"}`;
  }
}
function wheel(event: WheelEvent) {
  const rect = viewport.value!.getBoundingClientRect();
  zoom(
    Math.exp(-event.deltaY * 0.002),
    event.clientX - rect.left,
    event.clientY - rect.top,
  );
}
async function draw(reset = false) {
  await nextTick();
  if (canvas.value)
    paintGrid(canvas.value, props.pattern, props.colors, 16, codes.value);
  if (reset) fit();
}
watch(
  () => props.pattern,
  () => void draw(true),
);
watch(codes, () => void draw());
onMounted(() => {
  void draw(true);
  observer = new ResizeObserver(fit);
  if (viewport.value) observer.observe(viewport.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  points.clear();
  if (canvas.value) canvas.value.width = canvas.value.height = 0;
});
</script>

<template>
  <div class="pattern-tools">
    <el-checkbox v-model="codes">显示色号</el-checkbox>
    <div class="zoom-tools">
      <el-button aria-label="缩小图纸" @click="zoom(0.8)">−</el-button
      ><span>{{ Math.round(scale * 100) }}%</span
      ><el-button aria-label="放大图纸" @click="zoom(1.25)">＋</el-button
      ><el-button @click="fit">适应画布</el-button>
    </div>
  </div>
  <div
    ref="viewport"
    class="pattern-viewport"
    aria-label="拼豆图纸，可拖动和缩放"
    tabindex="0"
    @wheel.prevent="wheel"
    @pointerdown="down"
    @pointermove="move"
    @pointerup="up"
    @pointercancel="up"
    @lostpointercapture="up"
    @keydown.plus.prevent="zoom(1.25)"
    @keydown.minus.prevent="zoom(0.8)"
  >
    <canvas ref="canvas" :style="{ transform }" />
  </div>
  <div class="pattern-caption">{{ hovered }}</div>
</template>

<style scoped>
.pattern-tools,
.zoom-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.pattern-tools {
  justify-content: space-between;
  margin-bottom: 14px;
}
.zoom-tools .el-button {
  margin: 0;
  padding: 8px 10px;
}
.zoom-tools span {
  font-size: 12px;
  min-width: 42px;
  text-align: center;
  color: var(--app-muted);
}
.pattern-viewport {
  position: relative;
  height: 530px;
  overflow: hidden;
  border: 1px solid #e2e6ed;
  border-radius: 18px;
  touch-action: none;
  cursor: grab;
  background-color: #edf0f5;
  background-image: radial-gradient(#cbd1de 1px, transparent 1px);
  background-size: 16px 16px;
}
.pattern-viewport:active {
  cursor: grabbing;
}
.pattern-viewport canvas {
  position: absolute;
  left: 0;
  top: 0;
  transform-origin: 0 0;
  box-shadow: 0 14px 45px #2b344421;
  image-rendering: pixelated;
  max-width: none;
}
.pattern-viewport:focus-visible {
  outline: 3px solid var(--app-primary);
}
.pattern-caption {
  min-height: 30px;
  padding-top: 12px;
  font-size: 12px;
  color: #778090;
}
@media (max-width: 720px) {
  .pattern-viewport {
    height: 420px;
  }
  .pattern-tools {
    gap: 4px;
  }
  .zoom-tools {
    gap: 4px;
  }
  .zoom-tools .el-button {
    min-height: 36px;
  }
}
</style>
