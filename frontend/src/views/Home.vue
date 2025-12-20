<template>
  <div style="background: #f6f6f6; min-height: 100vh; padding-bottom: 80px;">
    <t-navbar title="本月账单" />

    <t-list>
      <t-cell-group v-for="item in records" :key="item.id">
        <t-cell :title="item.category" :note="`￥${item.amount}`" :description="item.note" />
      </t-cell-group>
    </t-list>

    <div style="position: fixed; bottom: 20px; left: 0; right: 0; padding: 0 20px;">
      <t-button theme="primary" shape="round" block @click="showAdd = true">记一笔</t-button>
    </div>

    <t-popup v-model="showAdd" placement="bottom" style="height: 60vh; padding: 20px;">
      <h3>新增记账</h3>
      <t-input v-model="newRecord.amount" type="number" label="金额" placeholder="0.00" />
      <t-input v-model="newRecord.category" label="分类" placeholder="如：餐饮、交通" />
      <t-input v-model="newRecord.note" label="备注" placeholder="选填" />
      <t-button theme="primary" block @click="saveRecord" style="margin-top: 20px;">保存</t-button>
    </t-popup>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const records = ref([]);
const showAdd = ref(false);
const newRecord = ref({ amount: '', category: '', note: '', type: '支出' });

const fetchData = async () => {
  const res = await axios.get('/api/records');
  records.value = res.data;
};

const saveRecord = async () => {
  await axios.post(`/api/records?amount=${newRecord.value.amount}&category=${newRecord.value.category}&type=支出&note=${newRecord.value.note}`);
  showAdd.value = false;
  fetchData();
};

onMounted(fetchData);
</script>