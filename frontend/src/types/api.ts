export interface ApiSuccessResponse<T> {
  success: boolean
  message: string
  data: T
}

export interface MessageResponse {
  message: string
}

export interface PaginationMeta {
  page: number
  size: number
  total: number
  pages: number
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: PaginationMeta
}
