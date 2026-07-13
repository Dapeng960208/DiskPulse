<script setup>
import { ElButton, ElCol, ElTabs,ElTabPane, ElForm, ElFormItem, ElInput, ElOption, ElRow, ElSelect, ElStatistic, ElTable, ElTableColumn, ElCard, ElAlert,ElMessage,ElSwitch, ElInputNumber } from 'element-plus';
import { ref } from 'vue';
import configApi from '@/api/config-api';

const form =ref({});
function fetchConfig(){
    configApi.fetch().then((result)=>{
      form.value = result;
    })
}
function updateConfig(){
  configApi.updateConfig(form.value).then((result)=>{
    form.value =result;
    ElMessage.success('保存成功');
  })
}
fetchConfig();
</script>
<template>
  <ElRow class="mt-5">
    <ElCol><ElButton
      type="primary"
      @click="updateConfig">保存</ElButton></ElCol>
  </ElRow>
  <ElTabs
    type="border-card"
    class="mt-5">
    <ElTabPane label="邮箱配置">
      <ElRow class="mt-5">
        <ElCol>
          <ElForm
            :model="form"
            label-width="auto">
            <ElFormItem label="邮箱域名/IP">
              <ElInput v-model="form.mail_host" />
            </ElFormItem>
            <ElFormItem label="端口号">
              <ElInput v-model="form.mail_port" />
            </ElFormItem>
            <ElFormItem label="账号">
              <ElInput v-model="form.mail_user" />
            </ElFormItem>
            <ElFormItem label="密码">
              <ElInput
                v-model="form.mail_password"
                type="password" />
            </ElFormItem>
            <ElFormItem label="抄送">
              <ElInput v-model="form.mail_to" />
            </ElFormItem>
          </ElForm>
        </ElCol>
      </ElRow>
    </ElTabPane>
    <ElTabPane label="邮件链接">
      <ElRow class="mt-5">
        <ElCol>
          <ElForm
            :model="form"
            label-width="auto">
            <ElFormItem label="公司名">
              <ElInput v-model="form.company" />
            </ElFormItem>
            <ElFormItem label="域名">
              <ElInput v-model="form.domain_name" />
            </ElFormItem>
            <ElFormItem label="个人扩容电子流链接">
              <ElInput v-model="form.person_expand" />
            </ElFormItem>
            <ElFormItem label="项目扩容电子流链接">
              <ElInput v-model="form.group_expand" />
            </ElFormItem>
          </ElForm>
        </ElCol>
      </ElRow>
    </ElTabPane>
    <ElTabPane label="IAM相关配置">
      <ElRow class="mt-5">
        <ElCol>
          <ElForm
            :model="form"
            label-width="auto">
            <ElFormItem label="IAM 接口">
              <ElInput v-model="form.iam_url" />
            </ElFormItem>
            <ElFormItem label="IAM应用账号">
              <ElInput v-model="form.iam_account" />
            </ElFormItem>
            <ElFormItem label="密码">
              <ElInput
                v-model="form.iam_password"
                type="password" />
            </ElFormItem>
          </ElForm>
        </ElCol>
      </ElRow>
    </ElTabPane>
    <ElTabPane label="存储配置">
      <ElRow class="mt-5">
        <ElCol>
          <ElForm
            :model="form"
            label-width="auto">
            <ElFormItem label="域名/IP">
              <ElInput v-model="form.storage_host" />
            </ElFormItem>
            <ElFormItem label="端口号">
              <ElInput v-model="form.storage_port" />
            </ElFormItem>
            <ElFormItem label="账号">
              <ElInput v-model="form.storage_user" />
            </ElFormItem>
            <ElFormItem label="密码">
              <ElInput
                v-model="form.storage_password"
                type="password" />
            </ElFormItem>
          </ElForm>
        </ElCol>
      </ElRow>
    </ElTabPane>
    <ElTabPane label="目录操作和备份配置">
      <ElRow class="mt-5">
        <ElCol>
          <ElForm
            :model="form"
            label-width="auto">
            <ElFormItem label="开启离职备份">
              <ElSwitch v-model="form.back_up_enabled"></ElSwitch>
            </ElFormItem>
            <ElFormItem
              v-if="form.back_up_enabled"
              label="域名/IP">
              <ElInput v-model="form.file_manage_host" />
            </ElFormItem>
            <ElFormItem
              v-if="form.back_up_enabled"
              label="端口号">
              <ElInput v-model="form.file_manage_port" />
            </ElFormItem>
            <ElFormItem
              v-if="form.back_up_enabled"
              label="账号">
              <ElInput v-model="form.file_manage_user" />
            </ElFormItem>
            <ElFormItem
              v-if="form.back_up_enabled"
              label="密码">
              <ElInput
                v-model="form.file_manage_password"
                type="password" />
            </ElFormItem>
            <ElFormItem
              v-if="form.back_up_enabled"
              label="离职数据保留时间(天)">
              <ElInputNumber
                v-model="form.back_up_quit_days"
                :min="1"
                :max="100"
                step="10" />
            </ElFormItem>
            <ElFormItem
              v-if="form.back_up_enabled"
              label="备份目录">
              <ElInput v-model="form.back_up_dir" />
            </ElFormItem>
            <ElFormItem
              v-if="form.back_up_enabled"
              label="备份数据保留时间(天)">
              <ElInputNumber
                v-model="form.back_up_duration"
                :min="1"
                :max="100"
                step="10" />
            </ElFormItem>
            <ElFormItem
              v-if="form.back_up_enabled"
              label="BPM电子流ID">
              <ElInput v-model="form.bpm_process_id" />
            </ElFormItem>
            <ElFormItem
              v-if="form.back_up_enabled"
              label="BPM电子流接口">
              <ElInput v-model="form.bpm_api_url" />
            </ElFormItem>
          </ElForm>
        </ElCol>
      </ElRow>
    </ElTabPane>
  </ElTabs>

</template>
