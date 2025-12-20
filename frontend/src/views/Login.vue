<template>
  <div style="padding: 20px;">
    <div style="text-align: center; margin: 40px 0;">
      <h2>家庭记账本</h2>
    </div>
    <t-input v-model="phone" label="手机号" placeholder="请输入手机号" />
    <t-input v-model="password" type="password" label="密码" placeholder="请输入密码" />
    <t-button theme="primary" size="large" block @click="handleLogin" style="margin-top: 20px;">登录</t-button>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';
import { useRouter } from 'vue-router';
import { Message } from 'tdesign-mobile-vue';

const phone = ref('');
const password = ref('');
const router = useRouter();

const handleLogin = async () => {
  try {
    const res = await axios.post(`/api/login?phone=${phone.value}&password=${password.value}`);
    localStorage.setItem('token', res.data.access_token);
    router.push('/home');
  } catch (e) {
    Message.error('登录失败，请检查账号密码');
  }
};
</script>