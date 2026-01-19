<template>
  <div class="preview-wrapper">
    <!-- 侧边文件列表 -->
    <aside class="preview-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="sidebar-title" v-show="!sidebarCollapsed">
          <el-icon><FolderOpened /></el-icon>
          <span>文件列表</span>
        </div>
        <el-button 
          class="collapse-btn" 
          link 
          @click="sidebarCollapsed = !sidebarCollapsed"
        >
          <el-icon :size="18">
            <component :is="sidebarCollapsed ? Expand : Fold" />
          </el-icon>
        </el-button>
      </div>
      
      <template v-if="!sidebarCollapsed">
        <el-input 
          v-model="fileSearch" 
          placeholder="搜索文件..." 
          size="small" 
          class="sidebar-search" 
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-scrollbar class="sidebar-list">
          <div 
            v-for="file in filteredFiles" 
            :key="file.id" 
            class="sidebar-file"
            :class="{ active: currentFile && file.id === currentFile.id }"
            @click="selectFile(file)"
          >
            <el-icon class="file-icon"><Document /></el-icon>
            <span class="file-name">{{ file.filename }}</span>
          </div>
        </el-scrollbar>
        
        <div class="sidebar-pagination">
          <el-pagination
            v-model:current-page="sidebarPage"
            v-model:page-size="sidebarPageSize"
            :total="sidebarTotal"
            :page-sizes="[10, 20, 50]"
            layout="prev, pager, next"
            size="small"
            :pager-count="3"
          />
        </div>
      </template>
    </aside>

    <!-- 主内容区 -->
    <main class="preview-main">
      <!-- 顶部工具栏 -->
      <header class="preview-header">
        <div class="header-left">
          <span class="current-file-name">{{ currentFile?.filename || '未选择文件' }}</span>
        </div>
        <div class="header-center">
          <div class="view-toggle">
            <button 
              class="toggle-btn" 
              :class="{ active: viewMode === 'origin' || viewMode === 'both' }"
              @click="handleViewMode('origin')"
            >
              <el-icon><Document /></el-icon>
              <span>原文件</span>
            </button>
            <button 
              class="toggle-btn" 
              :class="{ active: viewMode === 'markdown' || viewMode === 'both' }"
              @click="handleViewMode('markdown')"
            >
              <el-icon><EditPen /></el-icon>
              <span>Markdown</span>
            </button>
          </div>
          <!-- 高亮控制 -->
          <div class="highlight-toggle" v-if="viewMode !== 'markdown' && isPdf(currentFile?.filename)">
            <el-switch 
              v-model="showHighlight" 
              active-text="高亮区域" 
              inactive-text=""
              size="small"
            />
          </div>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleExport">
            <el-button type="primary">
              <el-icon><Download /></el-icon>
              <span>下载</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="original">原始文件</el-dropdown-item>
                <el-dropdown-item v-for="(name, format) in ExportFormatNames" :key="format" :command="format">
                  {{ name }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 预览内容区 -->
      <div class="preview-content">
        <!-- 原文件预览 -->
        <div 
          v-if="viewMode !== 'markdown'" 
          class="preview-panel origin-panel"
          :class="{ 'full-width': viewMode === 'origin' }"
        >
          <div class="panel-content">
            <template v-if="showOrigin && currentFile">
              <template v-if="isPdf(currentFile.filename)">
                <!-- PDF.js 渲染容器 -->
                <div class="pdf-container" ref="pdfContainer">
                  <div v-if="pdfLoading" class="loading-state">
                    <el-icon class="is-loading" :size="32"><Loading /></el-icon>
                    <span>正在加载PDF...</span>
                  </div>
                  <div class="pdf-pages" ref="pdfPagesContainer">
                    <div 
                      v-for="pageNum in totalPages" 
                      :key="pageNum"
                      class="pdf-page-wrapper"
                      :data-page="pageNum"
                    >
                      <canvas 
                        :ref="el => setCanvasRef(el, pageNum)" 
                        class="pdf-canvas"
                      ></canvas>
                      <!-- 高亮覆盖层 -->
                      <svg 
                        v-if="showHighlight && pageRegions[pageNum - 1]"
                        class="highlight-overlay"
                        :viewBox="`0 0 ${pageRegions[pageNum - 1].page_width} ${pageRegions[pageNum - 1].page_height}`"
                        preserveAspectRatio="none"
                      >
                        <rect
                          v-for="(region, idx) in pageRegions[pageNum - 1].regions"
                          :key="idx"
                          :x="region.bbox[0]"
                          :y="region.bbox[1]"
                          :width="region.bbox[2] - region.bbox[0]"
                          :height="region.bbox[3] - region.bbox[1]"
                          :class="['highlight-rect', `type-${region.type}`, `category-${region.category}`]"
                        />
                      </svg>
                    </div>
                  </div>
                  <!-- PDF 控制栏 -->
                  <div class="pdf-controls" v-if="totalPages > 0">
                    <el-button-group>
                      <el-button size="small" @click="zoomOut" :disabled="scale <= 0.5">
                        <el-icon><ZoomOut /></el-icon>
                      </el-button>
                      <el-button size="small" disabled>{{ Math.round(scale * 100) }}%</el-button>
                      <el-button size="small" @click="zoomIn" :disabled="scale >= 3">
                        <el-icon><ZoomIn /></el-icon>
                      </el-button>
                    </el-button-group>
                    <span class="page-info">第 {{ currentPage }} / {{ totalPages }} 页</span>
                  </div>
                </div>
              </template>
              <template v-else-if="isOffice(currentFile.filename)">
                <div v-if="loadingOffice" class="loading-state">
                  <el-icon class="is-loading" :size="32"><Loading /></el-icon>
                  <span>正在加载预览...</span>
                </div>
                <div v-else class="office-preview" v-html="officeContent"></div>
              </template>
              <template v-else-if="isImage(currentFile.filename)">
                <img :src="fileUrl" class="image-preview" />
              </template>
              <template v-else-if="isText(currentFile.filename)">
                <el-scrollbar>
                  <pre class="text-preview">{{ textContent }}</pre>
                </el-scrollbar>
              </template>
              <template v-else>
                <el-empty description="暂不支持该类型文件预览" :image-size="100" />
              </template>
            </template>
          </div>
        </div>

        <!-- Markdown预览 -->
        <div 
          v-if="viewMode !== 'origin'" 
          class="preview-panel markdown-panel"
          :class="{ 'full-width': viewMode === 'markdown' }"
        >
          <div class="panel-content">
            <div v-if="loading" class="loading-state">
              <el-icon class="is-loading" :size="32"><Loading /></el-icon>
              <span>加载中...</span>
            </div>
            <div v-else class="markdown-content" v-html="renderedContent"></div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  FolderOpened, Document, Search, Download, ArrowDown, 
  EditPen, Expand, Fold, Loading, ZoomIn, ZoomOut 
} from '@element-plus/icons-vue'
import axios from 'axios'
import MarkdownIt from 'markdown-it'
import mk from 'markdown-it-katex'
import 'katex/dist/katex.min.css'
import mammoth from 'mammoth'
import * as XLSX from 'xlsx'
import * as pdfjsLib from 'pdfjs-dist'
import { getUserId } from '@/utils/user'
import { filesApi, type PageRegions } from '@/api/files'

// 设置 PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`

const route = useRoute()
const md = MarkdownIt({ html: true, linkify: true, typographer: true }).use(mk)

interface FileItem {
  id: string
  filename: string
  size: number
  uploadTime: string
  status: string
}

const sidebarCollapsed = ref(false)
const allFiles = ref<FileItem[]>([])
const sidebarPage = ref(1)
const sidebarPageSize = ref(10)
const sidebarTotal = ref(0)
const fileSearch = ref('')
const currentFile = ref<FileItem | null>(null)
const isReady = ref(false)

// PDF.js 相关状态
const pdfContainer = ref<HTMLElement | null>(null)
const pdfPagesContainer = ref<HTMLElement | null>(null)
const pdfDoc = ref<pdfjsLib.PDFDocumentProxy | null>(null)
const totalPages = ref(0)
const currentPage = ref(1)
const scale = ref(1.5)
const pdfLoading = ref(false)
const canvasRefs = ref<Map<number, HTMLCanvasElement>>(new Map())

// 高亮相关状态
const showHighlight = ref(true)
const pageRegions = ref<PageRegions[]>([])

// 获取侧边栏文件列表
const fetchSidebarFiles = async () => {
  try {
    const res = await axios.get('/api/files', {
      params: { page: sidebarPage.value, page_size: sidebarPageSize.value, search: fileSearch.value },
      headers: { 'X-User-Id': getUserId() }
    })
    allFiles.value = res.data.files
    sidebarTotal.value = res.data.total
  } catch (e) {
    ElMessage.error('获取文件列表失败')
    allFiles.value = []
    sidebarTotal.value = 0
  }
}

// 根据ID获取单个文件信息
const loadFileById = async (fileId: string) => {
  try {
    const res = await axios.get(`/api/files/${fileId}`, {
      headers: { 'X-User-Id': getUserId() }
    })
    if (res.data) {
      currentFile.value = res.data
    }
  } catch (e) {
    console.error('获取文件信息失败', e)
  }
}

// 监听分页变化
watch(sidebarPage, () => {
  if (isReady.value) {
    fetchSidebarFiles()
  }
})

watch([sidebarPageSize, fileSearch], () => {
  if (isReady.value) {
    sidebarPage.value = 1
    fetchSidebarFiles()
  }
})

onMounted(async () => {
  const fileId = route.params.id as string
  const pageFromQuery = Number(route.query.page) || 1
  
  // 设置初始页码
  sidebarPage.value = pageFromQuery
  
  if (fileId) {
    // 加载指定文件
    await loadFileById(fileId)
  }
  
  // 加载对应页的文件列表
  await fetchSidebarFiles()
  
  // 如果没有指定文件，选中第一个
  if (!currentFile.value && allFiles.value.length > 0) {
    currentFile.value = allFiles.value[0]
  }

  // 初始化完成
  await nextTick()
  isReady.value = true

  // 如果初始视图模式需要显示 markdown，立即加载内容
  if (viewMode.value !== 'origin' && currentFile.value) {
    await fetchParsedContent()
  }
})

onUnmounted(() => {
  // 清理 PDF 文档
  if (pdfDoc.value) {
    pdfDoc.value.destroy()
    pdfDoc.value = null
  }
})

const filteredFiles = computed(() => allFiles.value)

const selectFile = (file: FileItem) => {
  currentFile.value = file
  page.value = 1
  if (viewMode.value !== 'origin') {
    fetchParsedContent()
  }
}

const showOrigin = ref(true)
const isImage = (name?: string) => name ? /\.(png|jpe?g|gif|bmp|webp)$/i.test(name) : false
const isText = (name?: string) => name ? /\.(txt|md|json|log)$/i.test(name) : false
const isWord = (name?: string) => name ? /\.(doc|docx)$/i.test(name) : false
const isExcel = (name?: string) => name ? /\.(xls|xlsx)$/i.test(name) : false
const isOffice = (name?: string) => name ? /\.(doc|docx|xls|xlsx)$/i.test(name) : false
const isPdf = (name?: string) => name ? /\.pdf$/i.test(name) : false

const page = ref(1)
const parsedContent = ref('')
const loading = ref(false)

const fetchParsedContent = async () => {
  if (!currentFile.value) return
  loading.value = true
  try {
    const res = await axios.get(`/api/files/${currentFile.value.id}/parsed_content`, {
      headers: { 'X-User-Id': getUserId() }
    })
    parsedContent.value = res.data || ''
  } catch (e) {
    ElMessage.error('获取解析内容失败')
    parsedContent.value = ''
  } finally {
    loading.value = false
  }
}

const viewMode = ref<'both' | 'origin' | 'markdown'>('both')

const handleViewMode = (mode: 'origin' | 'markdown') => {
  viewMode.value = viewMode.value === mode ? 'both' : mode
}

watch(viewMode, (newMode) => {
  if (newMode !== 'origin') fetchParsedContent()
})

const ExportFormats = { MARKDOWN: 'markdown', MARKDOWN_PAGE: 'markdown_page' } as const
type ExportFormat = typeof ExportFormats[keyof typeof ExportFormats]
const ExportFormatNames: Record<ExportFormat, string> = {
  [ExportFormats.MARKDOWN]: 'Markdown',
  [ExportFormats.MARKDOWN_PAGE]: 'Markdown带页码'
}

const handleExport = async (format: string) => {
  if (!currentFile.value) return
  
  // 处理原始文件下载
  if (format === 'original') {
    try {
      const downloadUrl = filesApi.getFileDownloadUrl(currentFile.value.id)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = currentFile.value.filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      ElMessage.success('下载开始')
    } catch (e) {
      ElMessage.error('下载失败')
    }
    return
  }
  
  // 处理导出格式
  try {
    const res = await axios.get(`/api/files/${currentFile.value.id}/export`, {
      params: { format },
      headers: { 'X-User-Id': getUserId() }
    })
    if (res.data.status === 'success') {
      const response = await fetch(res.data.download_url)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = res.data.filename
      document.body.appendChild(link)
      link.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(link)
      ElMessage.success(`导出${ExportFormatNames[format as ExportFormat]}成功`)
    } else {
      ElMessage.error(`导出失败`)
    }
  } catch (e) {
    ElMessage.error(`导出失败`)
  }
}

const fileUrl = ref('')
const textContent = ref('')
const officeContent = ref('')
const loadingOffice = ref(false)

// 设置 canvas 引用
const setCanvasRef = (el: any, pageNum: number) => {
  if (el) {
    canvasRefs.value.set(pageNum, el as HTMLCanvasElement)
  }
}

// 加载 PDF 文件
const loadPdf = async () => {
  if (!currentFile.value || !isPdf(currentFile.value.filename)) return
  
  pdfLoading.value = true
  pageRegions.value = []
  
  // 清理旧的 PDF 文档
  if (pdfDoc.value) {
    pdfDoc.value.destroy()
    pdfDoc.value = null
  }
  
  try {
    // 使用代理 URL 加载 PDF
    const pdfUrl = filesApi.getFileContentUrl(currentFile.value.id)
    
    const loadingTask = pdfjsLib.getDocument({
      url: pdfUrl,
      httpHeaders: {
        'X-User-Id': getUserId()
      }
    })
    
    pdfDoc.value = await loadingTask.promise
    totalPages.value = pdfDoc.value.numPages
    currentPage.value = 1
    
    // 等待 DOM 更新
    await nextTick()
    
    // 渲染所有页面
    await renderAllPages()
    
    // 加载区域信息
    await loadRegions()
    
  } catch (e) {
    console.error('加载PDF失败', e)
    ElMessage.error('加载PDF失败')
  } finally {
    pdfLoading.value = false
  }
}

// 渲染所有 PDF 页面
const renderAllPages = async () => {
  if (!pdfDoc.value) return
  
  for (let pageNum = 1; pageNum <= totalPages.value; pageNum++) {
    await renderPage(pageNum)
  }
}

// 渲染单个页面
const renderPage = async (pageNum: number) => {
  if (!pdfDoc.value) return
  
  const page = await pdfDoc.value.getPage(pageNum)
  const canvas = canvasRefs.value.get(pageNum)
  
  if (!canvas) return
  
  const viewport = page.getViewport({ scale: scale.value })
  const context = canvas.getContext('2d')
  
  if (!context) return
  
  canvas.height = viewport.height
  canvas.width = viewport.width
  
  const renderContext = {
    canvasContext: context,
    viewport: viewport
  }
  
  await page.render(renderContext).promise
}

// 加载识别区域信息
const loadRegions = async () => {
  if (!currentFile.value) return
  
  try {
    const response = await filesApi.getFileRegions(currentFile.value.id)
    pageRegions.value = response.regions || []
  } catch (e) {
    console.error('加载区域信息失败', e)
    pageRegions.value = []
  }
}

// 缩放控制
const zoomIn = () => {
  scale.value = Math.min(scale.value + 0.25, 3)
}

const zoomOut = () => {
  scale.value = Math.max(scale.value - 0.25, 0.5)
}

// 监听缩放变化，重新渲染
watch(scale, async () => {
  if (pdfDoc.value) {
    await nextTick()
    await renderAllPages()
  }
})

const fetchFileUrl = async () => {
  if (!currentFile.value) return
  
  // 对于 PDF 文件，使用代理 URL
  if (isPdf(currentFile.value.filename)) {
    fileUrl.value = filesApi.getFileContentUrl(currentFile.value.id)
    await loadPdf()
    return
  }
  
  // 其他文件类型使用代理 URL
  try {
    fileUrl.value = filesApi.getFileContentUrl(currentFile.value.id)
  } catch (e) {
    fileUrl.value = ''
    textContent.value = ''
    officeContent.value = ''
  }
}

const previewOfficeFile = async () => {
  if (!currentFile.value || !fileUrl.value) return
  loadingOffice.value = true
  try {
    const response = await fetch(fileUrl.value, {
      headers: { 'X-User-Id': getUserId() }
    })
    const blob = await response.blob()
    if (isWord(currentFile.value.filename)) {
      const arrayBuffer = await blob.arrayBuffer()
      const result = await mammoth.convertToHtml({ arrayBuffer })
      officeContent.value = result.value
    } else if (isExcel(currentFile.value.filename)) {
      const arrayBuffer = await blob.arrayBuffer()
      const workbook = XLSX.read(arrayBuffer, { type: 'array' })
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
      officeContent.value = XLSX.utils.sheet_to_html(firstSheet)
    }
  } catch (e) {
    ElMessage.error('预览 Office 文件失败')
    officeContent.value = ''
  } finally {
    loadingOffice.value = false
  }
}

const fetchTextContent = async () => {
  if (!fileUrl.value) return
  try {
    const res = await axios.get(fileUrl.value, {
      headers: { 'X-User-Id': getUserId() }
    })
    textContent.value = res.data
  } catch (e) {
    textContent.value = ''
  }
}

watch(currentFile, async (newFile) => {
  if (!newFile) return
  fileUrl.value = ''
  textContent.value = ''
  officeContent.value = ''
  totalPages.value = 0
  pageRegions.value = []
  canvasRefs.value.clear()
  
  await fetchFileUrl()
  if (isText(newFile.filename)) await fetchTextContent()
  else if (isOffice(newFile.filename)) await previewOfficeFile()
})

const renderedContent = computed(() => md.render(parsedContent.value || ''))
</script>

<style scoped>
.preview-wrapper {
  display: flex;
  min-height: 100vh;
  background: var(--bg-secondary);
}

/* 侧边栏 */
.preview-sidebar {
  width: 260px;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal);
  flex-shrink: 0;
}

.preview-sidebar.collapsed {
  width: 48px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-light);
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-primary);
}

.collapse-btn {
  color: var(--text-muted);
}

.sidebar-search {
  margin: 12px 16px;
}

.sidebar-list {
  flex: 1;
  padding: 0 8px;
}

.sidebar-file {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: 4px;
}

.sidebar-file:hover {
  background: var(--bg-tertiary);
}

.sidebar-file.active {
  background: rgb(99 102 241 / 0.1);
  color: var(--primary-color);
}

.file-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.sidebar-file.active .file-icon {
  color: var(--primary-color);
}

.file-name {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-pagination {
  padding: 12px 16px;
  border-top: 1px solid var(--border-light);
}

/* 主内容区 */
.preview-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-light);
  gap: 16px;
}

.header-left {
  flex: 1;
  min-width: 0;
}

.current-file-name {
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 16px;
}

.view-toggle {
  display: flex;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 4px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.toggle-btn:hover {
  color: var(--text-primary);
}

.toggle-btn.active {
  background: var(--bg-primary);
  color: var(--primary-color);
  box-shadow: var(--shadow-sm);
}

.highlight-toggle {
  display: flex;
  align-items: center;
}

/* 预览内容 */
.preview-content {
  flex: 1;
  display: flex;
  gap: 1px;
  background: var(--border-light);
  overflow: hidden;
}

.preview-panel {
  flex: 1;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  min-width: 0;
  transition: flex var(--transition-normal);
}

.preview-panel.full-width {
  flex: 1 0 100%;
}

.panel-content {
  flex: 1;
  overflow: auto;
  padding: 24px;
}

/* PDF 容器样式 */
.pdf-container {
  width: 100%;
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  position: relative;
}

.pdf-pages {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #525659;
}

.pdf-page-wrapper {
  position: relative;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  background: white;
}

.pdf-canvas {
  display: block;
}

.highlight-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

/* 高亮矩形样式 */
.highlight-rect {
  fill: transparent;
  stroke-width: 2;
  opacity: 0.6;
}

/* 根据类型设置不同颜色 */
.highlight-rect.type-text {
  stroke: #4CAF50;
  fill: rgba(76, 175, 80, 0.1);
}

.highlight-rect.type-text_line {
  stroke: #2196F3;
  fill: rgba(33, 150, 243, 0.05);
}

.highlight-rect.type-title {
  stroke: #FF9800;
  fill: rgba(255, 152, 0, 0.15);
}

.highlight-rect.type-image {
  stroke: #E91E63;
  fill: rgba(233, 30, 99, 0.1);
}

.highlight-rect.type-table {
  stroke: #9C27B0;
  fill: rgba(156, 39, 176, 0.1);
}

.highlight-rect.type-equation,
.highlight-rect.type-interline_equation {
  stroke: #00BCD4;
  fill: rgba(0, 188, 212, 0.1);
}

.highlight-rect.type-figure {
  stroke: #FF5722;
  fill: rgba(255, 87, 34, 0.1);
}

.highlight-rect.category-preproc {
  stroke-dasharray: 4;
}

.pdf-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 12px;
  background: var(--bg-primary);
  border-top: 1px solid var(--border-light);
}

.page-info {
  font-size: 13px;
  color: var(--text-secondary);
}

.image-preview {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-md);
}

.text-preview {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  margin: 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px;
  color: var(--text-muted);
}

/* Markdown样式 */
.markdown-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
  color: var(--text-primary);
}

.markdown-content :deep(h1) { font-size: 1.75em; border-bottom: 1px solid var(--border-light); padding-bottom: 0.3em; }
.markdown-content :deep(h2) { font-size: 1.5em; }
.markdown-content :deep(h3) { font-size: 1.25em; }

.markdown-content :deep(p) { margin: 1em 0; }

.markdown-content :deep(code) {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', monospace;
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: var(--radius-md);
  overflow-x: auto;
}

.markdown-content :deep(pre code) {
  background: transparent;
  padding: 0;
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid var(--border-color);
  padding: 10px 14px;
  text-align: left;
}

.markdown-content :deep(th) {
  background: var(--bg-tertiary);
  font-weight: 600;
}

.markdown-content :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-md);
}

.markdown-content :deep(blockquote) {
  margin: 1em 0;
  padding: 0 1em;
  border-left: 4px solid var(--primary-color);
  color: var(--text-secondary);
}

.markdown-content :deep(.katex-display) {
  overflow-x: auto;
  margin: 1em 0;
}

.markdown-content :deep(.katex-mathml) {
  display: none !important;
}

@media (max-width: 1024px) {
  .preview-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    box-shadow: var(--shadow-xl);
  }
  
  .preview-sidebar.collapsed {
    transform: translateX(-100%);
    width: 260px;
  }
  
  .preview-content {
    flex-direction: column;
  }
  
  .preview-panel {
    min-height: 50vh;
  }
}

@media (max-width: 768px) {
  .preview-header {
    flex-wrap: wrap;
    padding: 12px 16px;
  }
  
  .header-center {
    order: 3;
    width: 100%;
    margin-top: 12px;
    flex-wrap: wrap;
  }
  
  .view-toggle {
    width: 100%;
    justify-content: center;
  }
  
  .panel-content {
    padding: 16px;
  }
}
</style>
