/**
 * 团队空间状态（Pinia）：缓存「当前团队上下文 + 我的角色」。
 *
 * 角色来源：无「我在某空间角色」专用接口，通过 GET /spaces/{id}/members 列表
 * 找到当前用户项取 space_role（成员才能读该接口，非成员 403 即「无访问」）。
 * 进入团队空间时 load(spaceId)，切换空间重载，跨页面共享。
 */
import { defineStore } from 'pinia'
import { teamSpaceApi } from '@/api/teamSpace'
import { useAuthStore } from '@/stores/auth'
import type { SpaceMemberRead, SpaceRole, TeamSpaceListItemRead } from '@/types/teamSpace'

export const useTeamStore = defineStore('team', {
  state: () => ({
    spaceId: null as number | null,
    myRole: null as SpaceRole | null,
    team: null as TeamSpaceListItemRead | null,
    members: [] as SpaceMemberRead[],
    loading: false,
  }),

  getters: {
    isMember: (state): boolean => state.myRole !== null,
    isAdmin: (state): boolean => state.myRole === 'admin',
    isEditor: (state): boolean => state.myRole === 'editor',
    isViewer: (state): boolean => state.myRole === 'viewer',
    /** 可上传/编辑图片（admin / editor） */
    canWrite: (state): boolean => state.myRole === 'admin' || state.myRole === 'editor',
    /** 可删除图片（admin / editor） */
    canDelete: (state): boolean => state.myRole === 'admin' || state.myRole === 'editor',
    /** 可管理成员（仅 admin） */
    canManageMembers: (state): boolean => state.myRole === 'admin',
    /** 可管理团队设置（仅 admin） */
    canManageSettings: (state): boolean => state.myRole === 'admin',
  },

  actions: {
    /** 进入团队空间时加载上下文：团队信息 + 成员列表 + 我的角色 */
    async load(spaceId: number): Promise<void> {
      this.spaceId = spaceId
      this.loading = true
      this.myRole = null
      this.team = null
      this.members = []
      const auth = useAuthStore()

      // 团队信息（名称/级别/配额）来自「我加入的团队列表」；接口未就绪时降级为空
      try {
        const teams = await teamSpaceApi.listMyTeams()
        this.team = teams.find((t) => t.id === spaceId) ?? null
        if (this.team) this.myRole = this.team.space_role
      } catch {
        this.team = null
      }

      // 成员列表（含我的角色，权威来源）；非成员 403 则视为无访问
      try {
        this.members = await teamSpaceApi.listMembers(spaceId)
        const me = this.members.find((m) => m.user_id === auth.user?.id)
        this.myRole = me ? me.space_role : null
      } catch {
        this.members = []
        this.myRole = null
      } finally {
        this.loading = false
      }
    },

    reset(): void {
      this.spaceId = null
      this.myRole = null
      this.team = null
      this.members = []
      this.loading = false
    },
  },
})
