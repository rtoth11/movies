<template>
  <ScriptBlock v-for="b in blocks" :key="b.index_in_script" :block="b" />
</template>
