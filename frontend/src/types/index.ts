// 通用类型
export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PageQuery {
  page?: number
  page_size?: number
  keyword?: string
  [key: string]: any
}

// 用户
export interface User {
  id: number
  username: string
  email?: string
  phone?: string
  full_name?: string
  role: string
  status: string
  avatar?: string
  last_login_at?: string
  created_at: string
}

// 收款账户
export interface PaymentAccount {
  id: number
  platform: string
  account_name: string
  account_no?: string
  qr_code_url?: string
  bank_name?: string
  bank_card_no?: string
  is_default: boolean
  status: string
  remark?: string
  created_at: string
}

// 订单
export interface Order {
  id: number
  order_no: string
  out_order_no?: string
  total_amount: number
  platform_fee?: number
  shareable_amount?: number
  payment_account_id?: number
  payer_name?: string
  product_name?: string
  category?: string
  share_rule_id?: number
  share_status: string
  pay_status: string
  paid_at?: string
  transaction_id?: string
  source: string
  remark?: string
  created_at: string
  share_records?: ShareRecord[]
}

// 分账方
export interface Shareholder {
  id: number
  name: string
  contact?: string
  email?: string
  wechat_account?: string
  wechat_real_name?: string
  alipay_account?: string
  alipay_real_name?: string
  bank_name?: string
  bank_card_no?: string
  bank_account_name?: string
  preferred_payment: string
  default_rate?: number
  fixed_amount?: number
  shareholder_type: string
  status: string
  is_blacklisted: boolean
  remark?: string
  created_at: string
  total_receivable?: number
  total_settled?: number
  current_balance?: number
  pending_balance?: number
  total_orders?: number
}

// 分账明细项（规则配置用）
export interface ShareDetailItem {
  shareholder_id: number
  rate: number
  level: number
  parent_id?: number
}

// 分账规则
export interface ShareRule {
  id: number
  name: string
  description?: string
  scope_type: string
  scope_value?: string
  platform_fee_rate: number
  platform_fee_fixed?: number
  share_details: ShareDetailItem[]
  enable_multi_level: boolean
  max_levels: number
  is_default: boolean
  status: string
  priority: number
  effective_from?: string
  effective_to?: string
  remark?: string
  created_at: string
}

// 分账明细
export interface ShareRecord {
  id: number
  order_id: number
  order_no: string
  shareholder_id: number
  shareholder_name: string
  order_amount: number
  platform_fee: number
  shareable_amount: number
  share_rate?: number
  share_amount: number
  actual_amount?: number
  level: number
  parent_shareholder_id?: number
  status: string
  settlement_id?: number
  is_adjusted: number
  adjust_reason?: string
  created_at?: string
}

// 结算单
export interface Settlement {
  id: number
  settlement_no: string
  shareholder_id: number
  shareholder_name: string
  total_records: number
  total_amount: number
  actual_amount?: number
  fee_amount?: number
  payment_method: string
  transaction_no?: string
  transfer_voucher_url?: string
  status: string
  period_start?: string
  period_end?: string
  transferred_at?: string
  confirmed_at?: string
  remark?: string
  created_at: string
  share_records?: ShareRecord[]
}

// 对账记录
export interface Reconciliation {
  id: number
  recon_no: string
  platform: string
  recon_date: string
  system_orders: number
  system_amount: number
  channel_orders: number
  channel_amount: number
  matched_orders: number
  diff_orders: number
  diff_amount: number
  status: string
  file_name?: string
  created_at: string
}
