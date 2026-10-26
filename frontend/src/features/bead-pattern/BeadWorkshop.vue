<script setup lang="ts">
/** 独立拼豆工作台，展示状态和业务编排分别维护。 */
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import ImageCropper from "@/components/ImageCropper.vue";
import PatternCanvas from "./PatternCanvas.vue";
import { useWorkshop } from "./useWorkshop.ts";
import { PALETTES, getPalette } from "./palettes.ts";
import { downloadCsv, downloadProject } from "./export.ts";
const w = reactive(useWorkshop()),
  router = useRouter();
const input = ref<HTMLInputElement>(),
  projectInput = ref<HTMLInputElement>();
</script>

<template>
  <main class="bead-workshop">
    <input
      ref="input"
      class="file-input"
      type="file"
      accept="image/jpeg,image/png,image/webp,image/gif"
      aria-label="选择拼豆图片"
      @change="w.selected"
    />
    <input
      ref="projectInput"
      class="file-input"
      type="file"
      accept=".json"
      aria-label="导入拼豆项目"
      @change="w.importProject"
    />
    <section class="workshop-hero">
      <div class="hero-copy">
        <span class="eyebrow">PIXEL BEADS · 拼豆创意工坊</span>
        <h1>把喜欢的画面，<br /><em>拼成手中的小美好。</em></h1>
        <p>从一张图片出发，找到颜色、生成图纸，让灵感一颗一颗成形。</p>
        <div class="hero-tags">
          <span>本地处理</span><span>CIEDE2000 感知配色</span
          ><span>五品牌真实色号</span>
        </div>
      </div>
      <div class="hero-beads" aria-hidden="true">
        <div class="mini-board">
          <i
            v-for="i in 49"
            :key="i"
            :class="{
              light: [1, 7, 43, 49].includes(i),
              mint: i % 7 < 3,
              rose: i % 5 === 0,
            }"
          ></i>
        </div>
        <span class="floating-label">一格一豆 · 慢慢成形</span>
      </div>
    </section>
    <div class="workshop-actions">
      <div class="steps">
        <b>01 选图</b><span>—</span><b>02 配色</b><span>—</span
        ><b>03 开始创作</b>
      </div>
      <div>
        <el-button v-if="w.signedIn" type="primary" plain @click="w.openLibrary"
          >云端作品</el-button
        >
        <el-button :disabled="!w.ready" @click="projectInput?.click()"
          >导入项目</el-button
        ><el-button
          @click="
            w.draftsVisible = true;
            w.refreshDrafts();
          "
          >本地草稿
          <span class="count-badge">{{ w.drafts.length }}</span></el-button
        >
      </div>
    </div>
    <section class="persistence-strip" aria-label="作品保存设置">
      <div>
        <strong>{{
          w.signedIn
            ? "你的作品，可以跨设备继续"
            : "本地自动保存，登录后还可同步云端"
        }}</strong>
        <p>
          {{
            w.cloud
              ? "当前作品已关联云端，修改后请手动保存。"
              : "本地工作区自动恢复；云端仅在你主动保存时上传。"
          }}
        </p>
        <p v-if="w.changed" class="cloud-notice">
          参数已改变，请重新生成后再保存到云端。
        </p>
        <p v-if="w.pendingCreate" class="cloud-notice" role="status">
          有一次{{
            w.pendingCreate.asNew ? "另存" : "创建"
          }}尚未确认。重试会核对当时的图纸和图片，不会重复创建；当前修改仍保留在本地。
        </p>
      </div>
      <div class="persistence-controls">
        <el-switch
          aria-label="退出后保留本地草稿"
          v-if="w.signedIn"
          :model-value="w.retainLocal"
          active-text="退出后保留本地草稿"
          @change="w.retentionChanged"
        />
        <el-button
          type="primary"
          :loading="w.cloudBusy"
          :disabled="
            !w.project ||
            (w.changed && !w.pendingCreate) ||
            w.running ||
            !w.ready ||
            w.pendingLoading
          "
          @click="w.saveCloud()"
          >{{ w.pendingCreate ? "重试云端保存" : "保存到云端" }}</el-button
        >
        <el-button
          v-if="w.signedIn && w.project"
          :disabled="
            (w.changed && !w.pendingCreate) ||
            w.cloudBusy ||
            w.running ||
            w.pendingLoading
          "
          @click="w.saveCloud(true)"
          >{{ w.pendingCreate?.asNew ? "重试另存" : "另存为新作品" }}</el-button
        >
      </div>
      <div v-if="w.cloudError" class="cloud-error" role="alert">
        {{ w.cloudError }}
        <el-button v-if="w.cloudConflict" text @click="w.reloadCloud"
          >从云端重新载入</el-button
        >
        <span v-if="w.cloudConflict">也可使用“另存为新作品”保留当前版本。</span>
      </div>
    </section>
    <div v-loading="!w.ready" class="workshop-grid">
      <aside class="control-column">
        <section class="workshop-panel source-panel">
          <div class="panel-heading">
            <span class="section-number">01</span>
            <div>
              <h2>选择你的灵感</h2>
              <p>从本机或自己的私有空间开始</p>
            </div>
          </div>
          <div
            v-if="w.sourceUrl"
            class="source-preview"
            v-loading="w.preparing"
          >
            <img :src="w.sourceUrl" alt="当前拼豆工作源" /><el-button
              size="small"
              :disabled="w.preparing"
              @click="w.crop"
              >重新裁剪</el-button
            >
          </div>
          <button
            v-else
            class="upload-zone"
            :disabled="w.preparing"
            @click="input?.click()"
          >
            <span class="upload-symbol">＋</span
            ><strong>{{
              w.preparing ? "正在准备图片…" : "选择一张图片"
            }}</strong
            ><small
              >JPEG / PNG / WebP / GIF<br />不超过 10MB · 2500 万像素</small
            >
          </button>
          <div class="source-buttons">
            <el-button :loading="w.preparing" @click="input?.click()">{{
              w.source ? "更换本地图片" : "本地选图"
            }}</el-button
            ><el-button :disabled="w.preparing" @click="w.openPrivate"
              >私有空间导入</el-button
            >
          </div>
          <p class="privacy-note">
            <el-icon><Lock /></el-icon>图片在本机转换，不会上传到公共图库。
          </p>
        </section>
        <section class="workshop-panel">
          <div class="panel-heading">
            <span class="section-number lavender">02</span>
            <div>
              <h2>让配色更合心意</h2>
              <p>尺寸越大，制作所需豆数越多</p>
            </div>
          </div>
          <el-form label-position="top" class="bead-form">
            <el-form-item label="图纸名称"
              ><el-input
                v-model="w.name"
                maxlength="128"
                placeholder="为你的作品取个名字"
                @blur="w.renameCurrent"
            /></el-form-item>
            <el-form-item label="拼豆品牌"
              ><el-select v-model="w.paletteId"
                ><el-option
                  v-for="item in PALETTES"
                  :key="item.id"
                  :value="item.id"
                  :label="`${item.name} · ${item.colors.length} 可用色`" /></el-select
              ><small
                >收录
                {{ w.palette.nominalCount }} 色，已过滤重复及未知色号。</small
              ></el-form-item
            >
            <el-form-item
              ><template #label
                ><span>图纸最长边</span
                ><b class="parameter-value"
                  >{{ w.params.longEdge }} 格</b
                ></template
              ><el-slider
                v-model="w.params.longEdge"
                :min="20"
                :max="200"
                :step="1"
              />
              <div class="range-help">
                <span>轻巧 20</span
                ><span>{{
                  w.dimensions
                    ? `${w.dimensions.width} × ${w.dimensions.height} 格`
                    : "保持原图比例"
                }}</span
                ><span>精细 200</span>
              </div></el-form-item
            >
            <el-form-item label="最多颜色"
              ><el-input-number
                v-model="w.params.maxColors"
                :min="2"
                :max="128"
                :precision="0"
                controls-position="right"
              />
              <div class="color-presets">
                <button
                  v-for="n in [16, 24, 40, 64]"
                  :key="n"
                  :class="{ active: w.params.maxColors === n }"
                  @click.prevent="w.params.maxColors = n"
                >
                  {{ n }} 色
                </button>
              </div></el-form-item
            >
            <el-collapse class="cleanup-options"
              ><el-collapse-item name="cleanup" title="背景与细节处理"
                ><div class="switch-row">
                  <span>去除外部背景</span
                  ><el-switch v-model="w.params.removeBackground" />
                </div>
                <template v-if="w.params.removeBackground"
                  ><div class="background-controls">
                    <el-checkbox
                      :model-value="w.params.backgroundColor !== null"
                      @change="
                        w.params.backgroundColor = $event ? '#ffffff' : null
                      "
                      >手动指定背景色</el-checkbox
                    ><el-color-picker
                      v-if="w.params.backgroundColor !== null"
                      v-model="w.params.backgroundColor"
                      color-format="hex"
                    />
                  </div>
                  <el-slider
                    v-model="w.params.tolerance"
                    :min="0"
                    :max="40"
                    show-input
                  /><small
                    >容差 {{ w.params.tolerance }} ·
                    只去除与边缘连通的区域</small
                  ></template
                >
                <div class="denoise-label">清理孤立杂点</div>
                <el-select v-model="w.params.denoise"
                  ><el-option
                    :value="0"
                    label="关闭 · 保留所有细节" /><el-option
                    :value="1"
                    label="清理单格杂点" /><el-option
                    :value="2"
                    label="清理不超过两格的杂点" /></el-select></el-collapse-item
            ></el-collapse>
          </el-form>
          <el-button
            type="primary"
            size="large"
            class="generate-button"
            :disabled="!w.source || w.preparing"
            @click="w.generate"
            ><el-icon><MagicStick /></el-icon
            >{{ w.running ? "重新生成" : "生成拼豆图纸" }}</el-button
          >
          <div v-if="w.running" class="generation-progress" role="status">
            <el-progress :percentage="w.progress" :stroke-width="5" /><el-button
              text
              size="small"
              @click="w.stop"
              >取消生成</el-button
            >
          </div>
          <p v-else class="privacy-note">
            后台单任务计算；最大规格在手机上可能需要稍等。
          </p>
        </section>
      </aside>
      <div class="result-column">
        <section class="workshop-panel canvas-panel">
          <div class="result-heading">
            <div>
              <span class="eyebrow">YOUR PATTERN</span>
              <h2>每一格，都有灵感的位置</h2>
            </div>
            <span class="status-pill">{{
              w.project ? "图纸已生成" : "等待你的第一张图纸"
            }}</span>
          </div>
          <div v-if="w.preparing" class="preparing-state" role="status">
            <el-icon class="is-loading"><Loading /></el-icon
            >正在缩小图片并释放原图内存…
          </div>
          <template v-if="w.project"
            ><div class="result-metrics">
              <div>
                <strong
                  >{{ w.project.pattern.width }}<small> × </small
                  >{{ w.project.pattern.height }}</strong
                ><span>图纸格数</span>
              </div>
              <div>
                <strong>{{ w.totalBeads.toLocaleString() }}</strong
                ><span>实际用豆</span>
              </div>
              <div>
                <strong>{{ w.usage.length }}<small> 色</small></strong
                ><span>{{ w.resultPalette.name }} 品牌配色</span>
              </div>
              <div>
                <strong>{{
                  w.lastDuration === null
                    ? "已恢复"
                    : `${(w.lastDuration / 1000).toFixed(2)}s`
                }}</strong
                ><span>{{
                  w.lastDuration === null ? "本地图纸" : "本次后台计算"
                }}</span>
              </div>
            </div>
            <el-alert
              v-if="w.changed"
              title="参数已调整，点击生成后应用；当前导出对应下方已生成图纸。"
              type="info"
              :closable="false"
              show-icon /><PatternCanvas
              :pattern="w.project.pattern"
              :colors="w.resultPalette.colors"
          /></template>
          <div v-else class="empty-canvas">
            <div class="empty-beads" aria-hidden="true">
              <i
                v-for="i in 25"
                :key="i"
                :style="{ opacity: i % 3 === 0 ? 0.4 : 1 }"
              ></i>
            </div>
            <h3>把一张图片，变成一份手作计划</h3>
            <p>
              左侧选图后，调整品牌、规格和颜色数量。<br />图纸与用豆清单会一起出现在这里。
            </p>
            <el-button
              type="primary"
              plain
              :disabled="w.preparing"
              @click="input?.click()"
              >从选择图片开始</el-button
            >
          </div>
          <div
            v-for="warning in w.warnings"
            :key="warning"
            class="workshop-warning"
          >
            <el-icon><InfoFilled /></el-icon>{{ warning }}
          </div>
          <div class="save-state">
            <span :class="{ saved: w.saveState.startsWith('已') }">●</span
            >{{ w.saveState }}
          </div>
        </section>
        <section v-if="w.project" class="workshop-panel export-panel">
          <div class="panel-heading">
            <span class="section-number mint">03</span>
            <div>
              <h2>带着图纸，开始制作</h2>
              <p>导出包含色号的网格图纸，照清单准备材料</p>
            </div>
          </div>
          <div class="export-actions">
            <el-button
              type="primary"
              :loading="w.exporting"
              :disabled="!w.totalBeads"
              @click="w.png"
              >下载 PNG 图纸</el-button
            ><el-button
              :disabled="!w.totalBeads"
              @click="downloadCsv(w.project)"
              >下载 CSV 清单</el-button
            ><el-button @click="downloadProject(w.project)"
              >备份项目 JSON</el-button
            ><el-button text @click="w.copyList">复制清单</el-button>
          </div>
          <p class="export-note">
            JSON
            保留图纸和参数，不含原图；本地草稿还保留缩小图片，可继续调参。清除浏览器数据会删除草稿，请定期备份。
          </p>
        </section>
        <section v-if="w.project" class="workshop-panel materials-panel">
          <div class="materials-heading">
            <h2>
              你的备料清单 <span>{{ w.usage.length }} 色</span>
            </h2>
            <strong>共 {{ w.totalBeads.toLocaleString() }} 颗</strong>
          </div>
          <div v-if="w.usage.length" class="material-grid">
            <div v-for="row in w.usage" :key="row.index" class="material-item">
              <span
                class="material-swatch"
                :style="{ background: row.hex }"
              ></span>
              <div>
                <b>{{ row.code }}</b
                ><small>{{ row.hex }}</small>
              </div>
              <strong
                >{{ row.count.toLocaleString() }}<small> 颗</small></strong
              >
            </div>
          </div>
          <el-empty
            v-else
            description="没有需要放豆的格子，请检查背景设置"
            :image-size="70"
          />
        </section>
      </div>
    </div>
    <footer class="workshop-footer">
      色卡来自 MIT 开源数据 · 屏幕显示与实物可能存在色差，请以实际品牌色卡为准。
    </footer>
    <ImageCropper
      v-if="w.cropFile"
      v-model="w.cropVisible"
      :file="w.cropFile"
      @confirm="w.cropped"
    />
    <el-dialog
      v-model="w.cloudVisible"
      title="我的云端拼豆作品"
      width="860px"
      append-to-body
    >
      <p class="draft-scope">
        仅本人可见 · 工作源与图纸保存在云端，可跨设备继续创作
      </p>
      <div class="private-search">
        <el-input
          v-model="w.cloudKeyword"
          clearable
          placeholder="搜索云端作品名称"
          @keyup.enter="
            w.cloudPage = 1;
            w.refreshCloud();
          "
        />
        <el-button
          @click="
            w.cloudPage = 1;
            w.refreshCloud();
          "
          >搜索作品</el-button
        >
        <el-button @click="w.openMigration()">迁移本地作品</el-button>
      </div>
      <div v-loading="w.cloudLoading || w.cloudBusy" class="cloud-content">
        <el-alert
          v-if="w.cloudError"
          :title="w.cloudError"
          type="error"
          :closable="false"
        />
        <div v-if="w.cloudRows.length" class="draft-list">
          <article
            v-for="item in w.cloudRows"
            :key="item.id"
            class="draft-item cloud-item"
          >
            <img
              v-if="item.has_thumbnail"
              :src="w.previewUrl(item)"
              alt="云端作品缩略图"
              loading="lazy"
            />
            <div class="draft-info">
              <strong>{{ item.name }}</strong
              ><span
                >{{ item.width }} × {{ item.height }} 格 ·
                {{ getPalette(item.palette_id).name }} · v{{
                  item.revision
                }}</span
              >
              <small
                >{{ new Date(item.updated_at).toLocaleString("zh-CN") }} ·
                {{ item.has_source ? "可重新调参" : "仅图纸，无工作源" }}</small
              >
              <div>
                <el-button
                  size="small"
                  type="primary"
                  plain
                  @click="w.openCloud(item)"
                  >打开作品</el-button
                >
                <el-button size="small" @click="w.renameCloudItem(item)"
                  >重命名云端作品</el-button
                >
                <el-button
                  size="small"
                  text
                  type="danger"
                  @click="w.removeCloud(item)"
                  >删除云端作品</el-button
                >
              </div>
            </div>
          </article>
        </div>
        <el-empty
          v-else-if="!w.cloudLoading && !w.cloudError"
          description="还没有云端作品，生成后点击保存，或迁移本地草稿"
        />
        <el-button v-if="w.cloudError" @click="w.refreshCloud"
          >重试加载</el-button
        >
      </div>
      <el-pagination
        v-if="w.cloudTotal > 20"
        v-model:current-page="w.cloudPage"
        :total="w.cloudTotal"
        :page-size="20"
        layout="prev, pager, next"
        @current-change="w.refreshCloud"
      />
    </el-dialog>
    <el-dialog
      v-model="w.migrationVisible"
      title="选择本地作品同步到云端"
      width="760px"
      append-to-body
      :close-on-click-modal="!w.migrationBusy"
      :show-close="!w.migrationBusy"
      :close-on-press-escape="!w.migrationBusy"
    >
      <p class="draft-scope">
        勾选后才上传。同步成功保留本地副本；已关联当前账号的作品将按版本更新，其他账号缓存不会显示。
        所选作品全部同步成功后，将自动打开云端作品列表。
      </p>
      <el-checkbox-group
        v-model="w.selectedMigrations"
        class="migration-list"
        :disabled="w.migrationBusy"
      >
        <div
          v-for="draft in w.migrationRows"
          :key="draft.id"
          class="migration-row"
        >
          <el-checkbox :value="draft.id"
            >{{ draft.project.name }} ·
            {{
              draft.owner === "guest" ? "游客草稿" : "当前账号草稿"
            }}</el-checkbox
          >
          <small :data-migration="draft.id">{{
            w.migrationStatuses[draft.id]
          }}</small>
          <el-button
            v-if="w.migrationIssues[draft.id]"
            size="small"
            type="primary"
            plain
            :disabled="w.migrationBusy"
            @click.stop="w.migrateAsNew(draft)"
            >作为新作品同步</el-button
          >
        </div>
      </el-checkbox-group>
      <el-empty
        v-if="!w.migrationRows.length"
        description="没有可同步的本地作品"
      />
      <el-progress
        v-if="w.migrationTotal"
        :percentage="
          Math.round((w.migrationCompleted / w.migrationTotal) * 100)
        "
      />
      <p class="migration-feedback" role="status" aria-live="polite">
        {{
          w.migrationSummary ||
          (w.selectedMigrations.length
            ? `已选择 ${w.selectedMigrations.length} 份作品，点击下方按钮开始同步。`
            : "请先勾选需要同步的作品。")
        }}
        <span v-if="w.migrationBusy"
          >（{{ w.migrationCompleted }}/{{ w.migrationTotal }}）</span
        >
      </p>
      <template #footer
        ><el-button
          :disabled="w.migrationBusy"
          @click="w.migrationVisible = false"
          >暂不同步</el-button
        >
        <el-button
          type="primary"
          :loading="w.migrationBusy"
          :disabled="!w.selectedMigrations.length"
          @click="w.migrate"
          >同步所选作品</el-button
        ></template
      >
    </el-dialog>
    <el-dialog
      v-model="w.privateVisible"
      title="从我的私有空间导入"
      width="860px"
      append-to-body
      ><div class="private-search">
        <el-input
          v-model="w.keyword"
          placeholder="搜索图片名称或标签"
          clearable
          @keyup.enter="
            w.page = 1;
            w.privateList();
          "
        /><el-button
          @click="
            w.page = 1;
            w.privateList();
          "
          >搜索</el-button
        >
      </div>
      <div v-loading="w.privateLoading" class="private-content">
        <el-empty
          v-if="w.noSpace"
          description="你还没有私有空间；也可以直接使用本地图片。"
          ><el-button
            @click="
              w.privateVisible = false;
              router.push('/spaces/create');
            "
            >创建私有空间</el-button
          ></el-empty
        ><el-result
          v-else-if="w.privateError"
          icon="warning"
          :sub-title="w.privateError"
          ><template #extra
            ><el-button @click="w.privateList">重新加载</el-button></template
          ></el-result
        >
        <div v-else-if="w.privateItems.length" class="private-grid">
          <button
            v-for="item in w.privateItems"
            :key="item.id"
            :disabled="w.privateLoading"
            @click="w.importPrivate(item)"
          >
            <img :src="item.url" :alt="item.name" loading="lazy" /><strong>{{
              item.name
            }}</strong
            ><span>{{ item.pic_width }} × {{ item.pic_height }}</span>
          </button>
        </div>
        <el-empty
          v-else-if="!w.privateLoading"
          description="暂时没有可导入的图片"
        />
      </div>
      <el-pagination
        v-if="w.total > 12 && !w.noSpace"
        v-model:current-page="w.page"
        :page-size="12"
        :total="w.total"
        layout="prev, pager, next"
        @current-change="w.privateList"
      />
      <p class="privacy-note">
        仅导入当前账号的原图副本，不修改原图、审核状态或空间配额。
      </p></el-dialog
    >
    <el-dialog
      v-model="w.draftsVisible"
      title="当前浏览器的本地草稿"
      width="780px"
      append-to-body
      ><p class="draft-scope">
        {{
          w.auth.user
            ? "仅展示当前登录账号的草稿"
            : "当前为游客草稿，登录后的草稿独立保存"
        }}
        · 共 {{ w.drafts.length }} 份
        <el-button
          v-if="w.signedIn"
          text
          type="primary"
          @click="w.openMigration()"
          >选择本地作品迁移</el-button
        >
      </p>
      <div v-if="w.drafts.length" class="draft-list">
        <article v-for="draft in w.drafts" :key="draft.id" class="draft-item">
          <img v-if="draft.thumbnail" :src="draft.thumbnail" alt="草稿缩略图" />
          <div class="draft-info">
            <strong>{{ draft.project.name }}</strong
            ><span
              >{{ draft.project.pattern.width }} ×
              {{ draft.project.pattern.height }} 格 ·
              {{ getPalette(draft.project.paletteId).name }}</span
            ><small>{{
              new Date(draft.project.updatedAt).toLocaleString("zh-CN")
            }}</small>
            <div>
              <el-button
                size="small"
                type="primary"
                plain
                @click="w.restore(draft)"
                >继续创作</el-button
              ><el-button size="small" @click="w.renameDraft(draft)"
                >重命名</el-button
              ><el-button
                size="small"
                text
                type="danger"
                @click="w.removeDraft(draft)"
                >删除</el-button
              >
            </div>
          </div>
        </article>
      </div>
      <el-empty
        v-else
        description="生成图纸后会自动保存在这里"
        :image-size="90"
    /></el-dialog>
  </main>
</template>

<style scoped>
.persistence-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  margin: 0 0 24px;
  border: 1px solid #e7e2f2;
  border-radius: 22px;
  background: linear-gradient(110deg, #fff, #f4f0ff);
}
.persistence-strip strong {
  color: #62517d;
  font-size: 15px;
}
.persistence-strip p {
  margin: 7px 0 0;
  color: #858294;
  font-size: 12px;
  line-height: 1.7;
}
.persistence-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.persistence-controls .el-button {
  margin-left: 0;
}
.cloud-error {
  flex-basis: 100%;
  font-size: 13px;
  color: #b45e6d;
  line-height: 1.8;
}
.cloud-content {
  min-height: 160px;
  padding: 14px 0;
}
.migration-list {
  display: grid;
  gap: 10px;
}
.migration-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: 14px;
  background: #f7f5fb;
  min-width: 0;
}
.migration-row :deep(.el-checkbox) {
  white-space: normal;
  height: auto;
  min-height: 32px;
}
.migration-row :deep(.el-checkbox__label) {
  white-space: normal;
  overflow-wrap: anywhere;
}
.migration-row small {
  font-size: 12px;
  color: #8d7c9c;
  padding-left: 24px;
  line-height: 1.7;
}
.migration-feedback {
  margin: 14px 0 0;
  color: #756482;
  font-size: 13px;
  line-height: 1.8;
  overflow-wrap: anywhere;
}
@media (max-width: 600px) {
  .persistence-strip {
    padding: 16px;
  }
  .persistence-controls {
    width: 100%;
  }
  .persistence-controls .el-switch {
    width: 100%;
  }
  .cloud-item .draft-info > div {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .cloud-item .el-button {
    margin-left: 0;
  }
}
.bead-workshop {
  max-width: 1600px;
  margin: auto;
  padding: 30px var(--app-page-x) 24px;
}
.file-input {
  display: none;
}
.workshop-hero {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  overflow: hidden;
  border: 1px solid white;
  border-radius: 30px;
  padding: 38px 46px;
  background:
    radial-gradient(ellipse at 85% 10%, #ffe0ec, transparent 50%),
    linear-gradient(115deg, #e8f7fd, #f8f5ff 54%, #fff6f8);
  box-shadow: 0 16px 50px #4a52700a;
}
.eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #ad6687;
}
.hero-copy h1 {
  font-size: clamp(26px, 3vw, 42px);
  line-height: 1.45;
  letter-spacing: -1px;
  margin: 12px 0;
  font-weight: 900;
}
.hero-copy em {
  font-style: normal;
  color: #d56591;
}
.hero-copy p {
  color: #7c8291;
  font-size: 14px;
  line-height: 1.8;
}
.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 20px;
}
.hero-tags span {
  background: #ffffffb0;
  border: 1px solid white;
  padding: 6px 11px;
  border-radius: 99px;
  font-size: 11px;
  color: #7e6b83;
}
.hero-beads {
  position: relative;
  padding: 10px 54px 14px 28px;
}
.mini-board {
  display: grid;
  grid-template-columns: repeat(7, 20px);
  gap: 6px;
  padding: 20px;
  background: #ffffffa8;
  border: 1px solid white;
  border-radius: 22px;
  transform: rotate(-8deg);
  box-shadow: 16px 18px 32px #7c6b9515;
  animation: board-float 6s ease-in-out infinite;
}
.mini-board i {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #cbbbe9;
  box-shadow:
    inset 2px 2px 3px #ffffffa0,
    inset -2px -2px 3px #38304519;
}
.mini-board .mint {
  background: #a9ded3;
}
.mini-board .rose {
  background: #e991b4;
}
.mini-board .light {
  background: #fff2d1;
}
.floating-label {
  position: absolute;
  right: 18px;
  bottom: 5px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 9px 25px #9d6a9117;
  padding: 10px 15px;
  font-size: 11px;
  font-weight: 700;
  color: #a16e91;
}
.workshop-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin: 25px 0;
}
.steps {
  display: flex;
  align-items: center;
  gap: 14px;
  color: #b2b6c3;
  font-size: 11px;
}
.steps b {
  font-weight: 600;
  color: #7c8292;
}
.count-badge {
  background: #f4edf9;
  padding: 1px 7px;
  border-radius: 10px;
  margin-left: 6px;
  color: #8c6dac;
}
.workshop-grid {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}
.control-column,
.result-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}
.workshop-panel {
  background: #ffffffed;
  border: 1px solid #e8e8f1;
  border-radius: 22px;
  padding: 24px;
  box-shadow: 0 9px 30px #3d456207;
}
.panel-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.section-number {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: #ffedf3;
  color: #d16b92;
  font-size: 13px;
  font-weight: 800;
}
.section-number.lavender {
  background: #f0ebfb;
  color: #9c86c9;
}
.section-number.mint {
  background: #e7f6f0;
  color: #5d9a87;
}
.workshop-panel h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
}
.panel-heading p {
  font-size: 10px;
  color: #9a9eab;
  margin: 5px 0 0;
}
.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 180px;
  border: 1.5px dashed #ddcfe7;
  border-radius: 16px;
  background: linear-gradient(135deg, #fcf6fa, #f5f8fd);
  cursor: pointer;
  gap: 10px;
  color: #8a7793;
}
.upload-zone:hover {
  border-color: #d676a2;
  background: #fff4f9;
}
.upload-symbol {
  width: 42px;
  height: 42px;
  background: #fff;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 25px;
  box-shadow: 0 5px 15px #7b648b0c;
}
.upload-zone strong {
  font-size: 13px;
}
.upload-zone small {
  font-size: 10px;
  line-height: 1.8;
  color: #a3a0ad;
}
.source-preview {
  position: relative;
  height: 172px;
  border-radius: 15px;
  overflow: hidden;
  background: #f4f5f9;
  display: grid;
  place-items: center;
}
.source-preview img {
  max-width: 100%;
  max-height: 172px;
  object-fit: contain;
}
.source-preview .el-button {
  position: absolute;
  bottom: 8px;
  right: 8px;
}
.source-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 14px;
}
.source-buttons .el-button {
  margin: 0;
  padding: 8px 7px;
  font-size: 11px;
}
.privacy-note {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  line-height: 1.7;
  color: #9a9fac;
  margin: 12px 0 0;
}
.bead-form :deep(.el-form-item__label) {
  font-size: 12px;
  color: #747d8d;
  display: flex;
  justify-content: space-between;
  width: 100%;
  padding: 0;
}
.bead-form :deep(.el-form-item) {
  margin-bottom: 20px;
}
.bead-form :deep(.el-select),
.bead-form :deep(.el-input-number) {
  width: 100%;
}
.bead-form small {
  font-size: 10px;
  color: #a0a6b2;
  line-height: 1.8;
}
.parameter-value {
  color: #c979a0;
  font-size: 11px;
}
.range-help {
  display: flex;
  justify-content: space-between;
  width: 100%;
  font-size: 9px;
  color: #a2a8b3;
  line-height: 1;
}
.color-presets {
  display: flex;
  gap: 6px;
  width: 100%;
  margin-top: 10px;
}
.color-presets button {
  flex: 1;
  border: 1px solid #ece8f0;
  background: #faf9fc;
  padding: 6px 0;
  border-radius: 8px;
  font-size: 10px;
  color: #9791a3;
  cursor: pointer;
}
.color-presets .active {
  border-color: #edb3ce;
  color: #c56c99;
  background: #fff0f7;
}
.cleanup-options {
  border-top: 1px solid #f0edf4;
  border-bottom: 0;
}
.cleanup-options :deep(.el-collapse-item__header) {
  font-size: 12px;
  color: #6c7281;
}
.cleanup-options :deep(.el-collapse-item__wrap) {
  border-bottom: 0;
}
.switch-row,
.background-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}
.denoise-label {
  font-size: 11px;
  margin: 16px 0 8px;
  color: #7d8490;
}
.generate-button {
  width: 100%;
  margin-top: 16px;
  border: 0;
  box-shadow: 0 8px 18px #ec72962e;
}
.generation-progress {
  margin-top: 14px;
}
.result-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.result-heading h2 {
  font-size: 19px;
  line-height: 1.6;
  margin-top: 8px;
}
.status-pill {
  white-space: nowrap;
  font-size: 10px;
  background: #f4f0fa;
  color: #9780b9;
  padding: 7px 10px;
  border-radius: 20px;
}
.result-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid #f0edf4;
  border-radius: 15px;
  background: linear-gradient(110deg, #fff8fc, #f8faff);
  margin-bottom: 18px;
  padding: 17px 0;
}
.result-metrics div {
  padding: 0 16px;
  border-right: 1px solid #eeeaf3;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.result-metrics div:last-child {
  border: 0;
}
.result-metrics strong {
  font-size: 22px;
  font-variant-numeric: tabular-nums;
  color: #535065;
}
.result-metrics strong small {
  font-size: 11px;
}
.result-metrics span {
  font-size: 10px;
  color: #a19aa9;
}
.canvas-panel :deep(.el-alert) {
  margin-bottom: 16px;
}
.empty-canvas {
  min-height: 450px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  border-radius: 18px;
  background:
    radial-gradient(ellipse at 50% 42%, #f4edf9, transparent 58%), #fafbfe;
  border: 1px solid #f0edf6;
  padding: 36px 16px;
}
.empty-beads {
  display: grid;
  grid-template-columns: repeat(5, 17px);
  gap: 5px;
  transform: rotate(-10deg);
  padding: 20px;
  border-radius: 20px;
  background: #fff;
  box-shadow: 10px 14px 35px #806f9d15;
  margin-bottom: 16px;
}
.empty-beads i {
  height: 17px;
  border-radius: 5px;
  background: #dcbeda;
}
.empty-beads i:nth-child(3n) {
  background: #bae2d8;
}
.empty-beads i:nth-child(5n) {
  background: #f3d8bd;
}
.empty-canvas h3 {
  font-size: 17px;
  color: #77718b;
  margin: 20px 0 10px;
}
.empty-canvas p {
  font-size: 12px;
  color: #a0a0b3;
  line-height: 1.9;
  margin: 0 0 22px;
}
.save-state {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: #a4a7b3;
  margin-top: 17px;
  line-height: 1.8;
}
.save-state span {
  color: #c5bcd7;
}
.save-state .saved {
  color: #8abfaa;
}
.workshop-warning {
  display: flex;
  gap: 8px;
  align-items: center;
  background: #fff9ed;
  color: #b58a45;
  border-radius: 10px;
  padding: 10px 12px;
  margin-top: 12px;
  font-size: 11px;
  line-height: 1.7;
}
.preparing-state {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #a47e9c;
  font-size: 12px;
  margin-bottom: 16px;
}
.export-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}
.export-actions .el-button {
  margin: 0;
}
.export-note {
  font-size: 10px;
  line-height: 1.8;
  color: #a3a7b1;
  margin: 17px 0 0;
}
.materials-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}
.materials-heading h2 span {
  font-size: 10px;
  font-weight: 500;
  margin-left: 8px;
  color: #a08bac;
}
.materials-heading > strong {
  font-size: 12px;
  color: #a57e9a;
}
.material-grid {
  display: grid;
  /* 色号卡片保持紧凑宽度，按可用空间换行，不再拉伸占满整行。 */
  grid-template-columns: repeat(auto-fill, minmax(0, 190px));
  gap: 10px;
  max-height: 520px;
  overflow: auto;
}
.material-item {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #eeecf3;
  padding: 11px;
  border-radius: 12px;
  min-width: 0;
}
.material-swatch {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  box-shadow: inset 0 0 0 1px #00000010;
  flex-shrink: 0;
}
.material-item > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.material-item b {
  font-size: 12px;
  color: #606071;
}
.material-item small {
  font-size: 9px;
  color: #a9a5b4;
}
.material-item > strong {
  margin-left: auto;
  font-size: 12px;
  color: #80738e;
  white-space: nowrap;
}
.workshop-footer {
  font-size: 10px;
  text-align: center;
  color: #aba8b5;
  margin: 30px 0 12px;
  line-height: 1.8;
}
.private-search {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}
.private-content {
  min-height: 280px;
}
.private-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.private-grid button {
  background: #fff;
  border: 1px solid #e9e6ef;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  padding: 0 0 12px;
  text-align: left;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.private-grid button:hover {
  border-color: #e593b4;
}
.private-grid img {
  width: 100%;
  height: 125px;
  object-fit: cover;
}
.private-grid strong {
  margin: 10px 10px 6px;
  font-size: 12px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  max-width: calc(100% - 20px);
}
.private-grid span {
  font-size: 10px;
  color: #999;
  margin-left: 10px;
}
.draft-scope {
  font-size: 12px;
  color: #9296a4;
  margin-top: 0;
}
.draft-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 65vh;
  overflow: auto;
}
.draft-item {
  display: flex;
  gap: 18px;
  padding: 15px;
  border: 1px solid #ece8f0;
  border-radius: 14px;
}
.draft-item > img {
  width: 90px;
  height: 90px;
  object-fit: contain;
  border-radius: 10px;
  background: #f7f7fb;
  image-rendering: pixelated;
}
.draft-info {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}
.draft-info > strong {
  font-size: 14px;
  overflow-wrap: anywhere;
}
.draft-info > span,
.draft-info > small {
  font-size: 11px;
  color: #9693a3;
}
.draft-info > div {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.draft-info .el-button {
  margin: 0;
}
@keyframes board-float {
  50% {
    transform: rotate(-5deg) translateY(-6px);
  }
}
@media (max-width: 1100px) {
  .bead-workshop {
    padding: 22px;
  }
  .workshop-hero {
    padding: 30px;
  }
  .hero-beads {
    padding-right: 20px;
  }
  .workshop-grid {
    grid-template-columns: 270px minmax(0, 1fr);
    gap: 16px;
  }
  .workshop-panel {
    padding: 20px;
  }
  .result-metrics strong {
    font-size: 18px;
  }
  .result-metrics div {
    padding: 0 10px;
  }
  .status-pill {
    display: none;
  }
}
@media (max-width: 820px) {
  .workshop-grid {
    grid-template-columns: 1fr;
  }
  .control-column {
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: start;
    gap: 16px;
  }
  .hero-beads {
    transform: scale(0.8);
    transform-origin: right center;
    padding-left: 0;
  }
  .hero-copy h1 {
    font-size: 28px;
  }
  .hero-copy p {
    font-size: 12px;
  }
  .workshop-panel h2 {
    font-size: 15px;
  }
}
@media (max-width: 600px) {
  .bead-workshop {
    padding: 18px 12px;
  }
  .workshop-hero {
    padding: 26px 22px;
    border-radius: 23px;
  }
  .hero-beads {
    display: none;
  }
  .hero-copy h1 {
    font-size: 29px;
  }
  .hero-copy p {
    font-size: 12px;
  }
  .hero-tags {
    gap: 5px;
  }
  .hero-tags span {
    padding: 5px 8px;
    font-size: 9px;
  }
  .workshop-actions {
    margin: 18px 0;
    gap: 14px;
  }
  .workshop-actions > div:last-child {
    display: flex;
    gap: 8px;
    width: 100%;
  }
  .workshop-actions .el-button {
    margin: 0;
    flex: 1;
  }
  .steps {
    width: 100%;
    justify-content: center;
    font-size: 10px;
  }
  .control-column {
    display: flex;
    gap: 16px;
  }
  .workshop-panel {
    padding: 20px 16px;
    border-radius: 20px;
  }
  .source-panel .upload-zone {
    min-height: 150px;
  }
  .source-buttons .el-button {
    font-size: 12px;
    min-height: 42px;
  }
  .result-heading {
    margin-bottom: 18px;
  }
  .result-heading h2 {
    font-size: 16px;
  }
  .result-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    row-gap: 18px;
  }
  .result-metrics div:nth-child(2) {
    border: 0;
  }
  .result-metrics strong {
    font-size: 21px;
  }
  .result-metrics div {
    padding-left: 16px;
  }
  .empty-canvas {
    min-height: 350px;
  }
  .empty-canvas h3 {
    font-size: 15px;
  }
  .export-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .export-actions .el-button {
    padding: 8px 6px;
    font-size: 11px;
    min-height: 42px;
  }
  .material-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 7px;
  }
  .material-item {
    gap: 7px;
    padding: 9px 7px;
  }
  .material-swatch {
    width: 24px;
    height: 24px;
    border-radius: 7px;
  }
  .material-item strong {
    font-size: 11px;
  }
  .material-item small {
    font-size: 8px;
  }
  .private-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .private-grid img {
    height: 130px;
  }
  .draft-item {
    gap: 10px;
    padding: 10px;
  }
  .draft-item > img {
    width: 65px;
    height: 65px;
  }
  .draft-info .el-button {
    font-size: 11px;
    padding: 7px;
  }
  .workshop-footer {
    padding: 0 12px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .mini-board {
    animation: none;
  }
}
</style>
