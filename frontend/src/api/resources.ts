import request from '@/utils/request';
import { ApiResponse, Resource, Technique } from '@/types';

export const resourcesApi = {
  list: (category: string = '') =>
    request.get<ApiResponse<Resource[]>>('/resources', { params: category ? { category } : {} })
      .then(r => r.data.data!),

  categories: () =>
    request.get<ApiResponse<string[]>>('/resources/categories').then(r => r.data.data!),

  techniques: () =>
    request.get<ApiResponse<Technique[]>>('/resources/techniques').then(r => r.data.data!),
};
