<template>
  <section class="workspace">
    <PageState :state="settings.pageState" :message="settings.error || '系统设置保存失败'">
      <div class="hero-grid settings-grid">
        <Panel title="报告模型" note="默认参数">
          <div class="status-note">报告生成页会继承这里的默认值，并在创建任务前允许单次调整。</div>
          <div class="form-row">
            <label>模型网关</label>
            <select v-model="settings.reportGatewayId">
              <option value="">使用环境默认</option>
              <option v-for="gateway in settings.modelGateways" :key="gateway.id" :value="gateway.id">
                {{ gateway.name }} · {{ gateway.id }}
              </option>
            </select>
          </div>
          <div class="form-row">
            <label>报告模型</label>
            <input v-model="settings.reportModelId" placeholder="例如 qwen36-35b" />
          </div>
          <div class="grid-2">
            <div class="form-row">
              <label>温度</label>
              <input v-model.number="settings.reportTemperature" type="number" min="0" max="2" step="0.1" />
            </div>
            <div class="form-row">
              <label>最大 Token</label>
              <input v-model.number="settings.reportMaxTokens" type="number" min="512" max="65536" step="512" />
            </div>
          </div>
        </Panel>

        <Panel title="当前写作 Skill" note="任务默认值">
          <div v-if="currentSkill" class="current-skill">
            <div>
              <span>{{ currentSkill.source === 'builtin' ? '系统内置' : '用户导入' }} · v{{ currentSkill.version }}</span>
              <strong>{{ currentSkill.label }}</strong>
              <p>{{ currentSkill.description || currentSkill.id }}</p>
            </div>
            <Chip :label="currentSkill.id" :variant="currentSkill.source === 'builtin' ? 'ok' : undefined" />
          </div>
          <div class="form-row">
            <label>默认写作风格</label>
            <select v-model="settings.reportSkillId">
              <optgroup label="系统内置">
                <option v-for="skill in builtinSkills" :key="skill.id" :value="skill.id">{{ skill.label }}</option>
              </optgroup>
              <optgroup v-if="userSkills.length" label="用户导入">
                <option v-for="skill in userSkills" :key="skill.id" :value="skill.id">{{ skill.label }}</option>
              </optgroup>
            </select>
          </div>
          <div class="path-row">
            <span>当前文件夹</span>
            <code>{{ currentSkill?.directory || '未解析' }}</code>
            <button class="ghost compact" type="button" :disabled="!currentSkill?.directory" @click="copyPath(currentSkill?.directory || '')">复制</button>
          </div>
        </Panel>
      </div>

      <Panel title="写作 Skill 管理" note="仅支持 Markdown">
        <div class="skill-toolbar">
          <div>
            <strong>用户导入目录</strong>
            <code>{{ settings.reportSkillLocations.user || '读取中...' }}</code>
          </div>
          <div class="actions skill-actions">
            <input ref="skillFileInput" class="sr-only" type="file" accept=".md,text/markdown" @change="onSkillFile" />
            <button class="primary" type="button" :disabled="settings.skillBusy" @click="skillFileInput?.click()">
              {{ settings.skillBusy ? '处理中...' : '导入 Skill' }}
            </button>
            <button class="ghost" type="button" :disabled="settings.skillBusy" @click="settings.refreshReportSkills">刷新</button>
          </div>
        </div>
        <p v-if="settings.skillError" class="bad-text">{{ settings.skillError }}</p>
        <div class="skill-table" role="list">
          <div
            v-for="skill in settings.reportSkills"
            :key="skill.id"
            role="button"
            tabindex="0"
            :class="['skill-row', { active: settings.reportSkillId === skill.id }]"
            @click="settings.reportSkillId = skill.id"
            @keydown.enter="settings.reportSkillId = skill.id"
          >
            <span class="skill-source">{{ skill.source === 'builtin' ? '内置' : '用户' }}</span>
            <span class="skill-name">
              <strong>{{ skill.label }}</strong>
              <small>{{ skill.description || skill.id }}</small>
            </span>
            <code>v{{ skill.version }}</code>
            <span class="skill-row-actions">
              <span>{{ settings.reportSkillId === skill.id ? '当前默认' : '选择' }}</span>
              <button
                v-if="skill.deletable"
                class="danger-link"
                type="button"
                :aria-label="pendingDeleteId === skill.id ? '确认删除用户 Skill' : '删除用户 Skill'"
                @click.stop="requestDelete(skill.id)"
              >
                {{ pendingDeleteId === skill.id ? '确认删除' : '删除' }}
              </button>
            </span>
          </div>
        </div>
      </Panel>

      <div class="settings-save">
        <span>默认值保存后用于新的报告任务；已经创建的任务不会被改写。</span>
        <button class="primary" type="button" :disabled="settings.saving" @click="settings.saveSettings">
          {{ settings.saving ? '保存中...' : '保存默认设置' }}
        </button>
      </div>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ApiError } from '../api/client';
import Chip from '../components/Chip.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import { useSettingsStore } from '../stores/settings';

const settings = useSettingsStore();
const skillFileInput = ref<HTMLInputElement | null>(null);
const pendingDeleteId = ref('');
const builtinSkills = computed(() => settings.reportSkills.filter((skill) => skill.source === 'builtin'));
const userSkills = computed(() => settings.reportSkills.filter((skill) => skill.source === 'user'));
const currentSkill = computed(() => settings.reportSkills.find((skill) => skill.id === settings.reportSkillId));

onMounted(() => settings.loadSettings());

async function onSkillFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  try {
    await settings.importReportSkill(file);
  } catch (error) {
    if (error instanceof ApiError && error.code === 'REPORT_SKILL_EXISTS' && window.confirm('同名用户 Skill 已存在，是否更新？')) {
      await settings.importReportSkill(file, true);
    }
  }
}

async function requestDelete(skillId: string) {
  if (pendingDeleteId.value !== skillId) {
    pendingDeleteId.value = skillId;
    return;
  }
  await settings.deleteReportSkill(skillId);
  pendingDeleteId.value = '';
}

async function copyPath(path: string) {
  if (path) await navigator.clipboard.writeText(path);
}
</script>

<style scoped>
.sr-only {
  display: none;
}

.current-skill,
.skill-toolbar,
.settings-save {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.current-skill {
  margin-bottom: 16px;
}

.current-skill span,
.current-skill p,
.skill-toolbar code,
.settings-save span {
  color: var(--muted);
  font-size: 12px;
}

.current-skill strong {
  display: block;
  margin: 3px 0;
  font-size: 20px;
}

.current-skill p {
  margin: 0;
}

.path-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
}

.path-row span {
  color: var(--muted);
  font-size: 12px;
}

.path-row code,
.skill-toolbar code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #bfe8f6;
}

.skill-toolbar > div:first-child {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.skill-actions {
  flex: 0 0 auto;
  margin: 0;
}

.skill-table {
  margin-top: 14px;
  border-top: 1px solid var(--line);
}

.skill-row {
  width: 100%;
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr) 60px 150px;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
  border: 0;
  border-bottom: 1px solid rgba(81, 220, 255, .14);
  background: transparent;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.skill-row.active {
  background: rgba(81, 220, 255, .06);
}

.skill-source {
  color: var(--cyan);
  font-size: 12px;
}

.skill-name {
  min-width: 0;
}

.skill-name strong,
.skill-name small {
  display: block;
}

.skill-name small {
  overflow: hidden;
  color: var(--muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-row code {
  color: var(--muted);
}

.skill-row-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  color: var(--muted);
  font-size: 12px;
}

.danger-link {
  border: 0;
  background: transparent;
  color: var(--red);
  cursor: pointer;
}

.settings-save {
  padding: 14px 16px;
  border-top: 1px solid var(--line);
}

@media (max-width: 760px) {
  .skill-toolbar,
  .settings-save {
    align-items: stretch;
    flex-direction: column;
  }

  .skill-row {
    grid-template-columns: 54px minmax(0, 1fr) auto;
  }

  .skill-row > code {
    display: none;
  }

  .skill-row-actions {
    grid-column: 2 / -1;
    justify-content: flex-start;
  }
}
</style>
