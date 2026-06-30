import { ElMessage } from 'element-plus';
import { getDefaultTime, getShortcuts } from '@/utils/time-range';

export { getDefaultTime, getShortcuts };

export function exportReport(apiFunction) {
  apiFunction
    .then(({ data, headers }) => {
      const link = document.createElement('a');
      const fileName = decodeURIComponent(headers.filename);

      link.href = window.URL.createObjectURL(data);
      link.download = fileName;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      ElMessage({
        message: `${fileName} 文件下载完成`,
        type: 'success',
      });
    })
    .catch((error) => {
      console.error('There was a problem with the fetch operation:', error);
      ElMessage({
        message: '文件下载失败',
        type: 'error',
      });
    });
}
