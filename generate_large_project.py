#!/usr/bin/env python3
"""
大规模测试项目生成器 - 创建100+个复杂ArkTS文件的测试环境
"""
import os
import random
from pathlib import Path

def generate_large_project(base_dir: str):
    base_path = Path(base_dir)
    base_path.mkdir(exist_ok=True, parents=True)
    
    # 创建目录结构
    dirs = [
        "src",
        "src/components",
        "src/services",
        "src/models",
        "src/utils",
        "src/stores",
        "src/api",
        "src/types",
        "src/constants"
    ]
    
    for d in dirs:
        (base_path / d).mkdir(exist_ok=True)
    
    # 生成100个测试文件
    total_files = 100
    
    # 类名池
    class_names = [
        "User", "Product", "Order", "Cart", "Payment", "Shipping",
        "Notification", "Profile", "Settings", "Dashboard",
        "Header", "Footer", "Sidebar", "Modal", "Button", "Input",
        "Dropdown", "Tabs", "Table", "Form", "Card", "List"
    ]
    
    function_names = [
        "fetchData", "saveData", "deleteData", "updateData", "validate",
        "transform", "format", "parse", "serialize", "deserialize",
        "compute", "calculate", "generate", "create", "read"
    ]
    
    file_counter = 1
    file_list = []
    
    # 生成类型定义文件
    types_content = '''export interface BaseEntity {
  id: string
  createdAt: number
  updatedAt: number
}

export interface User extends BaseEntity {
  name: string
  email: string
  role: 'admin' | 'user'
}

export interface Product extends BaseEntity {
  name: string
  price: number
  stock: number
  category: string
}

export interface Order extends BaseEntity {
  userId: string
  items: OrderItem[]
  total: number
  status: 'pending' | 'paid' | 'shipped' | 'delivered'
}

export interface OrderItem {
  productId: string
  quantity: number
  price: number
}

export interface ApiResponse<T> {
  data: T
  success: boolean
  message?: string
}
'''
    (base_path / "src/types/index.ets").write_text(types_content)
    file_list.append("src/types/index.ets")
    file_counter += 1
    
    # 生成常量文件
    constants_content = '''export const API_BASE_URL = 'https://api.example.com'
export const DEFAULT_TIMEOUT = 30000
export const MAX_RETRY_COUNT = 3
export const CACHE_TTL = 300000
export const ITEMS_PER_PAGE = 20

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  PROFILE: '/profile',
  PRODUCTS: '/products',
  CART: '/cart'
}
'''
    (base_path / "src/constants/index.ets").write_text(constants_content)
    file_list.append("src/constants/index.ets")
    file_counter += 1
    
    # 生成工具函数文件
    utils_content = '''import { BaseEntity } from '../types'

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency
  }).format(amount)
}

export function formatDate(timestamp: number): string {
  return new Date(timestamp).toLocaleDateString()
}

export function generateId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: number | null = null
  return function(...args: Parameters<T>) {
    if (timeout !== null) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(() => func(...args), wait)
  }
}

export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj))
}

export function isEmpty(value: any): boolean {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.trim() === ''
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value).length === 0
  return false
}

export function calculateTotal(products: { price: number, quantity: number }[]): number {
  return products.reduce((sum, item) => sum + item.price * item.quantity, 0)
}

export function sortByField<T extends BaseEntity>(
  items: T[],
  field: keyof T,
  ascending: boolean = true
): T[] {
  return [...items].sort((a, b) => {
    if (a[field] < b[field]) return ascending ? -1 : 1
    if (a[field] > b[field]) return ascending ? 1 : -1
    return 0
  })
}
'''
    (base_path / "src/utils/index.ets").write_text(utils_content)
    file_list.append("src/utils/index.ets")
    file_counter += 1
    
    # 生成API服务文件
    api_content = '''import { API_BASE_URL, DEFAULT_TIMEOUT, MAX_RETRY_COUNT } from '../constants'
import { ApiResponse } from '../types'

export class ApiClient {
  private baseUrl: string
  private timeout: number
  private maxRetries: number
  private headers: Record<string, string>

  constructor(options?: {
    baseUrl?: string
    timeout?: number
    maxRetries?: number
  }) {
    this.baseUrl = options?.baseUrl || API_BASE_URL
    this.timeout = options?.timeout || DEFAULT_TIMEOUT
    this.maxRetries = options?.maxRetries || MAX_RETRY_COUNT
    this.headers = {
      'Content-Type': 'application/json'
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>('GET', endpoint)
  }

  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, data)
  }

  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', endpoint, data)
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', endpoint)
  }

  async request<T>(
    method: string,
    endpoint: string,
    data?: any
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`
    const options: RequestInit = {
      method,
      headers: this.headers
    }
    
    if (data && method !== 'GET') {
      options.body = JSON.stringify(data)
    }
    
    const response = await fetch(url, options)
    const result = await response.json()
    return result
  }
}

let defaultClient: ApiClient | null = null

export function getApiClient(): ApiClient {
  if (!defaultClient) {
    defaultClient = new ApiClient()
  }
  return defaultClient
}
'''
    (base_path / "src/api/client.ets").write_text(api_content)
    file_list.append("src/api/client.ets")
    file_counter += 1
    
    # 生成25个组件文件
    components_dir = base_path / "src/components"
    for i in range(1, 26):
        class_name = random.choice(class_names)
        component_name = f"{class_name}Component"
        file_name = f"{component_name.lower()}.ets"
        
        content = f'''import {{ Button, Text, Column }} from '@kit.ArkUI'

@Component
export struct {component_name} {{
  @State title: string = "{class_name}"
  @State isLoading: boolean = false
  @State data: string[] = []

  build() {{
    Column() {{
      Text(this.title)
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
      
      if (this.isLoading) {{
        Text("Loading...")
      }} else {{
        Button("Refresh")
          .onClick(() => this.handleRefresh())
        
        for (let i = 0; i < this.data.length; i++) {{
          Text(this.data[i])
            .margin(8)
        }}
      }}
    }}
    .padding(16)
  }}

  handleRefresh(): void {{
    this.isLoading = true
    setTimeout(() => {{
      this.isLoading = false
      this.data = ['Item 1', 'Item 2', 'Item 3']
    }}, 1000)
  }}
}}

export function format{class_name}(input: string): string {{
  return input.toUpperCase()
}}

export function validate{class_name}(value: any): boolean {{
  return value !== null && value !== undefined
}}

export function create{class_name}(): {{ id: string, name: string }} {{
  return {{
    id: '{random.randint(1000, 9999)}',
    name: '{class_name}'
  }}
}}
'''
        (components_dir / file_name).write_text(content)
        file_list.append(f"src/components/{file_name}")
        file_counter += 1
    
    # 生成15个服务文件
    services_dir = base_path / "src/services"
    service_names = ["User", "Product", "Order", "Auth", "Cache", "Storage", "Logger", "I18n", "Theme", "Notification", "Analytics", "Validation", "Encryption", "Compression", "Network"]
    for service_name in service_names:
        file_name = f"{service_name.lower()}Service.ets"
        
        sn_lower = service_name.lower()
        content = f'''import {{ ApiResponse }} from '../types'
import {{ getApiClient }} from '../api/client'

export class {service_name}Service {{
  private api = getApiClient()
  private cache: Map<string, any> = new Map()

  async fetchAll(): Promise<ApiResponse<any[]>> {{
    return this.api.get('/{sn_lower}s')
  }}

  async fetchById(id: string): Promise<ApiResponse<any>> {{
    const cacheKey = `{sn_lower}_${{id}}`
    if (this.cache.has(cacheKey)) {{
      return {{ data: this.cache.get(cacheKey), success: true }}
    }}
    
    const result = await this.api.get(`/{sn_lower}s/${{id}}`)
    if (result.success) {{
      this.cache.set(cacheKey, result.data)
    }}
    return result
  }}

  async create(data: any): Promise<ApiResponse<any>> {{
    return this.api.post('/{sn_lower}s', data)
  }}

  async update(id: string, data: any): Promise<ApiResponse<any>> {{
    return this.api.put(`/{sn_lower}s/${{id}}`, data)
  }}

  async delete(id: string): Promise<ApiResponse<void>> {{
    return this.api.delete(`/{sn_lower}s/${{id}}`)
  }}

  clearCache(): void {{
    this.cache.clear()
  }}
}}

let instance: {service_name}Service | null = null

export function get{service_name}Service(): {service_name}Service {{
  if (!instance) {{
    instance = new {service_name}Service()
  }}
  return instance
}}
'''
        (services_dir / file_name).write_text(content)
        file_list.append(f"src/services/{file_name}")
        file_counter += 1
    
    # 生成10个Store文件
    stores_dir = base_path / "src/stores"
    store_names = ["User", "Product", "Cart", "Ui", "Config", "Auth", "Theme", "Notification", "Analytics", "App"]
    for store_name in store_names:
        file_name = f"{store_name.lower()}Store.ets"
        
        content = f'''export class {store_name}Store {{
  private _state: any
  private _listeners: Set<Function> = new Set()

  constructor() {{
    this._state = {{
      loading: false,
      error: null,
      data: null,
      lastUpdated: null
    }}
  }}

  get state(): any {{
    return this._state
  }}

  setState(updates: any): void {{
    this._state = {{ ...this._state, ...updates, lastUpdated: Date.now() }}
    this._notify()
  }}

  subscribe(listener: Function): () => void {{
    this._listeners.add(listener)
    return () => {{
      this._listeners.delete(listener)
    }}
  }}

  private _notify(): void {{
    this._listeners.forEach(listener => listener(this._state))
  }}

  setLoading(loading: boolean): void {{
    this.setState({{ loading }})
  }}

  setData(data: any): void {{
    this.setState({{ data }})
  }}

  reset(): void {{
    this._state = {{
      loading: false,
      error: null,
      data: null,
      lastUpdated: null
    }}
    this._notify()
  }}
}}

let instance: {store_name}Store | null = null

export function get{store_name}Store(): {store_name}Store {{
  if (!instance) {{
    instance = new {store_name}Store()
  }}
  return instance
}}
'''
        (stores_dir / file_name).write_text(content)
        file_list.append(f"src/stores/{file_name}")
        file_counter += 1
    
    # 生成入口文件
    pages_dir = base_path / "src/pages"
    pages_dir.mkdir(exist_ok=True)
    
    page_content = '''import { Column, Text, Button } from '@kit.ArkUI'

@Component
export struct Index {
  @State currentTab: number = 0
  @State isInitialized: boolean = false

  build() {
    Column() {
      if (this.isInitialized) {
        Text("ArkTS Knowledge Graph Demo")
          .fontSize(32)
          .fontWeight(FontWeight.Bold)
          .margin({ bottom: 24 })
        
        Row() {
          Button("Home")
            .onClick(() => this.currentTab = 0)
          Button("Users")
            .onClick(() => this.currentTab = 1)
          Button("Products")
            .onClick(() => this.currentTab = 2)
        }
        .margin({ bottom: 16 })
        
        if (this.currentTab === 0) {
          Text("Welcome to the Dashboard!")
            .fontSize(20)
        }
      } else {
        Text("Initializing...")
          .fontSize(20)
      }
    }
    .padding(24)
    .width('100%')
    .height('100%')
  }

  aboutToAppear() {
    setTimeout(() => {
      this.isInitialized = true
    }, 500)
  }
}
'''
    (pages_dir / "Index.ets").write_text(page_content)
    file_list.append("src/pages/Index.ets")
    
    print(f"✅ 生成了 {len(file_list)} 个文件到 {base_path}")
    return file_list

if __name__ == "__main__":
    files = generate_large_project("large-test-project")
    print("\n生成的文件:")
    for f in files[:20]:
        print(f"  - {f}")
    if len(files) > 20:
        print(f"  ... 还有 {len(files) - 20} 个文件")
