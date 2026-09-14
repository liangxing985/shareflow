<template>
  <div class="dashboard page-container">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #ecf5ff; color: #409eff">
            <el-icon :size="28"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ overview.orders?.total || 0 }}</div>
            <div class="stat-label">总订单数</div>
          </div>
          <div class="stat-extra">
            今日 {{ overview.orders?.today || 0 }} 单
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #f0f9eb; color: #67c23a">
            <el-icon :size="28"><Money /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value money-text">¥{{ formatMoney(overview.orders?.total_amount) }}</div>
            <div class="stat-label">总收款金额</div>
          </div>
          <div class="stat-extra">
            今日 ¥{{ formatMoney(overview.orders?.today_amount) }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #fdf6ec; color: #e6a23c">
            <el-icon :size="28"><Wallet /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value money-text">¥{{ formatMoney(overview.orders?.platform_fee) }}</div>
            <div class="stat-label">平台抽成累计</div>
          </div>
          <div class="stat-extra">
            分账方 {{ overview.shares?.shareholder_count || 0 }} 人
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #fef0f0; color: #f56c6c">
            <el-icon :size="28"><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value money-text">¥{{ formatMoney(overview.settlements?.total_pending_balance) }}</div>
            <div class="stat-label">待结算余额</div>
          </div>
          <div class="stat-extra">
            {{ overview.settlements?.pending_count || 0 }} 笔待结算
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>收款与分账趋势（近{{ trendDays }}天）</span>
              <el-radio-group v-model="trendDays" size="small" @change="loadTrend">
                <el-radio-button :value="7">7天</el-radio-button>
                <el-radio-button :value="30">30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>分账方收益排行</span>
          </template>
          <div ref="rankingChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 平台抽成趋势 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>平台抽成趋势（近30天）</span>
              <div v-if="feeTrend" class="fee-summary">
                <span>累计抽成: <b class="money-text text-primary">¥{{ formatMoney(feeTrend.total_fee) }}</b></span>
                <span style="margin-left: 20px">平均费率: <b>{{ feeTrend.avg_rate }}%</b></span>
              </div>
            </div>
          </template>
          <div ref="feeChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDashboardOverview, getDashboardTrend, getShareholderRanking, getPlatformFeeTrend } from '@/api/dashboard'

const overview = ref<any>({})
const trendDays = ref(7)
const trendData = ref<any>(null)
const rankingData = ref<any>(null)
const feeTrend = ref<any>(null)

const trendChartRef = ref<HTMLElement>()
const rankingChartRef = ref<HTMLElement>()
const feeChartRef = ref<HTMLElement>()

let trendChart: echarts.ECharts | null = null
let rankingChart: echarts.ECharts | null = null
let feeChart: echarts.ECharts | null = null

function formatMoney(val: any): string {
  const num = Number(val || 0)
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadOverview() {
  overview.value = await getDashboardOverview()
}

async function loadTrend() {
  trendData.value = await getDashboardTrend(trendDays.value)
  await nextTick()
  renderTrendChart()
}

async function loadRanking() {
  const res = await getShareholderRanking(10)
  rankingData.value = res.ranking || []
  await nextTick()
  renderRankingChart()
}

async function loadFeeTrend() {
  feeTrend.value = await getPlatformFeeTrend(30)
  await nextTick()
  renderFeeChart()
}

function renderTrendChart() {
  if (!trendChartRef.value || !trendData.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['收款金额', '分账金额', '订单数'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: trendData.value.dates, boundaryGap: false },
    yAxis: [
      { type: 'value', name: '金额(元)' },
      { type: 'value', name: '订单数' }
    ],
    series: [
      { name: '收款金额', type: 'line', smooth: true, data: trendData.value.order_amounts, areaStyle: { opacity: 0.3 }, itemStyle: { color: '#409eff' } },
      { name: '分账金额', type: 'line', smooth: true, data: trendData.value.share_amounts, areaStyle: { opacity: 0.3 }, itemStyle: { color: '#67c23a' } },
      { name: '订单数', type: 'bar', yAxisIndex: 1, data: trendData.value.orders, itemStyle: { color: '#e6a23c' } }
    ]
  })
}

function renderRankingChart() {
  if (!rankingChartRef.value || !rankingData.value) return
  if (!rankingChart) rankingChart = echarts.init(rankingChartRef.value)

  const data = rankingData.value.slice(0, 10).reverse()
  rankingChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.map((d: any) => d.name) },
    series: [{
      type: 'bar',
      data: data.map((d: any) => d.total_receivable),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#83bff6' },
          { offset: 1, color: '#188df0' }
        ])
      },
      label: { show: true, position: 'right', formatter: (p: any) => '¥' + Number(p.value).toLocaleString() }
    }]
  })
}

function renderFeeChart() {
  if (!feeChartRef.value || !feeTrend.value) return
  if (!feeChart) feeChart = echarts.init(feeChartRef.value)

  feeChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['平台抽成', '收款金额'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: feeTrend.value.dates, boundaryGap: false },
    yAxis: { type: 'value', name: '金额(元)' },
    series: [
      { name: '平台抽成', type: 'line', smooth: true, data: feeTrend.value.fees, areaStyle: { opacity: 0.3 }, itemStyle: { color: '#f56c6c' } },
      { name: '收款金额', type: 'line', smooth: true, data: feeTrend.value.amounts, itemStyle: { color: '#909399' } }
    ]
  })
}

onMounted(() => {
  loadOverview()
  loadTrend()
  loadRanking()
  loadFeeTrend()

  window.addEventListener('resize', () => {
    trendChart?.resize()
    rankingChart?.resize()
    feeChart?.resize()
  })
})
</script>

<style scoped lang="scss">
.dashboard {
  .stat-cards {
    .stat-card {
      .el-card__body {
        display: flex;
        align-items: flex-start;
        gap: 16px;
        position: relative;
      }

      .stat-icon {
        width: 56px;
        height: 56px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }

      .stat-info {
        flex: 1;
        .stat-value {
          font-size: 24px;
          font-weight: 600;
          color: #303133;
          line-height: 1.2;
        }
        .stat-label {
          font-size: 13px;
          color: #909399;
          margin-top: 4px;
        }
      }

      .stat-extra {
        position: absolute;
        bottom: 16px;
        right: 20px;
        font-size: 12px;
        color: #c0c4cc;
      }
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .chart-container {
    width: 100%;
    height: 320px;
  }

  .fee-summary {
    font-size: 13px;
    color: #606266;
  }
}
</style>
