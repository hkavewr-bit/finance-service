<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'

// ─────────────────────────── 常量 ───────────────────────────
const DEFAULT_SENDER_ID = 'CUS00000001'
const CHANNEL_CODE = 'MOBILE_BANK'
const OPERATOR_NO = 'EMP000006'

const OBJECT_LABELS = {
  account: '账户',
  card: '银行卡',
  loan_product: '贷款产品',
  wealth_product: '理财产品',
}

const QUICK_SUGGESTIONS = [
  '查一下我的账户余额',
  '查一下我的交易流水',
  '我想申请一笔贷款',
  '我要挂失银行卡',
  '我要投诉',
  '你们有哪些贷款产品',
]

const SIDEBAR_TABS = [
  { key: 'accounts', label: '账户' },
  { key: 'cards', label: '银行卡' },
  { key: 'loans', label: '贷款产品' },
  { key: 'wealth', label: '理财产品' },
]

// ─────────────────────────── 状态 ───────────────────────────
const senderId = ref(DEFAULT_SENDER_ID)
const draftMessage = ref('')
const isSending = ref(false)
const isStreaming = ref(false)
const errorMessage = ref('')

const messages = ref([])
const messagesContainer = ref(null)

const activeTab = ref('accounts')
const accounts = ref([])
const cards = ref([])
const loanProducts = ref([])
const wealthProducts = ref([])
const isLoadingSidebar = ref(false)
const sidebarError = ref('')

const currentBotMessageId = ref(null) // 流式期间正在写入的 bot 消息索引

// ─────────────────────────── 工具 ───────────────────────────
function uuid() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function financeHeaders() {
  return {
    Authorization: `Bearer ${senderId.value.trim() || DEFAULT_SENDER_ID}`,
    'X-Channel-Code': CHANNEL_CODE,
    'X-Operator-No': OPERATOR_NO,
    'X-Request-Id': uuid(),
  }
}

function objectTitle(type, obj) {
  switch (type) {
    case 'account':
      return obj.account_no ? `账户 ${obj.account_no}` : '账户'
    case 'card':
      return obj.card_no ? `银行卡 ${obj.card_no}` : '银行卡'
    case 'loan_product':
      return obj.product_code ? `贷款产品 ${obj.product_code}` : '贷款产品'
    case 'wealth_product':
      return obj.product_name || (obj.product_code ? `理财产品 ${obj.product_code}` : '理财产品')
    default:
      return '业务对象'
  }
}

function objectMeta(type, obj) {
  if (type === 'account') {
    const pn = obj.account_product?.product_name || obj.product_name || ''
    const bal = obj.balance_amount != null ? `余额 ¥${obj.balance_amount}` : ''
    return [pn, bal].filter(Boolean).join(' · ')
  }
  if (type === 'card') {
    const lvl = obj.card_level ? `等级 ${obj.card_level}` : ''
    const st = obj.card_status ? `状态 ${obj.card_status}` : ''
    return [lvl, st].filter(Boolean).join(' · ')
  }
  if (type === 'loan_product') {
    const rate = obj.rate_range
      ? `年化 ${(Number(obj.rate_range.min) * 100).toFixed(2)}%~${(Number(obj.rate_range.max) * 100).toFixed(2)}%`
      : ''
    const term = obj.term_range ? `期限 ${obj.term_range.min}-${obj.term_range.max}月` : ''
    return [rate, term].filter(Boolean).join(' · ')
  }
  if (type === 'wealth_product') {
    const risk = obj.risk_level ? `风险 ${obj.risk_level}` : ''
    const yld = obj.expected_yield_rate != null
      ? `预期年化 ${(Number(obj.expected_yield_rate) * 100).toFixed(2)}%`
      : ''
    return [risk, yld].filter(Boolean).join(' · ')
  }
  return ''
}

function objectId(type, obj) {
  switch (type) {
    case 'account':
      return obj.account_no || ''
    case 'card':
      return obj.card_no || ''
    case 'loan_product':
      return obj.product_code || ''
    case 'wealth_product':
      return obj.product_code || obj.product_name || ''
    default:
      return ''
  }
}

function objectAttributes(type, obj) {
  if (type === 'account') {
    return {
      account_no: obj.account_no,
      balance_amount: obj.balance_amount,
      currency_code: obj.currency_code,
      product_name: obj.account_product?.product_name || obj.product_name || '',
    }
  }
  if (type === 'card') {
    return { card_no: obj.card_no, card_type: obj.card_type, card_level: obj.card_level, card_status: obj.card_status, account_no: obj.account_no }
  }
  if (type === 'loan_product') {
    return { product_code: obj.product_code, rate_range: obj.rate_range, term_range: obj.term_range }
  }
  if (type === 'wealth_product') {
    return { product_code: obj.product_code, product_name: obj.product_name, risk_level: obj.risk_level, expected_yield_rate: obj.expected_yield_rate, open_status: obj.open_status }
  }
  return {}
}

// ─────────────────────────── 消息渲染 ───────────────────────────
function appendUserText(text) {
  messages.value.push({ role: 'user', type: 'text', text })
  scrollToBottom()
}

function appendUserObject(type, obj) {
  messages.value.push({
    role: 'user',
    type: 'object',
    objectType: type,
    payload: obj,
  })
  scrollToBottom()
}

function appendBotText(text) {
  const msg = { role: 'bot', type: 'text', text }
  messages.value.push(msg)
  currentBotMessageId.value = messages.value.length - 1
  scrollToBottom()
  return messages.value.length - 1
}

function appendBotObject(type, obj) {
  const msg = { role: 'bot', type: 'object', objectType: type, payload: obj }
  messages.value.push(msg)
  scrollToBottom()
}

function applyDelta(delta) {
  const idx = currentBotMessageId.value
  if (idx == null || !messages.value[idx]) {
    // 首个 delta 到达时兜底创建一条 bot 文本消息
    currentBotMessageId.value = appendBotText(delta)
    return
  }
  messages.value[idx].text += delta
  scrollToBottom()
}

// ─────────────────────────── 请求 ───────────────────────────
async function streamChat(payload) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sender_id: senderId.value.trim(), ...payload }),
  })

  if (!response.ok) {
    let detail = ''
    try { detail = (await response.json()).detail || '' } catch { /* ignore */ }
    throw new Error(detail || `请求失败 (${response.status})`)
  }
  if (!response.body) throw new Error('浏览器不支持流式响应')

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      for (const line of rawEvent.split('\n')) {
        if (!line.startsWith('data: ')) continue
        let data
        try { data = JSON.parse(line.slice(6)) } catch { continue }
        handleSseEvent(data)
      }
    }
  }
}

function handleSseEvent(data) {
  if (data.type === 'bot_text') {
    isStreaming.value = true
    applyDelta(data.delta || '')
  } else if (data.type === 'bot_object') {
    appendBotObject(data.object?.type, data.object || {})
  } else if (data.type === 'turn_end') {
    isStreaming.value = false
    currentBotMessageId.value = null
    scrollToBottom()
  }
}

async function sendPayload(payload) {
  if (isSending.value) return
  errorMessage.value = ''
  isSending.value = true
  try {
    await streamChat(payload)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '请求失败'
  } finally {
    isSending.value = false
    isStreaming.value = false
    currentBotMessageId.value = null
  }
}

async function sendTextMessage() {
  const text = draftMessage.value.trim()
  if (!senderId.value.trim()) {
    errorMessage.value = '请先输入客户号（sender_id）。'
    return
  }
  if (!text) return
  draftMessage.value = ''
  appendUserText(text)
  await sendPayload({ text })
}

async function sendSuggestion(text) {
  appendUserText(text)
  await sendPayload({ text })
}

async function sendObject(type, obj) {
  if (!senderId.value.trim()) {
    errorMessage.value = '请先输入客户号（sender_id）。'
    return
  }
  appendUserObject(type, obj)
  await sendPayload({
    object: {
      type,
      id: objectId(type, obj),
      title: objectTitle(type, obj),
      attributes: objectAttributes(type, obj),
    },
  })
}

// ─────────────────────────── 会话 / 历史 ───────────────────────────
async function newConversation() {
  if (!senderId.value.trim()) {
    errorMessage.value = '请先输入客户号（sender_id）。'
    return
  }
  try {
    await fetch('/api/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender_id: senderId.value.trim() }),
    })
    messages.value = []
    errorMessage.value = ''
    loadHistory()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '新建会话失败'
  }
}

async function loadHistory() {
  try {
    const response = await fetch(`/api/chat/history?sender_id=${encodeURIComponent(senderId.value.trim())}`)
    const data = await response.json()
    messages.value = []
    for (const m of data.messages || []) {
      if (m.role === 'user') {
        if (m.object) {
          appendUserObject(m.object.type, m.object)
        } else if (m.text) {
          messages.value.push({ role: 'user', type: 'text', text: m.text })
        }
      } else {
        if (m.object) {
          appendBotObject(m.object.type, m.object)
        } else if (m.text) {
          messages.value.push({ role: 'bot', type: 'text', text: m.text })
        }
      }
    }
    scrollToBottom()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '加载历史失败'
  }
}

// ─────────────────────────── 侧栏对象列表 ───────────────────────────
async function loadSidebar() {
  const sid = senderId.value.trim() || DEFAULT_SENDER_ID
  isLoadingSidebar.value = true
  sidebarError.value = ''
  try {
    const [accountsRes, cardsRes, loansRes, wealthRes] = await Promise.all([
      fetch(`/finance/customers/${sid}/accounts`, { headers: financeHeaders() }),
      fetch(`/finance/customers/${sid}/cards`, { headers: financeHeaders() }),
      fetch('/finance/loan/products', { headers: financeHeaders() }),
      fetch('/finance/wealth/products', { headers: financeHeaders() }),
    ])

    const unwrap = (r) => r.json().then((d) => (d.code === 0 ? d.data : Promise.reject(new Error(d.message || '接口错误'))))

    const [a, c, l, w] = await Promise.all([
      unwrap(accountsRes),
      unwrap(cardsRes),
      unwrap(loansRes),
      unwrap(wealthRes),
    ])

    accounts.value = a?.list ?? a ?? []
    cards.value = c?.list ?? c ?? []
    loanProducts.value = (l?.list ?? l ?? []).slice(0, 30)
    wealthProducts.value = (w?.list ?? w ?? []).slice(0, 30)
  } catch (e) {
    sidebarError.value = e instanceof Error ? e.message : '加载业务对象失败'
  } finally {
    isLoadingSidebar.value = false
  }
}

const sidebarList = computed(() => {
  switch (activeTab.value) {
    case 'accounts': return accounts.value
    case 'cards': return cards.value
    case 'loans': return loanProducts.value
    case 'wealth': return wealthProducts.value
    default: return []
  }
})

const sidebarType = computed(() => {
  switch (activeTab.value) {
    case 'accounts': return 'account'
    case 'cards': return 'card'
    case 'loans': return 'loan_product'
    case 'wealth': return 'wealth_product'
    default: return 'account'
  }
})

// ─────────────────────────── 生命周期 ───────────────────────────
watch(senderId, () => {
  loadHistory()
  loadSidebar()
})

onMounted(() => {
  loadHistory()
  loadSidebar()
})
</script>

<template>
  <div class="app">
    <!-- 顶部 header -->
    <header class="header">
      <div class="header-brand">
        <div class="logo">金</div>
        <div>
          <div class="header-title">金融客服系统</div>
          <div class="header-sub">智能客服 · 金融小二</div>
        </div>
      </div>
      <div class="header-actions">
        <span class="agent-tag">🤖 金融小二 · 在线</span>
        <button class="btn btn-ghost" @click="newConversation">＋ 新对话</button>
      </div>
    </header>

    <div class="body">
      <!-- 左侧控制区 -->
      <aside class="controls">
        <label class="field-label" for="sender-id">客户号 sender_id</label>
        <input
          id="sender-id"
          v-model="senderId"
          class="input"
          placeholder="例如 CUS00000001"
          @change="() => { loadHistory(); loadSidebar() }"
        />
        <p class="hint">演示身份已绑定账户 / 银行卡 / 额度等数据</p>
        <button class="btn btn-block" @click="loadSidebar" :disabled="isLoadingSidebar">
          {{ isLoadingSidebar ? '加载中…' : '刷新业务对象' }}
        </button>
        <div v-if="sidebarError" class="error-text">{{ sidebarError }}</div>
      </aside>

      <!-- 中间聊天区 -->
      <main class="chat">
        <div class="chat-scroll" ref="messagesContainer">
          <div v-if="messages.length === 0" class="empty-state">
            <div class="empty-avatar">🤖</div>
            <div class="empty-title">您好，我是金融小二</div>
            <div class="empty-desc">可以帮您查账户余额、交易流水、申请贷款、挂失银行卡、提交投诉等。</div>
            <div class="suggestion-row">
              <span
                v-for="s in QUICK_SUGGESTIONS"
                :key="s"
                class="suggestion-chip"
                @click="sendSuggestion(s)"
              >{{ s }}</span>
            </div>
          </div>

          <template v-else>
            <div
              v-for="(msg, i) in messages"
              :key="i"
              class="turn"
              :class="msg.role === 'user' ? 'turn-user' : 'turn-bot'"
            >
              <div class="bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-bot'">
                <!-- 对象卡片 -->
                <div v-if="msg.type === 'object'" class="object-card" :class="`obj-${msg.objectType}`">
                  <div class="object-badge">{{ OBJECT_LABELS[msg.objectType] || '业务对象' }}</div>
                  <div class="object-title">{{ objectTitle(msg.objectType, msg.payload) }}</div>
                  <div class="object-meta">{{ objectMeta(msg.objectType, msg.payload) }}</div>
                </div>
                <!-- 文本 -->
                <div v-else class="text-content">{{ msg.text }}</div>
              </div>
            </div>

            <!-- 等待回复的输入指示（流式文本开始后自动隐藏） -->
            <div v-if="isSending && !isStreaming" class="turn turn-bot">
              <div class="bubble bubble-bot typing">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
            </div>
          </template>
        </div>

        <!-- 输入区 -->
        <div class="composer">
          <div v-if="errorMessage" class="error-text">{{ errorMessage }}</div>
          <div class="composer-row">
            <textarea
              v-model="draftMessage"
              class="composer-input"
              rows="2"
              placeholder="请输入您的问题…（Enter 发送，Shift+Enter 换行）"
              @keydown.enter.exact.prevent="sendTextMessage"
            ></textarea>
            <button class="btn btn-send" :disabled="isSending" @click="sendTextMessage">
              {{ isSending ? '发送中…' : '发送' }}
            </button>
          </div>
        </div>
      </main>

      <!-- 右侧业务对象侧栏 -->
      <aside class="sidebar">
        <div class="sidebar-tabs">
          <button
            v-for="t in SIDEBAR_TABS"
            :key="t.key"
            class="tab"
            :class="{ active: activeTab === t.key }"
            @click="activeTab = t.key"
          >{{ t.label }}</button>
        </div>
        <div class="sidebar-list">
          <div v-if="isLoadingSidebar" class="sidebar-empty">加载中…</div>
          <div v-else-if="sidebarList.length === 0" class="sidebar-empty">暂无数据</div>
          <div v-else class="side-card" v-for="(obj, i) in sidebarList" :key="i">
            <div class="side-card-title">{{ objectTitle(sidebarType, obj) }}</div>
            <div class="side-card-meta">{{ objectMeta(sidebarType, obj) }}</div>
            <button class="btn btn-mini" @click="sendObject(sidebarType, obj)">发送</button>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style>
:root {
  --bg: #0b1220;
  --bg-soft: #101a2c;
  --panel: rgba(255, 255, 255, 0.04);
  --border: rgba(255, 255, 255, 0.08);
  --text: #e8edf5;
  --text-dim: #8b98ad;
  --gold: #d9a441;
  --gold-soft: rgba(217, 164, 65, 0.16);
  --blue: #3b82f6;
  --blue-soft: rgba(59, 130, 246, 0.16);
}

* { box-sizing: border-box; }

html, body, #app {
  margin: 0;
  height: 100%;
  overflow: hidden;
}

body {
  background: radial-gradient(1200px 800px at 15% -10%, #14263f 0%, transparent 55%),
              radial-gradient(1000px 700px at 110% 10%, #2a1f12 0%, transparent 50%),
              var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* header */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 22px;
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
  background: rgba(11, 18, 32, 0.7);
}
.header-brand { display: flex; align-items: center; gap: 12px; }
.logo {
  width: 40px; height: 40px;
  display: grid; place-items: center;
  border-radius: 12px;
  font-weight: 700; font-size: 20px;
  color: #1a1406;
  background: linear-gradient(135deg, #f0c060, var(--gold));
}
.header-title { font-size: 17px; font-weight: 600; }
.header-sub { font-size: 12px; color: var(--text-dim); }
.header-actions { display: flex; align-items: center; gap: 12px; }
.agent-tag {
  font-size: 12px; color: #7fd49a;
  padding: 5px 12px; border-radius: 999px;
  background: rgba(127, 212, 154, 0.12);
  border: 1px solid rgba(127, 212, 154, 0.25);
}

/* buttons */
.btn {
  cursor: pointer;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--text);
  padding: 9px 16px;
  border-radius: 10px;
  font-size: 13px;
  transition: all .15s;
}
.btn:hover { border-color: var(--gold); color: var(--gold); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-ghost { background: transparent; }
.btn-block { width: 100%; }
.btn-send {
  background: linear-gradient(135deg, #e9b84c, var(--gold));
  color: #1a1406; font-weight: 600; border: none;
}
.btn-send:hover { filter: brightness(1.05); color: #1a1406; }
.btn-mini { padding: 4px 12px; font-size: 12px; }

/* layout */
.body {
  flex: 1;
  display: grid;
  grid-template-columns: 220px 1fr 320px;
  grid-template-rows: minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
}

/* controls */
.controls {
  padding: 18px 16px;
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 10px;
  min-height: 0;
  overflow-y: auto;
}
.field-label { font-size: 12px; color: var(--text-dim); }
.input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--text);
  font-size: 13px;
  outline: none;
}
.input:focus { border-color: var(--blue); }
.hint { font-size: 11px; color: var(--text-dim); line-height: 1.5; }
.error-text { font-size: 12px; color: #f87171; line-height: 1.5; }

/* chat */
.chat { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.chat-scroll { flex: 1; overflow-y: auto; padding: 22px 26px; }
.empty-state { text-align: center; padding: 60px 20px; }
.empty-avatar { font-size: 44px; margin-bottom: 12px; }
.empty-title { font-size: 18px; font-weight: 600; margin-bottom: 6px; }
.empty-desc { font-size: 13px; color: var(--text-dim); margin-bottom: 22px; }
.suggestion-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.suggestion-chip {
  font-size: 12px; color: var(--gold);
  padding: 7px 14px; border-radius: 999px;
  background: var(--gold-soft);
  border: 1px solid rgba(217, 164, 65, 0.3);
  cursor: pointer; transition: all .15s;
}
.suggestion-chip:hover { background: rgba(217, 164, 65, 0.28); }

.turn { display: flex; margin-bottom: 16px; }
.turn-user { justify-content: flex-end; }
.turn-bot { justify-content: flex-start; }
.bubble {
  max-width: 76%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}
.bubble-user {
  background: linear-gradient(135deg, #1d4ed8, var(--blue));
  border-bottom-right-radius: 4px;
}
.bubble-bot {
  background: var(--panel);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}
.text-content { color: var(--text); }

.typing { display: flex; gap: 4px; align-items: center; }
.dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--text-dim);
  animation: blink 1.2s infinite;
}
.dot:nth-child(2) { animation-delay: .2s; }
.dot:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%, 60%, 100% { opacity: .25; } 30% { opacity: 1; } }

/* object cards */
.object-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  min-width: 220px;
}
.obj-account { border-left: 3px solid var(--blue); }
.obj-card { border-left: 3px solid var(--gold); }
.obj-loan_product { border-left: 3px solid var(--gold); }
.obj-wealth_product { border-left: 3px solid #22c55e; }
.object-badge {
  font-size: 11px; color: var(--text-dim);
  margin-bottom: 6px;
}
.object-title { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.object-meta { font-size: 12px; color: var(--text-dim); }

/* composer */
.composer { padding: 14px 20px 18px; border-top: 1px solid var(--border); }
.composer-row { display: flex; gap: 10px; align-items: flex-end; }
.composer-input {
  flex: 1;
  resize: none;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--text);
  font-size: 14px;
  outline: none;
  font-family: inherit;
}
.composer-input:focus { border-color: var(--blue); }

/* sidebar */
.sidebar {
  border-left: 1px solid var(--border);
  display: flex; flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.sidebar-tabs { display: flex; border-bottom: 1px solid var(--border); }
.tab {
  flex: 1;
  padding: 12px 0;
  font-size: 13px;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--text-dim);
  border-bottom: 2px solid transparent;
}
.tab.active { color: var(--gold); border-bottom-color: var(--gold); }
.sidebar-list { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.sidebar-empty { text-align: center; color: var(--text-dim); font-size: 13px; padding: 30px 0; }
.side-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  background: var(--panel);
}
.side-card-title { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.side-card-meta { font-size: 11px; color: var(--text-dim); margin-bottom: 10px; line-height: 1.5; }
</style>
