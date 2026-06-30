import { ElMessage, ElMessageBox } from 'element-plus';
import configApi from '@/api/config-api';
import { getDefaultTime } from '@/utils/time-range';

export function confirmSync() {
  ElMessageBox.confirm(
    '确认将远程 LSF 配置文件同步到 RSF Manager？此操作不可撤销。',
    '提示',
    {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      beforeClose: (action, instance, done) => {
        if (action === 'confirm') {
          instance.confirmButtonLoading = true;
          configApi
            .syncLsfConfigFile()
            .then(() => {
              done();
              ElMessage.success('同步成功');
            })
            .finally(() => {
              instance.confirmButtonLoading = false;
            });
        } else {
          done();
        }
      },
    },
  ).catch(() => {});
}

export { getDefaultTime };
