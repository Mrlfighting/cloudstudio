<script setup lang="ts">
/**
 * 团队空间主页：图片 / 成员 / 设置 三个 tab
 * - 进入时加载团队上下文（成员 + 我的角色），非成员显示无访问权限
 * - 按钮级权限由 team store 的 getter 控制
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'
import { useTeamStore } from '@/stores/team'
import { SPACE_LEVEL_OPTIONS, formatBytes, spaceLevelLabel } from '@/types/space'
import { SPACE_ROLE_OPTIONS, spaceRoleLabel, type SpaceMemberRead, type SpaceRole } from '@/types/teamSpace'
import { PICTURE_CATEGORIES, type PictureListItemRead, type PictureSort } from '@/types/picture'
import PictureCard from '@/components/PictureCard.vue'
import PictureUploadDialog from '@/components/PictureUploadDialog.vue'
import TeamMemberInviteDialog from './TeamMemberInviteDialog.vue'

const route = useRoute()
const router = useRouter()
const team = useTeamStore()

const spaceId = computed(() => Number(route.params.id))
const activeTab = ref('pictures')

// ---- 图片 tab ----
const picLoading = ref(false)
const rows = ref<PictureListItemRead[]>([])
const uploadVisible = ref(false)
const picFilters = reactive({ keyword: '', category: '', sort: 'time' as PictureSort })
const picPagination = reactive({ page: 1, itemsPerPage: 20, total: 0 })

async function loadPictures() {
  picLoading.value = true
  try {
    const res = await teamSpaceApi.listPictures(spaceId.value, {
      page: picPagination.page,
      items_per_page: picPagination.itemsPerPage,
      category: picFilters.category || undefined,
      keyword: picFilters.keyword || undefined,
      sort: picFilters.sort,
    })
    rows.value = res.data
    picPagination.total = res.total_count
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取团队图片失败'))
  } finally {
    picLoading.value = false
  }
}

function resetPictures() {
  picPagination.page = 1
  loadPictures()
}

// ---- 成员 tab ----
const inviteVisible = ref(false)

function roleTagType(role: string): 'warning' | 'success' | 'info' {
  if (role === 'admin') return 'warning'
  if (role === 'editor') return 'success'
  return 'info'
}

async function onRemoveMember(m: SpaceMemberRead) {
  try {
    await ElMessageBox.confirm(`确认将「${m.name || m.username}」移出团队？`, '移除成员', {
      type: 'warning',
      confirmButtonText: '移除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await teamSpaceApi.removeMember(spaceId.value, m.user_id)
    ElMessage.success('成员已移除')
    await team.load(spaceId.value)
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '移除成员失败'))
  }
}

async function onRoleChange(m: SpaceMemberRead, role: SpaceRole) {
  try {
    await teamSpaceApi.updateMemberRole(spaceId.value, m.user_id, { space_role: role })
    ElMessage.success('角色已更新')
    m.space_role = role
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '设置角色失败'))
    await team.load(spaceId.value)
  }
}

// ---- 设置 tab ----
const settingsName = ref('')
const settingsLevel = ref<number>(0)
const settingsSaving = ref(false)

function syncSettingsFromTeam() {
  if (team.team) {
    settingsName.value = team.team.name
    settingsLevel.value = team.team.space_level
  }
}

async function saveSettings() {
  if (!settingsName.value.trim()) {
    ElMessage.warning('请输入团队名称')
    return
  }
  settingsSaving.value = true
  try {
    await teamSpaceApi.updateSettings(spaceId.value, {
      name: settingsName.value.trim(),
      space_level: settingsLevel.value,
    })
    ElMessage.success('团队设置已保存')
    await team.load(spaceId.value)
    syncSettingsFromTeam()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '保存设置失败'))
  } finally {
    settingsSaving.value = false
  }
}

onMounted(async () => {
  await team.load(spaceId.value)
  syncSettingsFromTeam()
  loadPictures()
})
</script>

<template>
  <div class="page-container">
    <!-- 非成员无访问 -->
    <el-result v-if="!team.loading && !team.isMember" icon="warning" title="无访问权限" sub-title="你不是该团队成员">
      <template #extra>
        <el-button type="primary" @click="router.push('/spaces/team')">返回团队列表</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="header">
        <div>
          <div class="eyebrow">TEAM WORKSPACE · 团队工作台</div><h2 class="page-title">{{ team.team?.name ?? '团队空间' }}</h2>
          <div v-if="team.myRole" class="role-line">
            <el-tag size="small" :type="roleTagType(team.myRole)">我的角色：{{ spaceRoleLabel(team.myRole) }}</el-tag>
          </div>
        </div>
        <el-button @click="router.push('/spaces/team')">返回团队列表</el-button>
      </div>

      <el-tabs v-model="activeTab">
        <!-- 图片 -->
        <el-tab-pane label="图片" name="pictures">
          <div class="tab-toolbar">
            <div class="filters">
              <el-input
                v-model="picFilters.keyword"
                placeholder="搜索名称/简介/标签"
                clearable
                class="search"
                @keyup.enter="resetPictures"
                @clear="resetPictures"
              >
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <el-select v-model="picFilters.category" placeholder="全部分类" clearable class="category" @change="resetPictures">
                <el-option v-for="c in PICTURE_CATEGORIES" :key="c" :label="c" :value="c" />
              </el-select>
              <el-radio-group v-model="picFilters.sort" @change="resetPictures">
                <el-radio-button value="time">最新</el-radio-button>
                <el-radio-button value="popularity">最热</el-radio-button>
              </el-radio-group>
            </div>
            <el-button v-if="team.canWrite" type="primary" :icon="'Upload'" @click="uploadVisible = true">上传图片</el-button>
          </div>

          <div v-loading="picLoading" class="grid">
            <PictureCard
              v-for="item in rows"
              :key="item.id"
              :item="item"
              kind="team"
              :space-id="spaceId"
            />
          </div>
          <el-empty v-if="!picLoading && rows.length === 0" description="暂无图片" />

          <div v-if="picPagination.total > 0" class="pagination-wrap">
            <el-pagination
              v-model:current-page="picPagination.page"
              v-model:page-size="picPagination.itemsPerPage"
              :total="picPagination.total"
              :page-sizes="[20, 40, 60]"
              layout="total, sizes, prev, pager, next"
              background
              @current-change="loadPictures"
              @size-change="resetPictures"
            />
          </div>
        </el-tab-pane>

        <!-- 成员 -->
        <el-tab-pane label="成员" name="members">
          <div class="tab-toolbar">
            <span class="muted">共 {{ team.members.length }} 名成员</span>
            <el-button v-if="team.canManageMembers" type="primary" :icon="'Plus'" @click="inviteVisible = true">
              邀请成员
            </el-button>
          </div>

          <el-table :data="team.members" stripe>
            <el-table-column label="用户" min-width="160">
              <template #default="{ row }">
                <div class="member-cell">
                  <span class="member-name">{{ row.name }}</span>
                  <span class="muted">@{{ row.username }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="角色" width="160">
              <template #default="{ row }">
                <el-select
                  v-if="team.canManageMembers"
                  :model-value="row.space_role"
                  size="small"
                  @change="(v: SpaceRole) => onRoleChange(row, v)"
                >
                  <el-option v-for="o in SPACE_ROLE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
                <el-tag v-else size="small" :type="roleTagType(row.space_role)">{{ spaceRoleLabel(row.space_role) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="加入时间" width="180">
              <template #default="{ row }">
                <span class="muted">{{ row.created_at ?? '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column v-if="team.canManageMembers" label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="danger" @click="onRemoveMember(row)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 设置 -->
        <el-tab-pane label="设置" name="settings">
          <el-empty v-if="!team.canManageSettings" description="仅管理员可修改团队设置" />
          <el-card v-else class="settings-card" shadow="never">
            <el-form label-position="top">
              <el-form-item label="团队名称">
                <el-input v-model="settingsName" maxlength="128" show-word-limit />
              </el-form-item>
              <el-form-item label="空间级别">
                <el-select v-model="settingsLevel" style="width: 220px">
                  <el-option v-for="o in SPACE_LEVEL_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
              </el-form-item>
              <div v-if="team.team" class="quota-line muted">
                {{ spaceLevelLabel(team.team.space_level) }} · 已用 {{ formatBytes(team.team.total_size) }}
                / {{ formatBytes(team.team.max_size) }} · {{ team.team.total_count }}/{{ team.team.max_count }} 张
              </div>
            </el-form>
            <div class="settings-actions">
              <el-button type="primary" :loading="settingsSaving" @click="saveSettings">保存</el-button>
            </div>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </template>

    <PictureUploadDialog v-model="uploadVisible" kind="team" :space-id="spaceId" @success="loadPictures" />
    <TeamMemberInviteDialog v-model="inviteVisible" :space-id="spaceId" @success="() => team.load(spaceId)" />
  </div>
</template>

<style scoped>
.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.role-line {
  margin-top: 6px;
}

.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search {
  width: 260px;
}

.category {
  width: 150px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
  min-height: 120px;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.member-cell {
  display: flex;
  flex-direction: column;
}

.member-name {
  font-weight: 500;
  color: #303133;
}

.muted {
  color: #909399;
  font-size: 13px;
}

.settings-card {
  max-width: 520px;
  border-radius: 10px;
}

.quota-line {
  margin-top: 4px;
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
