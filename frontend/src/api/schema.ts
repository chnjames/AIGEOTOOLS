import request from '@/utils/request';
import { ApiResponse } from '@/types';

export interface SchemaType {
  type: string;
  description: string;
  required: string[];
}

export interface SchemaRecommend {
  type: string;
  confidence: number;
  reason: string;
}

export interface SchemaValidateResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  score: number;
  detected_type?: string;
}

export interface SchemaGenerateResult {
  schema_type: string;
  json_ld: string;
  json_ld_raw: Record<string, unknown>;
}

export const schemaApi = {
  listTypes: () =>
    request.get<ApiResponse<SchemaType[]>>('/schema/types').then(r => r.data.data!),

  recommend: (content: string) =>
    request.post<ApiResponse<SchemaRecommend[]>>('/schema/recommend', { content }).then(r => r.data.data!),

  validate: (jsonLd: string, schemaType: string = '') =>
    request.post<ApiResponse<SchemaValidateResult>>('/schema/validate', { json_ld: jsonLd, schema_type: schemaType }).then(r => r.data.data!),

  generate: (body: { content: string; schema_type: string; brand?: string; temperature?: number }) =>
    request.post<ApiResponse<SchemaGenerateResult>>('/schema/generate', body).then(r => r.data.data!),
};
