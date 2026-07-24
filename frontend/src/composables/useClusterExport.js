import { ElMessage } from 'element-plus';
import storageClusterApi from '@/api/storage-cluster-api';
import { toUtcRange } from '@/utils/datetime.js';

/**
 * 存储集群分析报告导出composable
 * @param {Object} options
 * @param {import('vue').Ref<number>} options.clusterId - 集群ID
 * @param {import('vue').Ref<[string, string]>} options.dateRange - 时间范围
 * @param {string} options.defaultSection - 当前section标识，用于处理 'current' scope
 */
export function useClusterExport({ clusterId, dateRange, defaultSection }) {
  function exportFilename(response, format, section) {
    const headers = response?.headers;
    const disposition = headers?.['content-disposition'] || headers?.get?.('content-disposition') || '';
    const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
    if (match) {
      try {
        return decodeURIComponent(match[1] || match[2]).replace(/[\\/\r\n]/g, '_');
      } catch {
        return (match[1] || match[2]).replace(/[\\/\r\n]/g, '_');
      }
    }
    const extension = format === 'excel' ? 'xlsx' : format === 'csv' && section === 'all' ? 'zip' : format;
    return `storage-health-${clusterId.value}.${extension}`;
  }

  async function handleExport(command) {
    const [scope, format] = command.split(':');
    const section = scope === 'current' ? defaultSection : scope;
    const [start_time, end_time] = toUtcRange(dateRange.value);

    try {
      const response = await storageClusterApi.exportAnalytics(clusterId.value, {
        start_time,
        end_time,
        section,
        format,
      });

      const blob = response.data instanceof Blob ? response.data : new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = exportFilename(response, format, section);
      document.body.appendChild(link);
      try {
        link.click();
      } finally {
        link.remove();
        URL.revokeObjectURL?.(url);
      }
    } catch {
      ElMessage.error('导出失败，请稍后重试');
    }
  }

  return { handleExport };
}
