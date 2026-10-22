/**
 * 统一日期格式化工具
 *
 * 全项目使用此工具格式化日期，避免各页面使用不同的 toLocaleString / dayjs.format 导致格式不一致。
 */
import dayjs from 'dayjs';

/**
 * 格式化为日期+时间：YYYY-MM-DD HH:mm
 */
export function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return '-';
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm');
}

/**
 * 格式化为仅日期：YYYY-MM-DD
 */
export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '-';
  return dayjs(dateStr).format('YYYY-MM-DD');
}

/**
 * 格式化为带秒的完整时间：YYYY-MM-DD HH:mm:ss
 */
export function formatDateTimeFull(dateStr?: string | null): string {
  if (!dateStr) return '-';
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss');
}
